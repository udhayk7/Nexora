import threading
import time
from typing import Optional

import redis

from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import logger

# Thread-safe in-memory fallback store
_memory_lock = threading.Lock()
_memory_store: dict[str, list[float]] = {}


def _get_redis_client() -> Optional[redis.Redis]:
    """Attempt connecting to Redis, returning None if unreachable."""
    try:
        client = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_timeout=1.0,
            decode_responses=True,
        )
        client.ping()
        return client
    except Exception:
        return None


class RateLimiter:
    """Sliding-window rate limiter utilizing Redis with an in-memory fallback."""

    def __init__(self, action: str, max_requests: int = 5, window_seconds: int = 60) -> None:
        self.action = action
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def reset(self) -> None:
        """Reset rate limiter store (primarily for test environments)."""
        global _memory_store
        with _memory_lock:
            _memory_store.clear()
        redis_client = _get_redis_client()
        if redis_client:
            try:
                keys = redis_client.keys(f"nexora:rate:{self.action}:*")
                if isinstance(keys, list):
                    for k in keys:
                        redis_client.delete(k)
            except Exception:
                pass

    def check(self, identifier: str) -> None:
        """Check rate limit for the given client identifier (IP or username)."""
        redis_client = _get_redis_client()
        key = f"nexora:rate:{self.action}:{identifier}"

        if redis_client:
            try:
                current = int(redis_client.incr(key))  # type: ignore[arg-type]
                if current == 1:
                    redis_client.expire(key, self.window_seconds)
                if current > self.max_requests:
                    logger.warning(
                        f"Rate limit exceeded via Redis: action={self.action} id={identifier}"
                    )
                    raise AppError(
                        message="Too many requests. Please try again later.",
                        code="RATE_LIMIT_EXCEEDED",
                        status_code=429,
                    )
                return
            except AppError:
                raise
            except Exception as e:
                logger.warning(f"Redis rate limiter failed, falling back to memory: {e}")

        # In-memory fallback
        now = time.time()
        with _memory_lock:
            timestamps = _memory_store.get(key, [])
            # Filter timestamps within active window
            valid_timestamps = [t for t in timestamps if now - t < self.window_seconds]
            if len(valid_timestamps) >= self.max_requests:
                _memory_store[key] = valid_timestamps
                logger.warning(
                    f"Rate limit exceeded via memory: action={self.action} id={identifier}"
                )
                raise AppError(
                    message="Too many requests. Please try again later.",
                    code="RATE_LIMIT_EXCEEDED",
                    status_code=429,
                )
            valid_timestamps.append(now)
            _memory_store[key] = valid_timestamps


# Standard instances for auth routes
login_limiter = RateLimiter(
    action="login",
    max_requests=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)
register_limiter = RateLimiter(
    action="register",
    max_requests=settings.AUTH_RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)
