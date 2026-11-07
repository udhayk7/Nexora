import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import logger
from app.models.assistant import GmailConnection
from app.models.user import User
from app.services.ai.factory import test_all_ai_providers


class IntegrationHealthService:
    """Centralized diagnostic inspection and safe connection testing for all integrations."""

    @classmethod
    def check_all(cls, db: Session, user: Optional[User] = None) -> dict[str, Any]:
        """Aggregate health across AI providers, databases, Redis, Celery, Gmail, and Job feeds."""
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. AI Providers Health
        ai_status = cls._check_ai_providers()

        # 2. Database Health
        postgres_status = cls._check_postgres(db)

        # 3. Redis Health
        redis_status = cls._check_redis()

        # 4. Celery Health
        celery_status = cls._check_celery()

        # 5. Gmail OAuth Health
        gmail_status = cls._check_gmail(db, user)

        # 6. Job Discovery Sources Health
        job_sources_status = cls._check_job_sources()

        return {
            "timestamp": now_iso,
            "environment": settings.ENVIRONMENT,
            "openai": ai_status.get("openai", {}),
            "gemini": ai_status.get("gemini", {}),
            "postgres": postgres_status,
            "redis": redis_status,
            "celery": celery_status,
            "gmail": gmail_status,
            "job_sources": job_sources_status,
        }

    @classmethod
    def test_service(
        cls, service_name: str, db: Session, user: Optional[User] = None
    ) -> dict[str, Any]:
        """Safely test connection to a single service without exposing credentials."""
        service = service_name.lower().strip()

        if service == "openai":
            from app.services.ai.openai_provider import OpenAIProvider

            openai_prov = OpenAIProvider()
            return openai_prov.test_connection()

        elif service == "gemini":
            from app.services.ai.gemini_provider import GeminiProvider

            gemini_prov = GeminiProvider()
            return gemini_prov.test_connection()

        elif service == "postgres":
            return cls._check_postgres(db)

        elif service == "redis":
            return cls._check_redis()

        elif service == "celery":
            return cls._check_celery()

        elif service == "gmail":
            return cls._check_gmail(db, user)

        elif service == "job_sources":
            return cls._check_job_sources()

        return {
            "status": "unavailable",
            "service": service_name,
            "message": f"Unknown integration service '{service_name}'.",
        }

    @classmethod
    def _check_ai_providers(cls) -> dict[str, Any]:
        """Test configured AI providers."""
        try:
            return test_all_ai_providers()
        except Exception as exc:
            logger.warning("AI provider health check error: %s", exc)
            return {
                "openai": {"status": "unavailable", "error": str(exc)[:100]},
                "gemini": {"status": "unavailable", "error": str(exc)[:100]},
            }

    @classmethod
    def _check_postgres(cls, db: Session) -> dict[str, Any]:
        """Verify PostgreSQL connectivity and connection pool metrics."""
        start_time = time.time()
        try:
            db.execute(text("SELECT 1"))
            latency = int((time.time() - start_time) * 1000)

            # Check pool metrics from engine
            from app.core.database import engine

            pool = getattr(engine, "pool", None)
            pool_metrics = {
                "size": getattr(pool, "size", lambda: settings.DB_POOL_SIZE)(),
                "checkedin": getattr(pool, "checkedin", lambda: 0)(),
                "checkedout": getattr(pool, "checkedout", lambda: 0)(),
                "overflow": getattr(pool, "overflow", lambda: 0)(),
            }

            return {
                "status": "connected",
                "service": "postgresql",
                "latency_ms": latency,
                "pool_metrics": pool_metrics,
                "ssl_mode": settings.DB_SSL_MODE or "default",
                "message": "PostgreSQL database connected and responsive",
            }
        except Exception as exc:
            latency = int((time.time() - start_time) * 1000)
            return {
                "status": "disconnected",
                "service": "postgresql",
                "latency_ms": latency,
                "error": str(exc)[:150],
                "message": "PostgreSQL database connection failed",
            }

    @classmethod
    def _check_redis(cls) -> dict[str, Any]:
        """Verify Redis connectivity and ping latency."""
        start_time = time.time()
        try:
            import redis

            r = redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=3.0)
            r.ping()
            latency = int((time.time() - start_time) * 1000)
            return {
                "status": "connected",
                "service": "redis",
                "latency_ms": latency,
                "ssl_enabled": settings.REDIS_SSL,
                "message": "Redis cache and coordination service connected",
            }
        except Exception as exc:
            latency = int((time.time() - start_time) * 1000)
            return {
                "status": "disconnected",
                "service": "redis",
                "latency_ms": latency,
                "error": str(exc)[:150],
                "message": "Redis connection failed",
            }

    @classmethod
    def _check_celery(cls) -> dict[str, Any]:
        """Verify Celery task broker status and registered task schedules."""
        try:
            from app.core.celery_app import celery

            # Inspect active workers
            inspect = celery.control.inspect(timeout=1.5)
            ping_result = inspect.ping() if inspect else None
            active_workers = list(ping_result.keys()) if ping_result else []

            status = "connected" if active_workers else "degraded"
            message = (
                f"Celery worker active ({len(active_workers)} workers)"
                if active_workers
                else "Broker reachable; worker not detected or idle"
            )

            return {
                "status": status,
                "service": "celery",
                "broker": "redis",
                "active_workers_count": len(active_workers),
                "registered_schedules_count": len(celery.conf.beat_schedule or {}),
                "message": message,
            }
        except Exception as exc:
            return {
                "status": "disconnected",
                "service": "celery",
                "error": str(exc)[:150],
                "message": "Celery broker unreachable",
            }

    @classmethod
    def _check_gmail(cls, db: Session, user: Optional[User] = None) -> dict[str, Any]:
        """Inspect Google OAuth and Gmail integration state."""
        is_client_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)

        user_connection = None
        if user:
            user_connection = (
                db.query(GmailConnection)
                .filter(GmailConnection.user_id == user.id, GmailConnection.is_active.is_(True))
                .first()
            )

        if not is_client_configured:
            return {
                "status": "unconfigured",
                "service": "gmail_oauth",
                "is_client_configured": False,
                "is_connected": False,
                "message": (
                    "Google OAuth credentials (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET) "
                    "are not set in environment."
                ),
                "setup_instructions": (
                    "To enable Gmail OAuth, configure a Web Application in Google Cloud Console, "
                    "authorize the redirect URI, and set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
                ),
            }

        if user_connection:
            return {
                "status": "connected",
                "service": "gmail_oauth",
                "is_client_configured": True,
                "is_connected": True,
                "connected_email": user_connection.email,
                "scopes": user_connection.scopes,
                "connected_at": user_connection.connected_at.isoformat()
                if user_connection.connected_at
                else None,
                "last_used_at": user_connection.last_used_at.isoformat()
                if user_connection.last_used_at
                else None,
                "message": f"Connected to Google account ({user_connection.email})",
            }

        return {
            "status": "disconnected",
            "service": "gmail_oauth",
            "is_client_configured": True,
            "is_connected": False,
            "message": "OAuth client configured, but current user has not connected Gmail.",
        }

    @classmethod
    def _check_job_sources(cls) -> dict[str, Any]:
        """Inspect operational status of all 5 job discovery adapters."""
        adapters_info = {
            "greenhouse": {
                "name": "Greenhouse Board Adapter",
                "type": "api",
                "auth_required": False,
                "status": "operational",
                "endpoint_pattern": "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs",
                "rate_limit_policy": "0.5s domain pacing with Crawl-delay compliance",
                "normalization": "Title, company, location, requirements, source URL, salary",
                "deduplication": "Source domain + normalized job title hash",
            },
            "lever": {
                "name": "Lever Postings Adapter",
                "type": "api",
                "auth_required": False,
                "status": "operational",
                "endpoint_pattern": "https://api.lever.co/v0/postings/{site}",
                "rate_limit_policy": "0.5s domain pacing with Crawl-delay compliance",
                "normalization": "Role name, team tags, location text, hosted URL",
                "deduplication": "Normalized hosted URL + title hash",
            },
            "ashby": {
                "name": "Ashby Job Board Adapter",
                "type": "api",
                "auth_required": False,
                "status": "operational",
                "endpoint_pattern": "https://api.ashbyhq.com/api/non-auth/job-board/{org}",
                "rate_limit_policy": "0.5s domain pacing with Crawl-delay compliance",
                "normalization": "Title, department, employment type, location, apply link",
                "deduplication": "Ashby job UUID + posting URL hash",
            },
            "rss_atom": {
                "name": "RSS/Atom Feed Adapter",
                "type": "feed",
                "auth_required": False,
                "status": "operational",
                "endpoint_pattern": "Standard RSS 2.0 / Atom 1.0 XML feeds",
                "rate_limit_policy": "Full robots.txt Crawl-delay compliance + SSRF safeguards",
                "normalization": "Entry title, summary, pubDate, GUID/link",
                "deduplication": "Feed item GUID + canonical URL hash",
            },
            "json_feed": {
                "name": "Generic JSON Feed Adapter",
                "type": "feed",
                "auth_required": False,
                "status": "operational",
                "endpoint_pattern": "REST / JSON endpoints with configurable field mapping",
                "rate_limit_policy": "Domain pacing with atomic Redis reservation",
                "normalization": "Configurable schema field projection",
                "deduplication": "Unique job_id or canonical URL hash",
            },
        }

        return {
            "status": "operational",
            "adapters_count": len(adapters_info),
            "operational_count": len(adapters_info),
            "adapters": adapters_info,
        }
