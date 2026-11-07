# Production Configuration & Environment Guide

This document describes the environment configuration, secrets management, security guardrails, and validation rules for running Nexora in a production environment.

---

## 1. Environment Variable Reference

### 1.1 Core Platform & Security
| Variable | Required | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | Yes | `development` | Deployment tier: `development`, `staging`, `production`. |
| `DEBUG` | Yes | `False` (in prod) | Debug mode. **Strictly disabled (`False`)** in production. |
| `SECRET_KEY` | Yes | - | Primary cryptographic secret key for sessions and CSRF. Must be high-entropy. |
| `JWT_SECRET_KEY` | Yes | - | Signing secret for authentication tokens. Must be high-entropy. |
| `JWT_ALGORITHM` | No | `HS256` | Algorithm for JWT signature validation. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15` | Expiration lifetime for short-lived access tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Expiration lifetime for rotating refresh tokens. |
| `ALLOWED_ORIGINS` | Yes | - | Comma-delimited list of allowed CORS origins (e.g., `https://app.nexora.com`). |

### 1.2 Database (PostgreSQL)
| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | - | SQLAlchemy PostgreSQL URL (`postgresql+psycopg://user:pass@host:port/dbname`). Rejects `localhost` and placeholder passwords in production. |
| `DB_SSL_MODE` | No | `prefer` | PostgreSQL SSL connection mode: `prefer`, `require`, `verify-ca`, `verify-full`. In production, `require` or higher is recommended. |
| `DB_POOL_SIZE` | No | `5` | Base connection pool size. |
| `DB_MAX_OVERFLOW` | No | `10` | Maximum burst connections above `DB_POOL_SIZE`. |
| `DB_POOL_TIMEOUT` | No | `30` | Seconds to wait before timing out on pool checkout. |
| `DB_POOL_RECYCLE` | No | `1800` | Seconds before recycling idle connections (avoids stale connections). |

### 1.3 Redis & Celery Workers
| Variable | Required | Default | Description |
|---|---|---|---|
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Primary Redis connection string for caching, rate limiting, and domain pacing. |
| `REDIS_PASSWORD` | No | `None` | Authentication password for managed Redis instances. |
| `REDIS_SSL` | No | `False` | When `True`, enforces TLS/SSL connection (`rediss://`) for Celery broker and backend. |
| `CELERY_BROKER_URL` | Yes | `redis://localhost:6379/1` | Celery message broker queue. |
| `CELERY_RESULT_BACKEND` | Yes | `redis://redis:6379/2` | Celery task result backend. |

### 1.4 AI Providers & Model Routing
| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_PRIMARY_PROVIDER` | No | `openai` | Primary intelligence provider: `openai` or `gemini`. |
| `AI_SECONDARY_PROVIDER` | No | `gemini` | Secondary fallback provider when primary fails or is unconfigured. |
| `AI_FALLBACK_TO_DETERMINISTIC` | No | `True` | Fall back to rule-based deterministic scoring if all AI providers fail. |
| `OPENAI_API_KEY` | Optional | `None` | OpenAI API secret key (`sk-...`). Never exposed to frontend or committed to git. |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Economical model for routine categorization and parsing. |
| `OPENAI_STRONG_MODEL` | No | `gpt-4o` | High-reasoning model for complex tailoring and interview analysis. |
| `GEMINI_API_KEY` | Optional | `None` | Google Gemini API secret key. Never exposed or committed. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Fast routine model for high-throughput queries. |
| `GEMINI_STRONG_MODEL` | No | `gemini-1.5-pro` | High-context model for comprehensive evaluation. |

### 1.5 Server-Side AI Budget & Cost Controls
| Variable | Required | Default | Description |
|---|---|---|---|
| `AI_DAILY_BUDGET_USD` | No | `10.00` | Global platform spending ceiling per calendar day ($ USD). Rejections occur once reached. |
| `AI_MONTHLY_BUDGET_USD` | No | `100.00` | Global platform spending ceiling per calendar month ($ USD). Rejections occur once reached. |
| `AI_USER_DAILY_TOKEN_LIMIT` | No | `150000` | Per-user maximum total token consumption per calendar day. |
| `AI_USER_DAILY_BUDGET_USD` | No | `2.00` | Per-user maximum dollar spend per calendar day. |
| `AI_ENABLE_RESPONSE_CACHE` | No | `True` | SHA-256 fingerprint caching for identical user prompts and model combinations. |
| `AI_RESPONSE_CACHE_TTL_SECONDS` | No | `86400` | Cache time-to-live (24 hours). |

### 1.6 Google OAuth & Gmail Integration
| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | Optional | `None` | Google Cloud OAuth 2.0 Web Client ID. |
| `GOOGLE_CLIENT_SECRET` | Optional | `None` | Google Cloud OAuth 2.0 Web Client Secret. |
| `GOOGLE_REDIRECT_URI` | Optional | - | Authorized redirect URI (e.g. `https://app.nexora.com/api/v1/integrations/google/callback`). |
| `GMAIL_TOKEN_ENCRYPTION_KEY` | Required if Google enabled | - | 32-byte key used for AES-GCM encryption of stored OAuth access and refresh tokens. |

---

## 2. Startup Validation Guardrails

In production (`ENVIRONMENT=production`), Nexora executes strict startup checks in `Settings.validate_production_settings()`:
1. **Secrets Integrity**: `SECRET_KEY` and `JWT_SECRET_KEY` must be configured and cannot contain substrings like `default`, `secret`, `change_me`, or `test`.
2. **Database Hardening**: `DATABASE_URL` cannot point to `localhost`, `127.0.0.1`, or use default/example credentials.
3. **Debug Prohibition**: `DEBUG` must be `False`.
4. **Encryption Key Integrity**: When Google OAuth is enabled, `GMAIL_TOKEN_ENCRYPTION_KEY` must be configured with a 32-byte key.

