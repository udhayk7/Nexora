# Production Deployment Guide — Nexora: Your AI Career Navigator

This guide provides instructions for deploying Nexora to production environments using Docker Compose or orchestrators (Kubernetes / ECS).

---

## 1. System Requirements

- **Operating System:** Linux (Ubuntu 22.04+ or Debian 12+) or macOS
- **CPU / Memory:** Minimum 2 vCPU, 4GB RAM (8GB RAM recommended for production workloads)
- **Container Runtime:** Docker Engine 24.0+ & Docker Compose v2.20+
- **Database:** PostgreSQL 16+
- **In-Memory Cache / Broker:** Redis 7+

---

## 2. Environment Configuration

Copy `.env.example` to `.env` in the root directory and configure production secrets:

```bash
cp .env.example .env
```

### Critical Production Environment Variables

| Variable | Recommended Production Value | Description |
|---|---|---|
| `ENVIRONMENT` | `production` | Enables HSTS and disables debug endpoints |
| `SECRET_KEY` | *(64-char hex)* | Used for JWT signing and HMAC OAuth states |
| `ENCRYPTION_KEY` | *(32-byte Fernet base64)* | Used to encrypt OAuth tokens at rest |
| `POSTGRES_USER` | `nexora_user` | PostgreSQL user |
| `POSTGRES_PASSWORD` | *(Strong password)* | Database password |
| `POSTGRES_DB` | `nexora_db` | Database name |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Production DB connection string |
| `DB_SSL_MODE` | `require` | Enforces TLS transport for PostgreSQL |
| `REDIS_URL` | `redis://:pass@host:6379/0` | Production Redis connection string |
| `REDIS_PASSWORD` | *(Strong password)* | Redis authentication password |
| `REDIS_SSL` | `true` | Enforces TLS transport for Redis |
| `ALLOWED_ORIGINS` | `["https://nexora.example.com"]` | CORS origin restrictions |
| `AI_PROVIDER` | `openai` or `gemini` | Primary AI provider |
| `OPENAI_API_KEY` | *(sk-...)* | OpenAI production key |
| `GEMINI_API_KEY` | *(AIza...)* | Google Gemini production key |
| `AI_DAILY_BUDGET_USD` | `10.00` | Hard platform daily budget limit |
| `AI_MONTHLY_BUDGET_USD` | `100.00` | Hard platform monthly budget limit |
| `GOOGLE_CLIENT_ID` | *(OAuth Client ID)* | Google Workspace integration |
| `GOOGLE_CLIENT_SECRET` | *(OAuth Client Secret)* | Google Workspace secret |
| `GOOGLE_REDIRECT_URI` | `https://nexora.example.com/api/v1/integrations/google/callback` | OAuth redirect URI |

> [!WARNING]
> Never commit `.env` or files containing secret credentials to GitHub. Always use secrets management (AWS Secrets Manager, HashiCorp Vault, or GitHub Secrets).

---

## 3. Production Deployment via Docker Compose

### Step 1: Build Production Images
```bash
docker compose -f docker-compose.yml build --no-cache
```

### Step 2: Start Core Services
```bash
docker compose -f docker-compose.yml up -d postgres redis
```

### Step 3: Run Database Migrations
```bash
docker compose -f docker-compose.yml run --rm backend alembic upgrade head
```

### Step 4: Start Backend, Celery Worker, and Frontend
```bash
docker compose -f docker-compose.yml up -d
```

### Step 5: Verify Service Health
```bash
# Check all containers are running and healthy
docker compose ps

# Check API health endpoint
curl -s http://localhost:8000/api/v1/health | jq .
```

---

## 4. Disaster Recovery & Backup Procedures

### Automated Database Backup
Run daily via cron:
```bash
docker exec nexora-postgres pg_dump -U nexora_user nexora_db > /backups/nexora_$(date +%Y%m%d_%H%M%S).sql
```

### Restoration Verification
```bash
# Create temporary database
docker exec -i nexora-postgres psql -U nexora_user -c "CREATE DATABASE restore_test;"

# Restore dump
docker exec -i nexora-postgres psql -U nexora_user restore_test < /backups/nexora_latest.sql

# Drop temporary database
docker exec -i nexora-postgres psql -U nexora_user -c "DROP DATABASE restore_test;"
```

---

## 5. Security & Reverse Proxy Setup (Nginx Example)

```nginx
server {
    listen 443 ssl http2;
    server_name nexora.example.com;

    ssl_certificate /etc/letsencrypt/live/nexora.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nexora.example.com/privkey.pem;

    # Reverse proxy frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }

    # Reverse proxy backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```
