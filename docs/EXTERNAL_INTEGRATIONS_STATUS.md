# External Integrations Operational Status & Adapters

This document details all external services, third-party APIs, and discovery adapters integrated into Nexora.

---

## 1. Integrations Status Matrix

| Service | Category | Auth Method | Rate Limiting / Pacing Policy | Production Status |
|---|---|---|---|---|
| **OpenAI API** | AI Provider (Primary) | Bearer API Key | $10/day budget ceiling, response caching | Operational (Configured when key present) |
| **Google Gemini API** | AI Provider (Secondary) | API Key | $10/day budget ceiling, response caching | Operational (Configured when key present) |
| **PostgreSQL** | Primary Database | Password / SSL | Connection pooled (size=20, max=10) | Operational |
| **Redis** | Broker & Rate Limiting | Password / TLS | Atomic Lua script pacing, 1000 ops/sec | Operational |
| **Celery Workers** | Task Processing | Internal Queue | Distributed background workers | Operational |
| **Gmail OAuth 2.0** | Recruiter Outreach | OAuth 2.0 Bearer | User-confirmed draft creation only | Operational (Requires user authorization) |
| **Greenhouse API** | Job Discovery | Public Endpoint | 0.5s domain pacing with Crawl-delay | Operational |
| **Lever API** | Job Discovery | Public Endpoint | 0.5s domain pacing with Crawl-delay | Operational |
| **Ashby HQ API** | Job Discovery | Public Endpoint | 0.5s domain pacing with Crawl-delay | Operational |
| **RSS / Atom Feeds** | Job Discovery | Open XML | Robots.txt Crawl-delay + SSRF protection | Operational |
| **Generic JSON Feeds**| Job Discovery | Open JSON | Schema validation + deduplication | Operational |

---

## 2. Job Discovery Adapters Specifications

### 2.1 Greenhouse Board Adapter
- **Endpoint Pattern**: `https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs`
- **Authentication**: None required (public official API).
- **Normalization**: Standardized title, location, employment type, source URL, requirements, salary ranges.
- **Pacing**: Atomic Redis per-domain reservation adhering to Greenhouse robots directives.

### 2.2 Lever Postings Adapter
- **Endpoint Pattern**: `https://api.lever.co/v0/postings/{site}`
- **Authentication**: None required (public official API).
- **Normalization**: Role title, hosted URL, categories (team, department, location).
- **Pacing**: Atomic Redis per-domain reservation adhering to Lever robots directives.

### 2.3 Ashby HQ Adapter
- **Endpoint Pattern**: `https://api.ashbyhq.com/api/non-auth/job-board/{org}`
- **Authentication**: None required (public official API).
- **Normalization**: Title, department, compensation, location text, application link.
- **Pacing**: Atomic Redis per-domain reservation adhering to Ashby robots directives.

### 2.4 RSS / Atom Feed Adapter
- **Endpoint Pattern**: Any standard RSS 2.0 or Atom 1.0 XML career feed.
- **Authentication**: None required.
- **Security Safeguards**: Strict SSRF IP blocking (disallows private RFC-1918 subnets, link-local, loopback) and robots.txt Crawl-delay enforcement.

### 2.5 Generic JSON Feed Adapter
- **Endpoint Pattern**: Standard corporate JSON jobs endpoints.
- **Authentication**: None required.
- **Validation**: Strict Pydantic schema validation; invalid items are rejected safely without failing ingestion.

---

## 3. Compliance & Boundaries
- **No Unauthorized Scraping**: Nexora interacts only with published public APIs or RSS feeds.
- **No Access Control Bypass**: No CAPTCHA circumvention, private intranet probing, or authentication spoofing is permitted.
- **Clear Health Status**: All services report diagnostic status via `/api/v1/integrations/health` and `/dashboard/integrations`.

