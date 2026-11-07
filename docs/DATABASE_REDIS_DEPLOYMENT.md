# PostgreSQL & Redis Production Deployment Guide

This document specifies the database pooling, SSL enforcement, and Redis/Celery queue hardening configurations for Nexora.

---

## 1. PostgreSQL Production Deployment

### 1.1 Connection Pool Settings
Nexora uses SQLAlchemy with the `psycopg` (v3) binary driver. The connection pool is tuned for asynchronous web backends and high concurrency:
- **`DB_POOL_SIZE`** (Default: `5`, Prod: `20`): Base number of persistent connections maintained per process.
- **`DB_MAX_OVERFLOW`** (Default: `10`, Prod: `20`): Additional connections opened during traffic spikes.
- **`DB_POOL_TIMEOUT`** (Default: `30`): Timeout in seconds before raising a pool checkout error.
- **`DB_POOL_RECYCLE`** (Default: `1800`): Maximum lifetime (30 minutes) before idle connections are closed and refreshed.

### 1.2 Transport Security (`DB_SSL_MODE`)
PostgreSQL connections support configurable SSL modes:
- `disable`: No encryption (local Docker dev only).
- `prefer`: Attempts SSL encryption, falls back to plaintext if unsupported.
- `require`: Enforces SSL encryption. Rejects non-SSL database endpoints. Recommended for cloud databases (AWS RDS, GCP Cloud SQL, Supabase).
- `verify-ca` / `verify-full`: Enforces SSL and validates server certificate against trusted authorities.

### 1.3 Database Diagnostic Probing
The `/api/v1/integrations/health` endpoint and `/api/v1/integrations/test/postgres` endpoint execute a non-blocking `SELECT 1` query to verify:
- Connection reachability.
- Latency (ms).
- Current pool utilization (size, max overflow, active checked-out connections).

---

## 2. Redis & Celery Asynchronous Queue

### 2.1 Redis Server Configuration
Redis serves three distinct architectural functions in Nexora:
1. **DB 0**: Application caching, AI duplicate request fingerprinting, and robots.txt domain pacing locks.
2. **DB 1**: Celery task message broker queue.
3. **DB 2**: Celery task result backend.

### 2.2 Security & TLS/SSL Transport
In production environments:
- **`REDIS_PASSWORD`**: If configured, authentication is passed to all Redis connections and Celery broker URLs.
- **`REDIS_SSL=True`**: Switches broker and backend protocols from `redis://` to `rediss://`, with SSL certificate verification.

### 2.3 Celery Worker Health & Monitoring
The integration health service verifies:
- PING latency to Redis.
- Active Celery worker nodes via `celery_app.control.ping(timeout=1.0)`.
- Worker registered names and broker transport protocol.

