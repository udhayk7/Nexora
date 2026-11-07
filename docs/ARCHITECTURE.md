# System Architecture

## Overview

Nexora is designed as a modular monorepo separating a responsive Next.js frontend from a high-throughput Python FastAPI backend. The system integrates asynchronous background processing via Celery and Redis to handle computationally heavy AI workflows (e.g., resume parsing, opportunity scoring, embedding generation) without blocking client-facing HTTP requests.

---

## High-Level Topology

```mermaid
flowchart TD
    User["User Browser"] -->|HTTPS / Next.js Pages| Frontend["Next.js App Router (Port 3000)"]
    User -->|REST / JSON| Backend["FastAPI Backend (Port 8000)"]
    Frontend -->|API Calls (Bearer Auth)| Backend
    Backend -->|SQLAlchemy / Queries| DB[("PostgreSQL (Port 5432)")]
    Backend -->|Rate Limiting / Caching| Redis[("Redis Broker / Cache (Port 6379)")]
    Worker["Celery Worker"] -->|Fetch Jobs| Redis
    Worker -->|Read / Write State| DB
    Worker -.->|External AI API Calls| AIProviders["AI Services (Gemini / OpenAI)"]
```

---

## Component Breakdown

### 1. Frontend (`frontend/`)
- **Framework**: Next.js 14+ with App Router.
- **Language**: TypeScript with strict typing.
- **Styling**: Tailwind CSS with shadcn-compatible CSS variable tokens for clean, themeable interfaces.
- **Icons**: Lucide React.
- **Authentication Client**:
  - In-memory `access_token` retention in React Context (`AuthContext`).
  - Automatic session hydration via `HttpOnly` refresh token cookie on mount.
  - Transparent token refresh on expiration.
  - Dedicated pages: Registration (`/register`), Login (`/login`), and Protected User Area (`/dashboard`).

### 2. Backend Foundation (`backend/`)
- **Framework**: FastAPI (asynchronous ASGI framework).
- **Settings & Environment**: Centralized Pydantic `BaseSettings` (`app.core.config.Settings`) supporting `development`, `test`, and `production`. Validates production constraints (`DEBUG=False`, cryptographically secure `SECRET_KEY` and `JWT_SECRET_KEY`, non-default database credentials).
- **Database Engine**: SQLAlchemy 2.0 ORM with connection pooling (`QueuePool` with pre-ping for production/development; `NullPool`/`StaticPool` for test isolation).
- **Migrations**: Alembic managing relational database schemas, configured to load centralized settings dynamically without hardcoded credentials.
- **Background Queue**: Celery workers backed by Redis for decoupled long-running execution.

### 3. Authentication & User Management (`backend/app/models/`, `backend/app/core/security.py`)
- **User Entity (`users`)**:
  - UUID primary key.
  - Normalized, unique email address (`email`, indexed).
  - Bcrypt-hashed password (`hashed_password`, 12 rounds).
  - Full name, account status (`is_active`), timestamps (`created_at`, `updated_at`, `last_login_at`).
- **Token Lifecycle & Rotation (`refresh_tokens`)**:
  - **Short-Lived Access Token**: Signed JWT with 15-minute validity, containing `sub` (user UUID), `exp`, `iat`, `type=access`, and `jti`.
  - **Rotating Refresh Token**: Signed JWT with 7-day validity. Stored in PostgreSQL strictly as a SHA-256 hash (`token_hash`) for revocation and reuse detection.
  - **Automatic Rotation**: On every refresh request, the active refresh token is marked revoked and a brand-new token pair is issued. Re-use of a revoked token triggers an audit alert and revokes access.
- **Password Security Policy**:
  - Mandatory complexity: minimum 8 characters, at least one uppercase, one lowercase, one digit, and one special character.
  - Timing-safe password verification via bcrypt.
  - Generic login failure responses ("Invalid email or password") to eliminate user enumeration vectors.
- **Rate Limiting**:
  - Redis sliding window rate limiter (`login_limiter`, `register_limiter`) enforcing max 5 requests per 60 seconds per IP, with a thread-safe in-memory fallback.

### 4. Database Layer & Session Pattern (`backend/app/core/database.py`)
- **Relational Store**: PostgreSQL 16.
- **Session Lifecycle**: Request-safe `get_db()` dependency yielding a scoped `SessionLocal` instance. Automatically triggers `db.rollback()` on uncaught exceptions and guarantees session closure in a `finally` block.
- **Test Isolation**: Tests override `get_db` using `app.dependency_overrides[get_db]` and an isolated in-memory SQLite engine (`sqlite:///:memory:`).
- **Audit Trails**: Base timestamp mixin (`created_at`, `updated_at`) across all domain models.

### 5. Error Handling & Standard Response Shape (`backend/app/core/errors.py`)
All API errors return a uniform, predictable JSON shape:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": null,
    "request_id": "893c5c16-24e5-4712-9c3f-7e9b0629dc62"
  }
}
```
- **Custom Exceptions**: Inherit from `AppError` (`NotFoundError`, `BadRequestError`, `UnauthorizedError`, `ForbiddenError`, `ConflictError`).
- **Validation Errors**: Request validation failures (HTTP 422) are normalized into clean field-path lists without exposing internal traces.
- **Unhandled Exceptions**: Caught by a global fallback handler, returning HTTP 500 with a generic message. Internal stack traces are logged securely alongside the correlation ID and never leaked to the client.

### 6. Correlation IDs & Structured Logging (`backend/app/core/logging.py`, `middleware.py`)
- **Request ID Tracking**: Inbound `X-Request-ID` headers are validated; missing or malformed headers are replaced with a newly generated UUID. The correlation ID is stored in a `contextvars.ContextVar` and echoed on the outgoing response.
- **Structured Output**: Supports both human-readable text (local development) and JSON format (production/Docker).
- **Secret Redaction**: Automatic recursive redaction of sensitive parameters (`password`, `secret`, `token`, `authorization`, `api_key`, `database_url`).

### 7. Audit Event Foundation (`backend/app/core/audit.py`)
- **Schema**: Immutable `AuditEvent` model capturing `event_id`, `timestamp` (UTC), `actor_type`, `actor_id`, `action`, `resource_type`, `resource_id`, `request_id`, and sanitized `metadata`.
- **Authentication Events**: Emits `auth.register`, `auth.login`, `auth.login_failed`, `auth.token_refresh`, `auth.logout`, and `auth.token_revocation_alert`.
- **Resume Studio Events**: Emits `resume.upload`, `resume.parsed`, `resume.upload_version`, `resume.download`, and `resume.delete`.
- **Default Sink**: `LoggingAuditSink` routing events to the `nexora.audit` structured log stream with automatic sanitization of sensitive data.

### 8. Resume Studio: Upload, Parsing & Versioning (`backend/app/services/resume_parser.py`, `storage.py`, `models/resume.py`)
- **Data Models**:
  - `Resume`: UUID primary key, scoped to `user_id` (foreign key with `ondelete=CASCADE`), `title`, and pointer to `current_version_id`.
  - `ResumeVersion`: UUID primary key, `resume_id` foreign key, sequential `version_number` with unique constraint `(resume_id, version_number)`, original filename, file type, file size, internal storage path, parsing status (`uploaded`, `processing`, `parsed`, `failed`), `parsed_content` (PostgreSQL JSONB), `raw_text`, and user-safe `error_summary`.
- **Storage Abstraction (`LocalStorageService`)**:
  - Secure path isolation: `{base_dir}/{user_id}/{resume_id}/{version_id}_{sanitized_filename}`.
  - Strict path traversal defenses: checks relative path against base directory via `Path.resolve()` and `Path.relative_to()`.
  - Never leaks raw filesystem paths or storage hierarchy in API responses.
- **File Validation**:
  - Format validation against allowed extensions (`.pdf`, `.docx`).
  - Magic byte binary signature validation (`%PDF` for PDF, `PK\x03\x04` for DOCX) preventing file spoofing.
  - Configurable maximum size check (`MAX_UPLOAD_SIZE_BYTES=10MB`).
- **Deterministic Parsing Engine**:
  - Zero third-party SaaS or LLM dependencies: pure Python extraction using `pypdf` and `python-docx`.
  - Heuristic structured section segmentation (Summary, Skills, Work Experience, Education, Projects, Certifications).
  - Regex-based contact extraction (name heuristics, email, phone, web/portfolio links).
  - Graceful handling of unparseable or scanned documents: sets `parsing_status=failed` with actionable user guidance without throwing uncaught server errors.
- **User Scoping & Isolation**:
  - Every resume and version query is filtered by `user_id == current_user.id`.
  - Unowned resume requests return HTTP 404 (Not Found) without leaking the existence of other users' resumes.

### 9. AI Resume Intelligence (`backend/app/services/ai/`, `backend/app/models/analysis.py`)
- **Multi-Provider Abstraction (`AIProvider`)**:
  - Official, maintained SDKs: Google Gemini (`google-genai`) and OpenAI (`openai`).
  - Provider selection configured server-side via `AI_PROVIDER` (`gemini`, `openai`, `none`).
  - Configurable models (`GEMINI_MODEL`, `OPENAI_MODEL`).
  - Strict server-side secret management: API keys are loaded via environment variables and never leaked to the client, frontend, logs, or audit metadata.
- **Persistent Analysis Model (`ResumeAnalysis`)**:
  - Linked to `user_id`, `resume_id`, and `version_id` (all foreign keys with `ondelete="CASCADE"`).
  - Stores status (`pending`, `processing`, `completed`, `failed`), provider, model, validated structured output (`result` in PostgreSQL JSONB), token usage, estimated cost, and timestamps.
  - Caching & Deduplication: Returns existing completed analysis for identical resume version and provider/model unless `force_refresh=True` is explicitly passed.
- **Evidence-Grounded Structured Output**:
  - Pydantic schema enforcing structured outputs with explicit evidence citations (`EvidenceItem(section, excerpt)`).
  - Evaluates:
    - **Candidate Profile**: Stated summary, core technical domains, career level estimate (clearly labeled as an estimate).
    - **Skills Evidence Audit**: Categorized skills, supported skills (substantiated by work experience), unevidenced skills (listed but lacking context). Unverified disclaimer.
    - **Experience Evidence**: Explicit measurable outcomes vs. vague claims.
    - **Resume Strengths & Opportunities**: Actionable feedback with source references.
    - **Role Suitability**: Heuristics for 7 standardized role families (e.g. AI / ML Engineer, Full Stack, Python Backend Developer) with heuristic disclaimer.
    - **Prioritized Recommendations**: High/Medium/Low priority cards.
- **Security & Reliability Safeguards**:
  - Prompt Injection Defense: Resume text is wrapped inside `<RESUME_DOCUMENT>` tags and treated as untrusted external data. The system prompt instructs the model to ignore any embedded directives.
  - Token Budget & Truncation: Hard ceiling on input length (`AI_MAX_INPUT_CHARS=25000`) protecting against excessive token costs or buffer exhaustion.
  - Bounded Retries & Timeout: Bounded retry policy for transient errors (429/timeout/503) without infinite retry loops. Safe HTTP 503 (`AI_CONFIG_ERROR`) if provider credentials are not configured.
- **Privacy & Audit Logging**:
  - Emits `resume.analysis_requested`, `resume.analysis_completed`, and `resume.analysis_failed`.
  - Audit metadata captures execution timing, provider, and token counts, strictly omitting resume text, candidate contact details, and API keys.

### 10. Company Discovery & Provenance (`backend/app/models/company.py`, `services/company_service.py`)
- **Data Model (`companies`)**:
  - UUID primary key.
  - Raw and normalized company names (`name`, `normalized_name`) and extracted lowercase domain (`normalized_domain`) for deduplication.
  - Category taxonomy: `product_company`, `mnc`, `gcc`, `big_four`, `large_it_services`, `established_startup`, `other`.
  - Geographic footprint: Headquarters country & city, `operating_regions` (PostgreSQL JSONB).
  - Tags: `industry_tags`, `technology_tags` (PostgreSQL JSONB).
  - Careers portal URL (`careers_url`), official website, size band, and description.
  - Verification state machine: `verified`, `corroborated`, `unverified`, `suspicious`. Transitions to verified or corroborated mandate concrete `verification_notes` and update `last_verified_at`.
  - Scoping & Authorization: `created_by_user_id` (foreign key to `users.id`, ondelete="SET NULL") and `is_global` flag. Global records are read-only to regular users and modifiable only by admins.
  - Consolidation flag: `is_merged` and `merged_into_company_id` for auditable deduplication history.
- **Multi-Source Provenance (`company_sources`)**:
  - Captures granular discovery citations (`official_website`, `careers_page`, `public_directory`, `user_added`, `curated_dataset`, `other`).
  - Records `source_name`, `source_url`, `evidence_summary`, `first_seen_at`, and `last_checked_at`.
- **Deduplication & Explicit Merge Architecture**:
  - Duplicate detection matches on identical normalized domain (high confidence) or normalized legal-stripped name (medium confidence).
  - Explicit merge operation (`POST /api/v1/companies/{id}/merge`):
    - Transfers all provenance sources from secondary to target record with provenance attribution.
    - Fills missing target fields and merges tags without duplicates.
    - Marks secondary company as merged (`is_merged=True`) and archives it from active search.
    - Emits auditable `company.merged` event.
- **SSRF URL Guard (`backend/app/core/url_validator.py`)**:
  - Strictly limits URL schemes to `http` and `https`.
  - Blocks loopback (`127.0.0.0/8`, `::1`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local/cloud metadata (`169.254.169.254`, `fe80::/10`), and internal hostnames.
  - Performs DNS resolution checks to prevent DNS rebinding attacks.

### 11. Job Discovery & Ingestion Architecture (`backend/app/models/job.py`, `services/job_service.py`)
- **Job Entity (`jobs`)**:
  - UUID primary key.
  - Optional `company_id` foreign key (`companies.id`, `ondelete="SET NULL"`). Unassociated jobs remain `company_id = None` without assuming or forcing false company ties.
  - Raw and normalized titles (`title`, `normalized_title` stripping punctuation and normalizing Roman numerals).
  - Verbatim job description text (`description`).
  - Strict explicit salary values (`salary_min`, `salary_max`, `salary_currency`, `salary_period`) — strictly unpopulated unless explicitly stated in the source.
  - Role family taxonomy (`backend_engineer`, `frontend_engineer`, `full_stack_engineer`, `ai_ml_engineer`, etc.), seniority level (`entry_level`, `mid_level`, `senior`, `internship`), and work arrangement (`onsite`, `hybrid`, `remote`, `unspecified`).
  - Geographic fields: `location_text`, `city`, `state_province`, `country`, and `remote_eligibility_regions` (PostgreSQL JSONB).
  - Source tracking & canonical deduplication: `job_url`, `application_url`, `external_source_id`, and `canonical_url_hash` (SHA-256 of tracking-stripped URL).
  - Verification & Status Lifecycle: `job_status` (`active`, `expired`, `closed`, `suspicious`), `verification_status` (`verified`, `corroborated`, `unverified`, `expired`, `suspicious`), `verification_notes` (mandatory for verified status), and timestamps (`first_seen_at`, `last_seen_at`, `last_checked_at`, `last_verified_at`).
  - Scoping: `created_by_user_id` and `is_global` flag.
- **Job Source Provenance (`job_sources`)**:
  - Granular provenance records (`careers_page`, `official_api`, `permitted_feed`, `user_added`, `curated_record`, `other`).
  - Captures `source_name`, `source_url`, `external_id`, `evidence_summary`, `first_seen_at`, and `last_seen_at`.
- **Company Association Algorithm**:
  - Direct association if valid `company_id` provided.
  - Automated association matches exact normalized domain in `job_url` against active company records.
  - Secondary fallback matches unambiguous normalized company name hint.
  - When ambiguous or unresolvable, the record is safely retained as an unassociated job.
- **Idempotent Ingestion Pipeline**:
  - Ingestion endpoint (`POST /api/v1/jobs/ingest/feed`) accepts structured batches.
  - Idempotent duplicate resolution: matching `canonical_url_hash` updates `last_seen_at` and `last_checked_at` and records source citations without generating duplicate job listings.
  - Safe error recovery: captures per-item errors without failing the batch.
- **Audit Logging**:
  - Emits `job.created`, `job.updated`, `job.verified`, `job.source_added`, `job.source_deleted`, and `job.feed_ingested`.

### 12. Job Verification & Freshness Architecture (`backend/app/models/job.py`, `services/job_service.py`, `core/url_validator.py`)
- **Immutable Verification History (`job_verifications`)**:
  - Dedicated table recording every verification check and evidence review over time.
  - Fields: `id`, `job_id`, `verifier_type` (`system`, `user`), `verifier_user_id` (nullable FK to `users.id`), `evidence_type` (`careers_page`, `permitted_api`, `announcement`, `user_evidence`, `other`), `evidence_url`, `evidence_summary`, `observed_status` (`active`, `closed`, `removed`, `expired`, `unknown`), `verification_outcome` (`verified`, `corroborated`, `unverified`, `expired`, `suspicious`), `reason` (mandatory rationale), `checked_at`.
  - Cascades on delete with parent job, preserves immutable history across sequential checks.
- **Freshness Tier Calculation**:
  - Deterministic evaluation based on elapsed days since `last_checked_at`:
    - `recent`: $\le 7$ days (configurable via `JOB_FRESHNESS_RECENT_DAYS`)
    - `due_for_review`: $7$ to $14$ days (configurable via `JOB_FRESHNESS_DUE_DAYS`)
    - `stale`: $> 14$ days
    - `unknown`: No check timestamp recorded
  - Reflected on all job representations (`JobResponse.freshness`, `JobDetailResponse.freshness`) and filterable via `GET /api/v1/jobs?freshness=...`.
- **Connection-Time SSRF-Safe Rechecking (`backend/app/core/url_validator.py`)**:
  - `safe_check_url_status`: performs safe HTTP availability check.
  - Multi-hop redirect protection: re-validates hostname and IP against private/loopback/cloud-metadata CIDRs at every hop.
  - Recheck outcomes:
    - HTTP 200..399: updates `last_checked_at`, records `system` verification with `observed_status="active"`.
    - HTTP 404/410: updates `last_checked_at`, automatically marks `job_status="closed"` and logs `expired`/`removed` verification record.
    - SSRF violation: blocks connection, marks `verification_status="suspicious"`, logs security audit alert.
    - Connection timeout or ambiguous status: records `manual_evidence_required` check requesting user verification.
- **Manual Evidence Submission (`POST /api/v1/jobs/{job_id}/verifications`)**:
  - Allows verified users or administrators to submit verifiable proof URLs, observed status, and mandatory rationale.
  - Persists new immutable `JobVerification` entity and updates denormalized job verification status.
- **Audit Logging**:
  - Emits `job.verified`, `job.evidence_submitted`, `job.rechecked`, `job.recheck_blocked`, and `job.recheck_inconclusive`.

### 13. Job Matching & Ranking Engine Architecture (`backend/app/models/match.py`, `services/matching_engine.py`, `services/matching_service.py`)
- **Deterministic, Explainable Scoring Algorithm**:
  - Fast, grounded, and reproducible matching algorithm (`MatchingEngine`, version `v1.0-deterministic`) that evaluates candidate resumes against discovered opportunities without black-box or non-deterministic LLM calls.
  - **Baseline Dimension Weights**:
    - Technical Skills Alignment: 35% ($w = 0.35$)
    - Role Family & Title Fit: 25% ($w = 0.25$)
    - Seniority & Experience Level: 15% ($w = 0.15$)
    - Geographic & Work Arrangement: 15% ($w = 0.15$)
    - Compensation & Salary: 10% ($w = 0.10$)
- **Undisclosed Salary Integrity & Weight Reallocation**:
  - When a job listing does not disclose salary or the user specifies no minimum salary preference, `salary_score` is set to `None` with `salary_status="undisclosed"`.
  - The 10% compensation weight is dynamically reallocated across the remaining 4 dimensions ($w_{skills} = 0.3889$, $w_{role} = 0.2778$, $w_{exp} = 0.1667$, $w_{loc} = 0.1667$), guaranteeing that an undisclosed salary never depresses or penalizes candidate match scores.
- **Separate Trust Adjustments**:
  - Listing freshness and verification provenance are separated into a distinct score modifier (`trust_adjustment`), ensuring candidate qualification scores are never conflated with listing metadata:
    - Freshness: `recent` (+2), `stale` (-3)
    - Verification: `verified` (+3), `corroborated` (+2), `suspicious` (-30), `closed`/`expired` (-25)
- **Grounded Evidence & Gap Classification**:
  - Positive signals cite specific resume sections (`Projects`, `Experience`, `Skills`) and verbatim text excerpts (`SignalEvidenceRef`).
  - Gaps are explicitly partitioned into `type="missing"` (employer omitted structured requirements; treated neutrally) vs `type="mismatch"` (direct conflict with candidate seniority or preferences).
- **Negative Exclusions & Deductions**:
  - Deducts penalty points and adds gap signals for user-excluded role titles (-25), excluded keywords (-20), or excluded company industries (-20).
- **Persistence & Idempotency**:
  - `user_matching_preferences`: Persists target roles, locations, work arrangements, min salary, priority skills, and negative exclusions.
  - `job_matches`: Persists match score, score breakdown JSON, positive signals JSON, gap signals JSON, `is_saved`, `is_dismissed`, and engine version.
  - Idempotent upsert via unique constraint `uq_user_job_version_engine (user_id, job_id, version_id, engine_version)`.
- **Multi-Tenant Scoping & Security**:
  - Every match execution, preference query, and match mutation is strictly scoped to `current_user.id`.
- **Audit Logging**:
  - Emits `match.generated`, `match.preferences_updated`, `match.saved`, and `match.dismissed`.

### 14. Resume Tailoring Studio Architecture (`backend/app/models/tailoring.py`, `services/tailoring_*.py`, `services/latex_*.py`, `frontend/src/app/dashboard/resumes/tailor/`)
- **Zero-Fabrication & Factual Integrity Standard**:
  - Nexora strictly enforces zero-fabrication: the system never invents technologies, programming languages, metrics, achievements, companies, dates, or degrees.
  - Every proposed modification is classified into legitimate refinement types (`wording_improvement`, `restructuring`, `relevance_improvement`, `keyword_alignment`) and must cite verbatim supporting evidence from the candidate's existing resume (`supporting_evidence: {"section": "...", "excerpt": "..."}`).
  - Job requirements not evidenced in the candidate's resume are categorized under `missing_requirements` and strictly omitted from tailored resume content.
- **Tailoring Workspace Data Model**:
  - `resume_tailoring_sessions`: Scoped to `user_id`, `resume_id`, `version_id` (base version), and `job_id`. Tracks active LaTeX source, grounded job requirement analysis, provider/model, and status (`ready`, `saved`).
  - `resume_tailoring_changes`: Individual structured proposed modifications linked to the session. Tracks `original_content`, `proposed_content`, `user_content`, `status` (`pending`, `accepted`, `rejected`, `modified`), `order_index`, and citation evidence.
  - `resume_versions` extension: Extends version records with `parent_version_id`, `job_id`, `tailoring_session_id`, `is_tailored`, `latex_source`, and `tailoring_metadata`. Original parent resume versions remain strictly immutable.
- **AI Tailoring Engine & Multi-Provider Abstraction (`backend/app/services/tailoring_engine.py`)**:
  - Pluggable provider architecture supporting configured Gemini and OpenAI endpoints with temperature controls ($T=0.2$) and strict injection defense.
  - Deterministic Grounded Engine fallback (`v1.0`): Guarantees high-quality, truthful improvements for professional summaries, prioritized skill groupings, and action-oriented bullet enhancements without external API dependencies.
- **Sandboxed LaTeX Compilation & Layout Renderer (`backend/app/services/latex_compiler.py`)**:
  - **Sandbox Security Guard**: Token-level scanner rejects dangerous command execution directives (`\write18`, `\sys_exec`, `\input`, `\include`, `\openin`, `\openout`, `\newwrite`, `\directlua`, etc.) with HTTP 400.
  - **Execution Isolation**: When `pdflatex` is available, runs in an isolated temporary directory with `-no-shell-escape` and timeout limits.
  - **High-Fidelity ReportLab Fallback**: Minimal Docker containers compile standard A4 resumes directly using ReportLab, guaranteeing 100% sandboxed execution, zero shell invocation, and instant PDF rendering.
- **Frontend 3-Panel Tailoring Workspace (`frontend/src/app/dashboard/resumes/tailor/`)**:
  - **Left Panel (Job & Alignment)**: Target requisition details, matching skills badges, missing qualification alerts, and truthful terminology opportunities.
  - **Center Panel (Editor & Review)**:
    - Tab 1: AI Suggestion Review with original vs proposed diffs, evidence citations, individual approve/reject/edit controls, and batch actions.
    - Tab 2: Monaco Code Editor (`@monaco-editor/react`) with LaTeX syntax highlighting, line numbers, search/replace, unsaved changes indicator, and save/revert controls.
  - **Right Panel (Live PDF Preview & Export)**: Sandboxed PDF preview iframe, recompile button, native PDF and `.tex` source downloads, and modal to commit the tailored resume as an immutable `ResumeVersion`.
- **Audit Logging**:
  - Emits `tailoring.session_created`, `tailoring.change_status_updated`, `tailoring.batch_changes_updated`, `tailoring.latex_updated`, and `tailoring.version_saved`.

### 15. Application Management System Architecture (`backend/app/models/application.py`, `services/application_service.py`, `frontend/src/app/dashboard/applications/`)
- **Centralized Application Tracker (`job_applications`)**:
  - Persists tracked job applications scoped strictly to `user_id`.
  - Supports standalone manual applications without requiring an existing job requisition or company record.
  - Relational connections: optional foreign keys to `job_id`, `company_id`, `resume_id`, and `resume_version_id`.
  - Tracks `application_channel` (`official_portal`, `email`, `referral`, `external_form`, `other`), `status` (9-stage lifecycle), `submission_confirmed` boolean, `link_opened_at`, `application_url`, `deadline_at`, `next_follow_up_at`, `notes`, recruiter contacts, and flexible metadata JSON.
  - **Non-Destructive Deletion**: Deleting an application deletes associated activities, interviews, and status history via `cascade="all, delete-orphan"`, but preserves shared `Job`, `Company`, and `Resume` entities intact.
- **Strict No-False-Submission Guarantee**:
  - Opening an application link (`POST /api/v1/applications/{id}/open-link`) updates `link_opened_at` without marking `submission_confirmed = true` or automatically transitioning status to `applied`.
  - Submissions require explicit user confirmation.
- **9-Stage Application Pipeline & Immutable Audit History (`application_status_history`)**:
  - Stages: `interested`, `preparing`, `applied`, `shortlisted`, `assessment`, `interview`, `offer`, `rejected`, `withdrawn`.
  - Every status transition creates an immutable historical audit record with `from_status`, `to_status`, optional `note`, and timestamp.
- **Chronological Activity Timeline (`application_activities`)**:
  - Audited activity events tracking submissions, status changes, manual user notes, recruiter communications, interviews, and follow-ups. Full user CRUD for manual notes and activities.
- **Interview & Assessment Manager (`application_interviews`)**:
  - Tracks individual interview and assessment rounds: `round_number`, `interview_type`, `scheduled_at`, `duration_minutes`, `meeting_url`, `interviewers` (JSON list), `preparation_notes`, `feedback`, `outcome` (`pending`, `passed`, `failed`, `cancelled`, `waived`), and `status` (`scheduled`, `completed`, `cancelled`, `rescheduled`).
  - Strict manual control: no automated calendar sync or email sending.
- **100% Real Database Analytics (`GET /api/v1/applications/analytics`)**:
  - Computes exact metrics directly from database rows with zero mock or hardcoded statistics:
    - Total applications, in progress, interviews scheduled, assessments pending, offers, rejections.
    - Upcoming events (deadlines, follow-ups, interviews, assessments) occurring within 14 days.
    - Status distribution counts across all 9 stages.
    - Channel distribution counts across all channels.
    - 6-week rolling activity trend.
- **Frontend Workspace & Integration Shortcuts**:
  - `/dashboard/applications`: Full responsive workspace with KPI summary cards, 9-stage pipeline filter bar, search/channel filters, table with quick status transitions, slide-over detail drawer with timeline and interview scheduler, and manual application entry modal.
  - "Track Application" shortcut links seamlessly integrated on Job Cards (`/dashboard/jobs`), Job Details modal, and Job Matches (`/dashboard/matches`), pre-populating requisition details.
- **Audit Logging**:
  - Emits `application.created`, `application.status_changed`, `application.updated`, `application.link_opened`, `application.deleted`, `application.activity_created`, `application.activity_deleted`, `application.interview_scheduled`, `application.interview_updated`, and `application.interview_deleted`.

### 16. Notification & Reminder System Architecture (`backend/app/models/notification.py`, `services/notification_service.py`, `tasks/reminder_tasks.py`, `frontend/src/app/dashboard/notifications/`)
- **Centralized Persistent Notifications (`notifications`)**:
  - Scoped strictly to `user_id` with foreign key cascade on delete.
  - Fields: `notification_type` (`application_follow_up`, `interview_reminder`, `assessment_reminder`, `application_deadline`, `job_freshness_update`, `task_completion`, `system`), `title`, `message`, `entity_type`, `entity_id`, `action_url`, `is_read`, `read_at`, `scheduled_for`, `delivery_status`, `idempotency_key`, `metadata_json`.
  - Database Indexes & Constraints:
    - Unique constraint `uq_notifications_user_idempotency (user_id, idempotency_key)` guarantees duplicate prevention even under concurrent worker retries.
    - Composite indexes on `(user_id, is_read)` and `(user_id, created_at desc)`.
- **User Notification Preferences (`user_notification_preferences`)**:
  - 1-to-1 relationship with `User`.
  - Configurable category toggles: `enable_in_app`, `enable_interview_reminders`, `enable_assessment_reminders`, `enable_follow_up_reminders`, `enable_deadline_reminders`, `enable_job_freshness_updates`, `enable_task_completion_updates`, `enable_system_notifications`.
  - Scheduling interval controls: `interview_reminder_24h` and `interview_reminder_1h`.
  - Timezone personalization: `preferred_timezone` (validated against standard IANA `zoneinfo`).
  - Disabling categories prevents future notifications without erasing notification history.
- **Automated Celery & Redis Reminder Processing**:
  - Celery task `process_scheduled_reminders_task` registered in worker and beat schedule (15-minute periodic beat).
  - Corrected Non-Overlapping Reminder Windows (Prompt 12.1):
    - **24-hour reminder**: Evaluates when `timedelta(hours=22) <= delta <= timedelta(hours=24, minutes=15)`. Uses a 15-minute execution window with a 2-hour recovery grace period for Celery/Redis restarts.
    - **1-hour reminder**: Evaluates when `timedelta(0) < delta <= timedelta(hours=1, minutes=15)`. Recovers missed reminders down to the exact event start.
    - **No False 24h Triggers**: An event 30 minutes away (`delta = 30m < 22h`) will never trigger a 24-hour reminder, only triggering the 1-hour reminder if enabled.
    - **Zero Past Reminders**: If `delta <= 0` or `scheduled_utc <= now`, no reminders are ever generated for already started or past events.
    - Applied identically to both interview rounds and take-home/online assessments.
  - Timezone-aware message rendering: formats localized event times using the candidate's configured IANA timezone (e.g. `ZoneInfo("America/New_York")`).
  - Exclusion guards: Skips completed or cancelled interviews and rejected or withdrawn applications.
  - Strict idempotency key convention: `reminder:{type}:{interval}:{entity_id}` guarantees zero duplicates across task retries and concurrent workers via database uniqueness constraint `uq_notifications_user_idempotency` with automatic rollback and existing record return upon `IntegrityError`.
- **Frontend Notification Center & Global Bell**:
  - Global `NotificationBell` in dashboard navigation with real-time unread badge, popover dropdown for fast reads and action URL navigation.
  - Dedicated `/dashboard/notifications` workspace with category tab filtering (All, Unread, Interviews, Deadlines, Preferences), mark-all-read action, deletion, and interactive preference manager.
- **Audit Logging**:
  - Emits `notification.created`, `notification.read`, `notification.read_all`, `notification.deleted`, and `notification.preferences_updated`.

### 17. Automated Job Discovery & Source Integrations Architecture (`backend/app/services/discovery/`, `models/company.py`, `tasks/discovery_tasks.py`, `frontend/src/app/dashboard/discovery/`)
- **Modular Source-Adapter Architecture (`backend/app/services/discovery/adapters/`)**:
  - Pluggable, extensible adapter pattern inheriting from `BaseSourceAdapter`:
    - `GreenhouseAdapter`: Consumes Greenhouse v1 public job board API (`https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true`). Supports single-request full job content retrieval with department and location extraction.
    - `LeverAdapter`: Consumes Lever v0 public postings API (`https://api.lever.co/v0/postings/{site}?mode=json`). Extracts structured requirements and lists from `lists` payload.
    - `AshbyAdapter`: Consumes Ashby public job-board API (`https://api.ashbyhq.com/posting-api/job-board/{board_name}`). Parses structured compensation tiers (`compensationTierSummary`) and department metadata.
    - `RSSFeedAdapter`: Parses standard RSS 2.0 and Atom XML feeds with safe XML handling (defending against entity expansion and external entity vulnerabilities) and HTML stripping.
    - `JSONFeedAdapter`: Parses generic JSON job feeds supporting root arrays, nested listing wrappers, and property normalization.
  - Adapter registry (`registry.py`) provides dynamic lookup and supported adapter introspection.
- **SSRF-Safe Outbound Request Engine (`safe_get`)**:
  - Outbound HTTP requests route through `safe_get` wrapping `url_validator.validate_url`.
  - Blocks loopback, private IPv4/IPv6 RFC 1918 subnets, AWS/GCP/Azure link-local cloud metadata addresses (`169.254.169.254`), and prohibited ports.
  - Inspects every HTTP redirect hop to prevent redirect-based SSRF.
  - Adheres to standard polite crawling practices: identified `NexoraBot/1.0` User-Agent, configurable timeout (15s), and exponential backoff on HTTP 429 rate limit responses.
- **Deterministic Job Normalization Engine (`backend/app/services/discovery/normalizer.py`)**:
  - **10 Nexora Role Families**: Deterministic keyword scoring categorizing listings into `Frontend Engineering`, `Backend Engineering`, `Full Stack Engineering`, `Mobile Development`, `DevOps & Cloud Infrastructure`, `Data Engineering`, `Data Science & Machine Learning`, `QA & Test Automation`, `Cybersecurity & InfoSec`, and `Product & Engineering Management`.
  - **Early Career Classification**: Classifies seniority into `fresher` (0-1 yrs, new grad, campus, intern), `junior` (1-3 yrs), `mid` (3-5 yrs), or `senior` (5+ yrs).
  - **Work Arrangement & Employment Type**: Accurately infers `remote`, `hybrid`, or `on_site` and distinguishes `full_time`, `part_time`, `internship`, and `contract`.
  - **Strict Undisclosed Salary Truthfulness**: Extracts explicit compensation figures for INR LPA (supports both Western comma grouping and Indian comma format like `₹8,00,000`), USD, EUR, and GBP. Never invents or infers undisclosed salaries.
  - **Skill Synonym Normalization**: Recognizes and canonicalizes aliases (e.g. `react.js` $\rightarrow$ `react`, `k8s` $\rightarrow$ `kubernetes`, `tailwind` $\rightarrow$ `tailwindcss`, `postgres` $\rightarrow$ `postgresql`).
- **Idempotent Ingestion & Provenance Preservation (`JobDiscoveryService`)**:
  - Deduplication pipeline checks SHA-256 canonical URL hash (`canonical_url_hash`), external source ID (`external_id`), and company-title pair.
  - Preserves user edits on existing jobs while updating freshness timestamps (`last_seen_at`, `last_checked_at`).
  - Automatically records citation provenance in `job_sources` with external source ID and adapter attribution.
  - Automated Corroboration: Sets newly discovered listings to `corroborated` verification status and appends a `job_verifications` audit event (`verifier_type="system"`, `observed_status="active"`, `verification_outcome="corroborated"`). Discovered jobs are never automatically promoted to `verified` without listing-level or human verification.
- **Celery Background Scanning & Audit Logs (`tasks/discovery_tasks.py`, `models/company.py`)**:
  - `scan_all_due_sources_task`: Hourly periodic Celery beat task evaluating enabled sources whose elapsed time exceeds `scan_frequency_hours`.
  - `scan_single_company_source_task`: Async Celery task for on-demand scans.
  - `discovery_scan_logs`: Immutable audit table tracking every scan: `company_source_id`, `company_id`, `adapter_name`, `scan_type` (`manual`, `scheduled`), `status` (`running`, `success`, `failed`, `partial`), `jobs_found`, `jobs_imported`, `jobs_updated`, `error_message`, and execution timings.
- **Frontend Discovery Workspace (`frontend/src/app/dashboard/discovery/`)**:
  - Responsive workspace featuring:
    - Overview KPIs: Active Sources, Total Discovered Opportunities, Jobs Imported Today, Scans Completed Today.
    - Discovered Opportunities Tab: Searchable, filterable list of discovered early-career roles with role family, arrangement, freshness, verification tags, and details modal.
    - Source Integrations Tab: Table of configured sources with active toggle, scan frequency, last scan status badge, manual "Scan Now" button, and "Add Source" modal featuring live connection testing.
    - Scan History Tab: Audit logs table detailing every scan attempt, run duration, jobs found/imported/updated, and error messages.
- **Audit Logging**:
  - Emits `company_source.created`, `company_source.updated`, `company_source.deleted`, `discovery.test_connection`, `discovery.scan_started`, `discovery.scan_completed`, `discovery.scan_failed`, and `job.corroborated`.

---

## 18. AI Job Intelligence & Personalized Recommendations Architecture

Nexora's AI Job Intelligence and Personalized Recommendations system pairs the deterministic, explainable job-matching engine with structured AI description intelligence, deep candidate-to-job compatibility assessments, and balanced recommendation scoring.

### 18.1 Core Components

```
+----------------------------------------------------------------------------------------------------+
|                                    DISCOVERED JOBS & CAREER SOURCES                                |
+----------------------------------------------------------------------------------------------------+
                                                   |
                                                   v
                         +--------------------------------------------------+
                         |       JobDescriptionIntelligenceEngine           |
                         |  Extracts: skills, experience, education, tools, |
                         |  responsibilities, seniority, evidence excerpts  |
                         |  * SHA-256 content_hash caching                  |
                         +--------------------------------------------------+
                                                   |
                                                   v
                                        [job_intelligences]
                                                   |
    +----------------------------------------------+----------------------------------------------+
    |                                                                                             |
    v                                                                                             v
+------------------------------------+                                          +------------------------------------+
|  Deterministic Matching Engine     |                                          |       AIJobMatchEngine             |
|  - Skill alignment (35%)           |                                          |  - Technical compatibility         |
|  - Role family (25%)               |                                          |  - Project & internship alignment  |
|  - Seniority & experience (15%)    |                                          |  - Transferable skills discovery   |
|  - Location & arrangement (15%)    |                                          |  - Actionable gap signals          |
|  - Disclosed compensation (10%)    |                                          |  * SHA-256 assessment_hash caching |
|  * Undisclosed salary neutrality   |                                          +------------------------------------+
+------------------------------------+                                                            |
                  \                                                                              /
                   \                                                                            /
                    \                                                                          /
                     +------------------------------------------------------------------------+
                     |                 Personalized Recommendation Engine                     |
                     |  - Blended scoring: S_rec = 0.60*S_det + 0.40*S_ai (or 1.0*S_det)      |
                     |  - Priority bonuses: Python, AI/ML, GenAI, Frontend, Fullstack, SDE    |
                     |  - Automatic exclusion of dismissed and applied opportunities          |
                     |  - Grounded explanations: Why Matches, Potential Gaps, Next Steps     |
                     +------------------------------------------------------------------------+
                                                   |
                                                   v
                     +------------------------------------------------------------------------+
                     |           Recommendations Workspace (/dashboard/recommendations)       |
                     |  - KPI metrics, multi-dimensional filters, AI Insights modal           |
                     |  - Direct save/dismiss, application pipeline shortcut, refresh controls|
                     +------------------------------------------------------------------------+
```

### 18.2 Structured Job Description Intelligence (`JobIntelligence`)
- **Extraction Schema**: Structured extraction capturing:
  - `required_skills`: Mandated technical and domain competencies.
  - `preferred_skills`: Desirable competencies and nice-to-haves.
  - `min_experience_years` & `max_experience_years`: Explicit experience ranges.
  - `education_qualifications`: Extracted degree levels (B.Tech/BS, MS, etc.).
  - `responsibilities`: Core day-to-day job duties.
  - `tools_and_frameworks`: Libraries, developer tools, and infrastructure.
  - `seniority_level`: Inferred seniority (`fresher`, `junior`, `mid`, `senior`).
  - `work_arrangement`: Extracted arrangement (`remote`, `hybrid`, `on_site`).
  - `salary_min`, `salary_max`, `salary_currency`: Explicit salary only; never fabricated.
  - `evidence_excerpts`: Verbatim citations from the listing supporting extracted fields.
- **Cost Optimization & Caching**:
  - Content SHA-256 hash (`content_hash = SHA-256(title + description + location + arrangement)`).
  - Unmodified job listings reuse stored `job_intelligences` records with 0 AI API overhead.
  - Deterministic fallback (`DeterministicJobAnalyzer`) executes instantly when AI provider is unconfigured or unavailable.

### 18.3 Resume-to-Job AI Compatibility Matching (`AIJobMatch`)
- **Evaluation Criteria**:
  - `compatibility_rating`: `strong`, `moderate`, `potential`, `unlikely`.
  - `fit_score`: Calibrated percentage score (0-100).
  - `strengths`: Concrete matches with verbatim resume and job evidence citations.
  - `skill_gaps`: Missing prerequisites with distinction between trainable vs hard blockers.
  - `experience_alignment`: Evaluation of academic, internship, and project experience.
  - `transferable_skills`: Recognition of adjacent technologies (e.g. Flask/Django $\rightarrow$ FastAPI, React $\rightarrow$ Next.js, C++ $\rightarrow$ Go/Rust, PyTorch $\rightarrow$ TensorFlow).
  - `missing_requirements`: Explicitly missing qualifications without penalizing undisclosed candidate data.
  - `recommendation_rationale`: Grounded prose explaining why the opportunity is suitable.
  - `next_steps`: Concrete preparation steps (tailoring resume, highlighting specific projects).
- **Cost Optimization & Assessment Hashing**:
  - Assessment SHA-256 hash (`assessment_hash = SHA-256(user_id + resume_version_id + job_id + job_content_hash)`).
  - Enforces database unique constraint `uq_user_resume_version_job_ai`.
  - Deterministic fallback (`DeterministicAIMatchEvaluator`) provides rich heuristics and transferable skill detection without external LLM calls.

### 18.4 Blended Recommendation Ranking Engine
- **Formula**:
  $$S_{rec} = \begin{cases} 0.60 \times S_{det} + 0.40 \times S_{ai} & \text{if AI evaluated} \\ S_{det} & \text{otherwise} \end{cases}$$
- **Early-Career & Role Priority Bonuses**:
  - Early-career bonus (+3.0 pts) for `fresher` or `junior` roles.
  - Priority role bonus (+4.0 pts) for listings matching Python, AI/ML, GenAI, Frontend, Full-stack, SDE, and Data Engineering tracks.
- **Undisclosed Salary Standard**:
  - Undisclosed salary is treated as completely neutral ($0.0$ penalty). Listings without disclosed compensation display a reassuring "Salary Undisclosed (Neutral)" indicator.
- **Exclusion Filters**:
  - Jobs previously marked dismissed (`is_dismissed = True`) are automatically excluded.
  - Jobs with active applications (`applied`, `interview`, etc.) are excluded unless `include_applied = True` is selected.

### 18.5 Connection-Time SSRF & DNS Rebinding Protection (`SSRFSafeTransport`)
- Outbound HTTP requests in `BaseSourceAdapter` and URL validation utilize `SSRFSafeTransport` (`app/core/url_validator.py`).
- Intercepts socket TCP connections directly at connection time (`connect_tcp`), resolves the IP, and blocks loopback (`127.0.0.0/8`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and AWS/GCP cloud metadata endpoints (`169.254.169.254`).
- Connection is pinned directly to the validated IP to defeat time-of-check to time-of-use (TOCTOU) DNS rebinding attacks.

---

## 19. AI Application Assistant & Gmail Integration Architecture

### 19.1 Philosophy & Safety Invariants
- **Human In The Loop**: Nexora prepares, formats, drafts, and inspects application materials. Every external submission or dispatch requires deliberate, explicit confirmation by the authenticated user immediately prior to execution.
- **Strict Zero-Fabrication**: Cover letters, recruiter emails, and screening Q&A answers are grounded exclusively in verified facts from the candidate's resume analysis. When candidate-specific details (e.g. work authorization, notice period, compensation expectations) are missing, the system strictly refuses to invent answers and flags `missing_info` for candidate input.
- **Portal Decoupling**: Opening an external company application portal or career URL records a `portal_opened_at` audit timestamp, but **never** marks the application as submitted. Submission confirmation is strictly independent and requires explicit confirmation (`confirm_submission=True`).

### 19.2 Google Cloud Console & OAuth 2.0 Setup
1. **Google Cloud Console Configuration**:
   - Create or select a Google Cloud Project in [Google Cloud Console](https://console.cloud.google.com/).
   - Enable the **Gmail API** and **Google People API** under APIs & Services.
   - Configure the OAuth Consent Screen: User Type: External; add test users if in Testing status.
   - Create Credentials: **OAuth client ID** $\rightarrow$ Application Type: **Web application**.
2. **Authorized Redirect URIs**:
   - `http://localhost:3000/dashboard/application-assistant` (Frontend callback handler)
   - `http://localhost:8000/api/v1/integrations/google/callback` (Backend direct callback handler)
3. **Environment Variables**:
   - `GOOGLE_CLIENT_ID`: OAuth 2.0 Client ID from Google Cloud Console.
   - `GOOGLE_CLIENT_SECRET`: OAuth 2.0 Client Secret.
   - `GOOGLE_REDIRECT_URI`: Configured redirect URI (`http://localhost:3000/dashboard/application-assistant` or backend).
   - `GMAIL_TOKEN_ENCRYPTION_KEY`: 32-byte URL-safe base64 key for Fernet AES-128-CBC + HMAC-SHA256 encryption. If unset, automatically derives a reproducible Fernet key from `SECRET_KEY`.
4. **Least-Privilege Scopes**:
   - `https://www.googleapis.com/auth/userinfo.email`: Resolves connected email identity.
   - `https://www.googleapis.com/auth/gmail.compose`: Creates drafts and sends approved outgoing messages.
   - *Nexora never requests full mailbox read access (`gmail.readonly` or `mail.google.com`).*

### 19.3 Security: Token Encryption & State CSRF Mitigation
- **Token Encryption at Rest (`token_encryption.py`)**:
  - Access and refresh tokens are encrypted prior to database persistence using Fernet symmetric encryption (AES-128-CBC with PKCS7 padding and HMAC-SHA256 authenticated integrity).
  - API responses strictly omit raw and encrypted tokens, exposing only connection status, email address, and granted scopes.
- **Tamper-Proof OAuth State (`oauth_state.py`)**:
  - State token format: `<base64_json_payload>.<hmac_sha256_signature>`.
  - Encodes `user_id`, action (`gmail_connect`), nonce, and UNIX timestamp.
  - Verification validates signature with `SECRET_KEY`, matches user identity, and rejects states older than 15 minutes (900 seconds) or with future timestamps.

### 19.4 Application Preparation Workspace
- **Model**: `ApplicationPreparation` (`application_preparations` table with migration `e431f850829f`).
- **Milestone Checklist Items**:
  1. `review_job`: Review role responsibilities and requirements.
  2. `select_resume`: Choose target resume and version.
  3. `tailor_resume`: Shortcut to Resume Tailoring Studio.
  4. `generate_cover_letter`: Synthesize and approve tailored cover letter.
  5. `prepare_recruiter_email`: Compose and approve outreach/application email.
  6. `review_qa_answers`: Review truthful answers to screening questions.
  7. `prepare_documents`: Validate required attachments ($\le 10$MB).
  8. `open_application_portal`: Visit external career portal.
  9. `confirm_application_submitted`: Confirm external submission completed.
- **Progression Statuses**: `not_started`, `in_progress`, `ready_for_review`, `completed`.

### 19.5 AI Cover Letter Generator & PDF Export
- **Grounding Strategy**:
  - Analyzes role requirements from `Job` and verified achievements from `ResumeAnalysisResult`.
  - Generates structured sections: `opening`, `body_paragraphs` (with skills alignment and specific experience citations), and `closing`.
  - Fallback engine: `DeterministicCoverLetterGenerator` ensures high quality even in offline or API-constrained environments.
- **ReportLab PDF Compilation (`cover_letter_pdf.py`)**:
  - Generates polished, single-page A4 PDF documents with professional typography, candidate header, recipient block, clean margins, and page numbers.

### 19.6 Recruiter Email & Gmail Dispatch Workflow
- **6 Supported Communication Types**:
  1. `direct_application`: Formal job application submission.
  2. `recruiter_outreach`: Direct recruiter introduction and interest pitch.
  3. `referral_request`: Polite internal employee referral request.
  4. `follow_up`: Respectful status inquiry post-application.
  5. `interview_follow_up`: Re-alignment of strengths after an interview round.
  6. `thank_you`: Post-interview gratitude note.
- **Anti-Guessing Guardrail**: Nexora never guesses recruiter email addresses. Recipient emails must be explicitly provided by the user or pre-existing on the application record.
- **Gmail Draft Creation**:
  - Builds RFC 2822 MIME message (`email.mime.multipart.MIMEMultipart`) with optional resume and cover letter PDF attachments.
  - Calls Gmail API `POST /gmail/v1/users/me/drafts`, storing `gmail_draft_id`.
- **Direct Dispatch & Duplicate-Send Prevention**:
  - Requires explicit confirmation immediately before execution: payload must include `confirm_send=True`.
  - If email has already been sent (`status == 'sent'`), further dispatch calls are strictly rejected with HTTP 400.
  - Attachment safety: Enforces maximum total attachment size $\le 10$MB (`10,485,760` bytes) and validates storage paths to prevent path traversal leaks.

### 19.7 Audit & Activity Logging
- Logs security and operational events to `audit_logs` and `application_activities`:
  - `cover_letter_generated`, `cover_letter_approved`
  - `recruiter_email_generated`, `recruiter_email_approved`
  - `gmail_draft_created`, `email_sent`
  - `portal_opened`, `application_submitted`

---

## 20. AI Interview Preparation & Interview Coach Architecture

### 20.1 Overview & System Invariants
The AI Interview Preparation & Coaching module provides personalized preparation sessions grounded in the candidate's verified resume analysis, target job requisition, hiring company profile, and application stage.

Core invariants enforced:
1. **Zero Fabrication**: All preparation plans, project deep-dive breakdowns, and practice questions strictly anchor to verified skills, projects, and experiences evidenced in `ResumeAnalysisResult`.
2. **Safe Code Evaluation**: Submitted code is evaluated strictly statically (`SafeStaticCodeAnalyzer`) using Python's standard `ast` parser to inspect functions, control loops, and syntax errors. Arbitrary code is NEVER executed on the application server.
3. **Multi-Category & Tier Calibration**: 10 specialized categories (`technical`, `coding_problem_solving`, `backend_python`, `frontend_fullstack`, `ai_ml_genai`, `database_sql`, `system_design`, `project_deep_dive`, `internship_experience`, `behavioral_hr`) across 3 difficulty tiers (`beginner`, `intermediate`, `advanced`).
4. **Standardized Rubric Scoring**: Candidate answers are scored on a 0-100 scale using a 6-dimension weighted rubric:
   $$\text{Overall Score} = 0.30 \times \text{Correctness} + 0.20 \times \text{Relevance} + 0.20 \times \text{Completeness} + 0.10 \times \text{Clarity} + 0.10 \times \text{Approach} + 0.10 \times \text{Communication}$$
5. **Decoupled Application Status**: Mock interview scores are for preparation only; they never automatically alter the application's actual stage or outcome in the tracker.

### 20.2 Data Models & Relational Architecture
- **`InterviewPreparationSession` (`interview_preparation_sessions`)**:
  - Primary key: `id` (UUIDv4)
  - Scoped to `user_id`, optional FKs: `job_id`, `company_id`, `application_id`, `resume_version_id`.
  - Tracks: `interview_round`, `interview_type`, `difficulty`, `status` (`in_progress`, `completed`, `abandoned`), `total_questions`, `completed_questions`, `average_score`, `preparation_plan` (JSONB).
- **`InterviewQuestion` (`interview_questions`)**:
  - `session_id`, `question_order` (1-indexed), `category`, `difficulty`, `question_text`, `context_hint`, `expected_points` (JSONB array), `evaluation_criteria` (JSONB), `ideal_answer_outline`, `project_name`.
- **`InterviewAnswer` (`interview_answers`)**:
  - `question_id`, `session_id`, `user_id`, `answer_text`, `submitted_code`, `submitted_language`, `word_count`, `time_spent_seconds`.
- **`InterviewEvaluation` (`interview_evaluations`)**:
  - One-to-one with `InterviewAnswer`. Stores scores for the 6 rubric dimensions and overall score (0.0 to 100.0).
  - Feedback lists: `strengths`, `missing_points`, `suggested_improvements`, `stronger_answer_example`, `evaluation_feedback`.
  - Provider provenance: `provider`, `model`, `is_deterministic_fallback`.
- **`InterviewPreparationNote` (`interview_preparation_notes`)**:
  - Scoped to `user_id`, optional `session_id` and `application_id`.
  - Categories: `topics_to_revise`, `questions_to_ask`, `company_research`, `checklist`, `general`.
  - Supports pinned status (`is_pinned`) and checklist items (`checklist_items` JSONB).

### 20.3 AI Engine & Fallback Architecture
- **Plan Generation (`InterviewPrepEngine`)**: Generates structured technical topics, project talking points, internship anchors, and skill gap mitigations.
- **Question Generation (`InterviewQuestionEngine`)**: Employs prompt templates with structured JSON outputs and `DeterministicQuestionGenerator` featuring curated question banks for all 10 categories and 3 difficulty tiers.
- **Answer Evaluation (`InterviewEvaluationEngine`)**: Evaluates submissions against rubric expectations with `SafeStaticCodeAnalyzer` and `DeterministicEvaluationEngine`.
- **Project Deep-Dive Studio (`ProjectPrepEngine`)**: Structures candidate projects into STAR frameworks (pitch, architecture, implementation, bottlenecks, scalability, practice questions).

### 20.4 Performance Analytics & Scheduling
- **Analytics Aggregator (`InterviewPrepService.get_analytics`)**:
  - Calculates real metrics from completed evaluations: overall average, technical average, behavioral average, category breakdown, score trends, strong areas ($\ge 75\%$), and weak areas ($< 70\%$).
- **Reminder Integration**:
  - Connects to existing `NotificationService` infrastructure to schedule automated reminder alerts with celery background worker execution.

---

## 21. Company Intelligence & Employer Research Architecture

### 21.1 Overview & System Invariants
The Company Intelligence module provides candidates with transparent, evidence-grounded research on hiring organizations prior to applying or interviewing.

Core invariants enforced:
1. **Zero Fabrication**: Company headcount, revenue, and funding are only reported when verifiable evidence exists in official sources. Missing or non-disclosed metrics are explicitly labeled `"Undisclosed"` or `"Not publicly evidenced"`.
2. **Provenance & Evidence Tiers**: Every identified technology is classified into one of four evidence strengths:
   - `confirmed`: Direct official mention in company web pages, engineering blogs, or technical publications from **verified official domains**.
   - `supported`: Mentioned across 2 or more active job requisitions in the Nexora database.
   - `inferred`: Derived from 1 open job requisition, company profile tags, or unverified/third-party syndicated sources with transparent attribution.
   - `unknown`: When evidence is ambiguous or unverified.
3. **Safe Public Web Research**: All outbound HTTP fetches use `SSRFSafeTransport` with connection-time DNS rebinding validation, blocking access to private/internal CIDRs, loopbacks, and cloud metadata services. Responses are stream-checked with a hard 2MB size cap and multi-hop redirect destination validation.
4. **Hiring Truth Grounding**: Aggregated hiring trends (active jobs, entry-level, internships, top categories, locations) are calculated strictly from discovered job records in the Nexora database, distinguishing active from expired/stale postings.
5. **Grounded Candidate Fit & Tenant Isolation**: Evaluates alignment between verified resume skills, user career preferences, and company technologies without exaggerating candidate qualifications. User resume version ownership is strictly verified.
6. **Deterministic Caching & Stale Invalidation**: 10-section research reports compute a SHA-256 digest of `(company_id, source_content_hash, candidate_skills, job_ids, jobs_fingerprint)`. If intelligence is updated or job statuses change, cached reports are invalidated.
7. **Strict Platform Compliance**: Operates in compliance with robots.txt and public terms of service. Does not perform unauthorized scraping behind authentication gates, paywalls, or anti-bot challenges (e.g. Cloudflare Turnstile/CAPTCHA).

### 21.2 Data Models & Relational Architecture
- **`CompanyIntelligence` (`company_intelligence`)**:
  - One-to-one with `Company`. Stores `overview`, `industry_domain`, `headquarters`, `operating_locations`, `website_url`, `careers_url`, `products_and_services` (JSONB), `technology_stack` (JSONB), `size_band`, `size_evidence`, `funding_ownership_info`, `recent_developments` (JSONB), `hiring_summary` (JSONB), `source_content_hash`, `last_researched_at`, `is_stale`, `provenance_sources_count`.
- **`CompanyResearchSource` (`company_research_sources`)**:
  - Many-to-one with `Company`. Stores `source_type` (`official_website`, `careers_page`, `news_release`, `engineering_blog`, `investor_relations`, `public_feed`), `source_url`, `final_url` (tracks redirects), `title`, `content_snippet`, `raw_content`, `content_hash` (SHA-256), `retrieved_at`, `is_verified` (True only for verified company + matching official domain).
- **`CompanyResearchReport` (`company_research_reports`)**:
  - Scoped to `user_id` and `company_id`. Stores `report_title`, `sections` (10-section dictionary), `candidate_fit` (JSONB), `source_evidence` (JSONB array), `content_hash` (SHA-256 cache key), `provider`, `model`, `is_cached`, `is_deterministic_fallback`. Fully deletable by owner via `DELETE /company-intelligence/reports/{id}`.

### 21.3 Public Web Ingestion & Multi-Source Coverage
The `CompanyResearchCoordinator` coordinates public evidence discovery and collection across 6 genuine source categories:
1. **Official Company Websites**: `OfficialWebsiteAdapter` fetches homepage, `/about`, and `/company`.
2. **Company Newsrooms & Press Releases**: `CompanyNewsroomAdapter` discovers `/news`, `/press`, `/newsroom`, and configured news sources.
3. **Engineering Blogs & Tech Docs**: `EngineeringBlogAdapter` discovers `/blog`, `/engineering`, `/techblog`, and configured engineering URLs.
4. **Investor Relations & Public Disclosures**: `InvestorRelationsAdapter` discovers `/investors`, `/ir`, `/investor-relations` for corporate reports.
5. **Permitted Public RSS/Atom Feeds**: `RSSFeedAdapter` safely parses RSS 2.0 and Atom feeds, blocking DTD/entity expansion (XXE protection).
6. **Permitted Public JSON Feeds**: `JSONFeedAdapter` parses standard JSON Feed 1.1 streams.

### 21.4 Content Security & Crawl Policy Defense
- **Automated Robots.txt Enforcement (`RobotsPolicyEnforcer`)**:
  - Automatically fetches, parses, and caches `robots.txt` per domain (1-hour TTL).
  - Evaluates explicit user-agent directives for `NexoraBot` before falling back to `*`.
  - **Strict Disallow on Policy Failure**: If `robots.txt` cannot be retrieved or policy cannot be safely established due to HTTP 401, 403, 5xx, or network timeouts, Nexora halts the crawl and logs the failure. Only HTTP 404 (absence of policy) defaults to permitted crawling.
  - **Redis-Backed Distributed Crawl Pacing & Crawl-Delay Directives**: Honors full valid `Crawl-delay` directives (e.g. 5s or 15s, never capped below the site's valid directive) with a default 0.5-second pacing floor. Enforces atomic slot reservation across multiple Python worker processes (FastAPI backend and Celery workers) using a single-threaded Redis Lua script. The script atomically obtains the authoritative timestamp using Redis `TIME` with microsecond precision (`%.6f`), calculating wait durations and scheduling subsequent slots entirely within Redis to ensure complete immunity to local worker clock skew (ahead or behind). Pacing applies to normalized domain keys (`nexora:crawl_pacing:{domain_key}` with zero credentials, paths, or query params). Calling workers sleep for the assigned slot duration before executing outbound requests. Sensible key TTL (`max(int(delay * 3), 300)`) cleans up idle domain schedules.
  - **Redis Failure & Degraded Behavior**: When Redis is unreachable or times out, Nexora logs the coordination failure without exposing secrets, explicitly flags the degraded mode (`degraded_conservative_local`), and applies a conservative local delay floor (`max(delay, 2.0s)`), never claiming global coordination when operating locally. Optional `defer_on_coordination_failure` defers crawling (`CRAWL_COORDINATION_DEFERRED`, HTTP 503). Robots.txt and SSRF defenses remain 100% active.
  - **Request Deduplication**: Tracks visited URLs in memory per crawl session to eliminate duplicate requests.
  - **Anti-Bot & Paywall Non-Bypass**: Detects Cloudflare Turnstile, CAPTCHAs, challenge scripts (`cf-mitigated`, `challenge-platform`, `just a moment...`), and paywalls. Never bypasses authentication, paywalls, or anti-bot protections; halts immediately and records diagnostic reason.
  - **Division of Responsibility**: Nexora guarantees strict robots.txt compliance, SSRF protection, size caps, rate limiting, and prompt-injection neutralization. Users remain responsible for configuring legitimate public URLs and must not supply credentials or proprietary intranet URLs.
- **Connection-Time IP Pinning (`SSRFSafeTransport`)**: Resolves hostnames and verifies socket destination IPs immediately prior to TCP handshake, defeating DNS rebinding attacks.
- **Decompression Bomb Protection**: Streams responses chunk by chunk and halts at 2MB (`MAX_RESPONSE_BYTES`).
- **Prompt Injection Neutralization & Untrusted Enclosure**:
  - `sanitize_untrusted_content` strips and filters instruction-override patterns (`ignore previous instructions`, `system prompt:`, `assistant:`, `you are now DAN`, etc.) and defuses container closing tags (`</UNTRUSTED` -> `<_UNTRUSTED`).
  - LLM prompt constructs `<UNTRUSTED_EXTERNAL_EVIDENCE_CATALOG>` with isolated `<EVIDENCE_ITEM>` and `<PASSIVE_EXCERPT>` wrappers.
  - Caps individual source snippets at 800 characters and aggregate catalog payload at 4,000 characters.
  - System instructions enforce strict immunity invariants: the model is barred from following directives, changing roles, revealing secrets/prompts, or invoking tools regardless of content inside source excerpts.
- **Multi-Hop Redirect Validation**: Validates each redirect hop URL against scheme and hostname policies.

### 21.5 10-Section AI Research Dossier
- Structured sections:
  1. `overview`: Company overview and mission
  2. `products_and_services`: Products, services, and business model
  3. `technology_landscape`: Technology landscape and engineering stack
  4. `engineering_culture`: Engineering culture, practices, and public technical work
  5. `hiring_activity`: Hiring activity and growth trends
  6. `entry_level_opportunities`: Relevant entry-level and fresher opportunities
  7. `candidate_alignment`: Candidate-company alignment (skills, strengths, gaps)
  8. `interview_prep_topics`: Recommended interview preparation topics
  9. `recruiter_interviewer_questions`: Thoughtful questions to ask recruiters and interviewers
  10. `sources_and_evidence`: Sources and evidence summary with verification and provenance citations

### 21.6 Authorization & Tenant Isolation Matrix
The Company Intelligence module separates shared organizational research from candidate-specific private data across all 10 endpoints:

| Endpoint | Access Level | Tenant Isolation & Security Control |
|---|---|---|
| `GET /api/v1/companies/{id}/intelligence` | Authenticated | Shared organizational intelligence. Returns zero candidate data. |
| `GET /api/v1/companies/{id}/technology` | Authenticated | Shared tech stack with 4-tier provenance. No candidate data. |
| `GET /api/v1/companies/{id}/hiring` | Authenticated | Aggregated from public job records. No candidate data. |
| `GET /api/v1/companies/{id}/sources` | Authenticated | Verified public citation documents. No candidate data. |
| `GET /api/v1/companies/{id}/fit` | Authenticated User | Candidate-specific. Requires `resume_version_id` owned by the requesting user; returns 404 on cross-user substitution. |
| `POST /api/v1/companies/{id}/research/generate` | Authenticated User | Candidate-specific. Validates user ownership of `resume_version_id`. Generates report owned strictly by `current_user.id`. |
| `GET /api/v1/companies/{id}/research/reports` | Authenticated User | Filters `CompanyResearchReport.user_id == current_user.id`. User B cannot see User A's reports. |
| `GET /api/v1/company-intelligence/reports` | Authenticated User | Filters `CompanyResearchReport.user_id == current_user.id`. |
| `GET /api/v1/company-intelligence/reports/{id}` | Authenticated User | Returns report only if `report.user_id == current_user.id`; returns 404 otherwise. |
| `DELETE /api/v1/company-intelligence/reports/{id}` | Authenticated User | Deletes report only if `report.user_id == current_user.id`; returns 404 otherwise. |

---

## Token & Cookie Security Strategy

| Aspect | Strategy & Implementation | Tradeoff / Mitigation |
|---|---|---|
| **Access Token Storage** | Kept strictly in client **memory** (React Context state). | Access token disappears on page reload. Mitigated by instant background refresh via HttpOnly cookie. |
| **Refresh Token Storage** | Transmitted as an `HttpOnly`, `SameSite=Lax`, `Secure` (in production) cookie scoped to `/api/v1/auth`. Also provided in JSON body for non-browser clients. | Immune to browser JavaScript XSS extraction. Cross-Site Request Forgery is mitigated by `SameSite=Lax` and explicit endpoint paths. |
| **Database Token Security** | Stored strictly as SHA-256 hashes (`token_hash`), never raw token strings. | In the event of a database snapshot leak, refresh tokens cannot be used to forge user sessions. |
| **Rotation Protection** | Single-use refresh tokens: each refresh revokes the old token. | Revocation tracking detects replay attacks and invalidates compromised token chains. |

---

## 22. Career Command Center & Unified Analytics Architecture

The Career Command Center (`/dashboard/career-command-center`) provides a unified, cross-module career intelligence cockpit for candidates. It consolidates activity across Discovery, Matching, Tailoring, Application Tracking, AI Application Assistant, Interview Prep Coach, and Company Intelligence into an integrated interface without duplicating data storage or introducing ungrounded AI percentage estimations.

### 22.1 Architecture Principles
1. **Zero Database Bloat & 100% Architectural Reuse**: No new database tables or migrations are required. The module leverages existing models (`Job`, `JobMatch`, `JobApplication`, `ApplicationStatusHistory`, `ApplicationPreparation`, `InterviewPreparationSession`, `InterviewEvaluation`, `ResumeAnalysis`, `ResumeVersion`, `Company`, `JobIntelligence`, `UserMatchingPreference`).
2. **Strict Multi-Tenant User Isolation**: All aggregations and queries filter explicitly by `user_id == current_user.id` or user-owned resume/application associations. Cross-user leaks are mathematically impossible.
3. **Real Database Aggregations**: All KPIs, funnel counts, conversion rates, and analytics are computed live from persistent records. Zero mock or hardcoded metric numbers.
4. **Time-Horizon Filtering**: Supports `30d` (past 30 days), `90d` (past 90 days), and `all` (all-time) date ranges via `date_range` query parameters, filtering against `created_at` timestamps on tracked events.

### 22.2 Real-Time Career KPIs & 7-Stage Application Funnel
- **10 Core KPIs**:
  1. `total_discovered_jobs`: Total active, verified opportunities discovered on the platform.
  2. `verified_active_opportunities`: Currently active and verified job postings.
  3. `strong_job_matches`: Discovered jobs with match score $\ge 75\%$ for the candidate.
  4. `saved_opportunities`: Applications in `interested` status.
  5. `applications_in_progress`: Applications in `preparing` status or active preparation sessions.
  6. `applications_submitted`: Total applications with status in `applied`, `shortlisted`, `assessment`, `interview`, `offer`, `rejected`, or `withdrawn` (or confirmed submissions).
  7. `interviews_scheduled`: Total scheduled interview rounds across applications.
  8. `offers_received`: Total applications reaching `offer` status.
  9. `resume_versions_created`: Total resume versions uploaded or tailored by the user.
  10. `interview_prep_sessions_completed`: Total mock interview sessions completed.
- **7-Stage Career Funnel**:
  - Stages: `Discovered` $\to$ `Matched` $\to$ `Saved` $\to$ `Preparing` $\to$ `Applied` $\to$ `Interview` $\to$ `Offer`.
  - Step conversions ($C_i = N_i / N_{i-1} \times 100$) and drop-offs ($D_i = N_{i-1} - N_i$).
  - **No False Application Inflation**: External portal clicks (`open-link`) record link opening events without transitioning application state. Only verified status transitions in `application_status_history` and explicit `submission_confirmed` flags increment the `Applied` funnel step.

### 22.3 Deterministic Career Readiness Scoring
Rather than relying on ungrounded AI predictions, Nexora implements an explainable, deterministic readiness score ($S_{\text{readiness}} \in [0, 100]$):
$$S_{\text{readiness}} = 0.40 \cdot S_{\text{skills}} + 0.30 \cdot S_{\text{match}} + 0.20 \cdot S_{\text{interview}} + 0.10 \cdot S_{\text{evidence}}$$

Where:
- $S_{\text{skills}}$: Demonstrated skills coverage against target roles and top market demand skills ($0 - 100$).
- $S_{\text{match}}$: Average score across the user's top job matches ($0 - 100$).
- $S_{\text{interview}}$: Average performance score across completed mock interview evaluations ($0 - 100$).
- $S_{\text{evidence}}$: Project and experience evidence coverage verified in resume analysis ($0 - 100$).

**Transparent Limitation Disclosure**: The UI and API explicitly display: *"Readiness score is an algorithmic synthesis (40% skills coverage, 30% top match score, 20% mock interview performance, 10% verified project evidence) based strictly on your uploaded resumes, saved jobs, and completed practice sessions. It is a preparation benchmark, not a guarantee of employment or external recruiter decision."*

### 22.4 Deterministic Action Recommendation Engine
Evaluates candidate state and produces prioritized recommendations with direct dashboard deep links:
- **High Priority**:
  - `scheduled_interview`: Upcoming scheduled interview rounds requiring revision.
  - `company_research`: Applications reaching interview stage without completed company research.
  - `incomplete_prep`: Application preparations in draft status needing submission.
- **Medium Priority**:
  - `application_followup`: Submitted applications awaiting response after 7+ days.
  - `high_score_match`: Discovered matches $\ge 85\%$ that have not yet been saved or applied to.
- **Low Priority**:
  - `resume_tailoring`: High-match opportunities lacking a targeted tailored resume version.

### 22.5 Job Search Performance Analytics
- **Activity Trends**: Weekly and monthly time-series tracking saved jobs, tailored resumes, submitted applications, and interview sessions.
- **Distributions**: Role family counts, company category breakdown, application status pipeline, and top location frequency.
- **Conversion Metrics**: Interview conversion rate ($N_{\text{interview}} / N_{\text{applied}}$) and offer conversion rate ($N_{\text{offer}} / N_{\text{applied}}$).
- **Small-Sample Safeguards**: When applications submitted is less than 5, the UI displays: *"More data needed (min 5 applications) for statistically meaningful rates"* rather than misleading percentages.
- **Saved vs. Applied Comparison**: Quantifies application execution efficiency ($N_{\text{applied}} / N_{\text{saved}}$) with actionable feedback.

### 22.6 Career Goals & Preferences Integration
Reuses the `UserMatchingPreference` model without schema mutations:
- Standard fields: `target_role_families`, `preferred_locations`, `work_arrangements`, `min_salary`, `priority_skills`.
- Extended metadata: Stored cleanly within `metadata_json` (`weekly_application_target`, `preferred_company_categories`).
- Progress tracking: Dynamically calculates weekly applications submitted vs `weekly_application_target` with real-time percentage progress.

### 22.7 REST API Endpoints
All endpoints mounted under `/api/v1/career-command-center` and require standard user authentication:
- `GET /api/v1/career-command-center/overview?date_range={30d|90d|all}`: 10 Career KPIs and weekly goal progress.
- `GET /api/v1/career-command-center/funnel?date_range={30d|90d|all}`: 7-stage funnel metrics, stage conversions, and drop-offs.
- `GET /api/v1/career-command-center/readiness`: Algorithmic readiness score, component breakdown, demonstrated skills, skill gaps, interview rubric, project evidence, and formula disclosure.
- `GET /api/v1/career-command-center/recommendations`: Prioritized recommended next actions with category tags and direct navigation URLs.
- `GET /api/v1/career-command-center/analytics?timeframe={weekly|monthly}&date_range={30d|90d|all}`: Activity trends, role/category distributions, conversions with sample-size safeguards, and saved vs applied comparison.
- `GET /api/v1/career-command-center/goals`: Target roles, priority skills, locations, salary, and weekly application target.
- `PUT /api/v1/career-command-center/goals`: Updates user career goals and matching preferences atomically.

---

## 23. Personalized Skill Development & Learning Roadmaps (Prompt 19)

### 23.1 Objectives & Anti-Fabrication Principles
The Skill Development module synthesizes demonstrated resume evidence, job market demand, interview weaknesses, and target roles into personalized 4-stage learning roadmaps, practical hands-on exercises, curated educational resources, and portfolio project tracking.

**Strict Anti-Fabrication Boundaries**:
1. **Evidence-Grounded Skill Possession**: The platform never asserts a candidate possesses a technical skill without verified resume or project evidence.
2. **Decoupled Resume Modification**: Completing lessons or exercises never modifies the user's resume automatically. Completed portfolio projects require explicit user review, repository link verification, and architectural evidence submission before becoming eligible for resume integration.

### 23.2 Architecture & Service Pipeline
```
[User Resume & Target Jobs] ───► [Skill Gap Analyzer]
                                       │ (Categorizes: Demonstrated, Partial, Missing, Weakness)
                                       ▼
                         [Roadmap Generation Engine]
                                       ├── Multi-track Deterministic Templates (6 tracks)
                                       │   └── Adapts beginner stage based on verified skills
                                       └── AI Provider Abstraction (Gemini / OpenAI fallback)
                                       │
                                       ▼
                       [Learning Roadmaps & Milestones]
                                       ├── 4 Stages (Beginner -> Intermediate -> Advanced -> Portfolio)
                                       ├── Practical Hands-On Exercises & Time Estimates
                                       ├── Curated Verified Resources Catalog + Custom Bookmarks
                                       ├── Project Portfolio Tracker (Architecture & Repo URL)
                                       └── Activity Velocity & Study Time Analytics
```

### 23.3 Database Models (`app/models/learning_roadmap.py`)
- `learning_roadmaps`: Multi-tenant roadmap entity storing target role, target skills, difficulty tier, status (`active`, `paused`, `completed`, `archived`), total hours, completed hours, prerequisites JSON, already mastered skills JSON, and metadata.
- `learning_milestones`: 4 stages per roadmap (`beginner`, `intermediate`, `advanced`, `portfolio`), learning objectives list, practical exercises checklist with individual completion flags, estimated hours, and completion notes.
- `learning_resources`: Curated and custom educational bookmarks with verified external URLs, provider name, cost tier (`free`, `freemium`, `paid`), difficulty, and skill tags.
- `learning_projects`: Tracked practical portfolio projects with functional requirements, tech stack, milestones, repository URL, live demo URL, architecture evidence notes, and portfolio readiness flag.
- `learning_activities`: Granular study session log (`reading`, `coding`, `exercise`, `project_work`, `review`, `practice`), duration in hours, skill tag, and session notes.

### 23.4 Deterministic Roadmap Tracks & AI Provider Fallback
Supports 6 comprehensive technical tracks:
1. `backend_python`: Python, FastAPI, PostgreSQL, Docker, Redis, Celery, REST API architecture.
2. `fullstack`: React, Next.js, TypeScript, Tailwind CSS, Python/FastAPI backend, deployment.
3. `ai_ml`: NumPy, Pandas, Scikit-Learn, PyTorch, model evaluation, inference serving.
4. `genai`: Prompt Engineering, Gemini API, RAG, Vector Databases, LangChain, LLM safety.
5. `data_analyst`: Advanced SQL, PostgreSQL aggregation, Pandas, Metabase/Streamlit dashboards.
6. `sde`: Data Structures & Algorithms, Big-O, System Design, clean OOP design patterns.

When candidates possess verified resume skills matching a track's beginner topics, the engine automatically flags prerequisite satisfaction and completes foundational exercises so candidates skip redundant beginner material.

### 23.5 REST API Endpoints
All endpoints mounted under `/api/v1/learning-roadmaps` with multi-tenant user authentication:
- `GET /api/v1/learning-roadmaps/skill-gaps`: Synthesizes demonstrated, partial, missing, and interview weakness skills with deterministic priority scores ($0-100$).
- `GET /api/v1/learning-roadmaps/analytics`: Study velocity, total hours learned, weekly velocity, and hours-by-skill distribution.
- `GET /api/v1/learning-roadmaps/resources/catalog`: Explores curated public educational resources with filters for skill, difficulty, and cost tier.
- `POST /api/v1/learning-roadmaps/resources/custom`: Saves user custom resource bookmarks.
- `DELETE /api/v1/learning-roadmaps/resources/custom/{id}`: Deletes custom bookmark.
- `POST /api/v1/learning-roadmaps/activities`: Logs granular study activity.
- `GET /api/v1/learning-roadmaps/activities`: Retrieves chronological study history.
- `GET /api/v1/learning-roadmaps/projects/recommendations`: Recommends practical portfolio projects.
- `GET /api/v1/learning-roadmaps/projects`: Lists user tracked projects.
- `POST /api/v1/learning-roadmaps/projects`: Creates or tracks a portfolio project.
- `PATCH /api/v1/learning-roadmaps/projects/{id}`: Updates project status, repo URL, demo URL, and architecture evidence notes.
- `PATCH /api/v1/learning-roadmaps/milestones/{id}`: Updates milestone status, completed hours, and practical exercise checkboxes.
- `GET /api/v1/learning-roadmaps`: Lists user roadmaps with completion summaries.
- `POST /api/v1/learning-roadmaps`: Generates personalized 4-stage roadmap adapted to resume evidence.
- `GET /api/v1/learning-roadmaps/{id}`: Retrieves complete roadmap details with stages and exercises.
- `PATCH /api/v1/learning-roadmaps/{id}/status`: Toggles roadmap status (`active`, `paused`).
- `DELETE /api/v1/learning-roadmaps/{id}`: Deletes roadmap and cascades milestones.

---

## 24. Portfolio Studio & Professional Showcase Architecture

### 24.1 Overview & System Invariants
The Portfolio Studio & Professional Showcase module enables candidates to create, customize, preview, and publish a recruiter-ready professional portfolio website and downloadable artifacts (PDF resume and offline HTML package) grounded entirely in verified career data, completed learning projects, and technical skills.

Core architectural invariants:
1. **Zero Fabrication**: All portfolio profiles, project descriptions, and measurable outcomes strictly reflect actual candidate experience and verified project repositories. AI assistance operates under strict grounding invariants and requires explicit user review before saving.
2. **Privacy by Design**: Public portfolio URLs (`/portfolio/[public_slug]`) expose only explicitly approved content and visible sections. Private account attributes (internal user IDs, password hashes, email verification tokens, application pipeline records, and private learning notes) are strictly excluded from public responses.
3. **Responsive Multi-Template System**: Features 3 distinctive professional templates:
   - `minimal`: Clean, typography-driven, recruiter-friendly layout.
   - `developer`: Code & architecture focused, monospace fonts, tech stack badges, terminal headers, and repository links.
   - `ai_tech`: AI/ML engineering focused, highlighting models, frameworks, architecture diagrams, and system benchmarks.
4. **Offline & Multi-Format Exports**: Provides self-contained static HTML (works offline without external CDN dependencies) and high-quality ReportLab A4 PDF export.
5. **Privacy-Conscious Visitor Analytics**: Tracks aggregate page views, project clicks, and downloads without storing visitor PII, cookies, or IP addresses.

### 24.2 Relational Database Models (`app/models/portfolio.py`)
- **`Portfolio` (`portfolios`)**: Root entity per user (`user_id` unique). Stores `public_slug`, `title`, `headline`, publication status (`is_published`, `published_at`), `template_id` (`minimal`, `developer`, `ai_tech`), `theme_config` JSONB (colors, typography, dark mode), and structured `profile_data` JSONB.
- **`PortfolioSection` (`portfolio_sections`)**: Configurable sections (`hero`, `about`, `skills`, `projects`, `experience`, `education`, `certifications`, `contact`) with custom titles, order indices, and visibility flags (`is_visible`).
- **`PortfolioProject` (`portfolio_projects`)**: Evidence-backed project entries linked to `Portfolio` and optionally to `learning_projects`. Tracks title, problem statement, description, tech stack array, key features array, architecture overview, candidate contribution, repo URL, demo URL, challenges, outcomes, status (`completed`, `in_progress`), featured flag, visibility, and display order.
- **`PortfolioVersion` (`portfolio_versions`)**: Immutable snapshots of portfolio state (`snapshot_data` JSONB) with incremental version numbers and change summaries, supporting full rollback and restoration.
- **`PortfolioViewEvent` (`portfolio_view_events`)**: Privacy-conscious event log tracking `event_type` (`page_view`, `project_view`, `pdf_download`, `html_download`), optional `project_id`, normalized `referrer_category` (`direct`, `linkedin`, `github`, `search`, `external`), and `device_category` (`desktop`, `mobile`, `tablet`).

### 24.3 Cross-Module Integrations
- **Learning Roadmap Module**: Direct one-click import from `learning_projects` (`POST /api/v1/portfolios/projects/import-learning/{id}`), automatically mapping problem statements, tech stacks, architecture summaries, and repository URLs.
- **Resume Studio Module**: One-click profile bootstrap (`POST /api/v1/portfolios/import-resume`), populating contact info, professional summary, technical skills, and work history directly from the user's latest parsed `ResumeAnalysisResult`.

### 24.4 AI Portfolio Assistant (`AIPortfolioAssistantEngine`)
- Multi-provider abstraction (`Gemini` & `OpenAI`) with deterministic rule-based fallback.
- Supports 4 assistance workflows:
  1. `improve_summary`: Refines executive summaries for clarity and impact while preserving factual boundaries.
  2. `project_description`: Converts rough technical notes into structured STAR descriptions highlighting problems, architectures, and measurable outcomes.
  3. `role_tailoring`: Adapts portfolio headline and highlights to align with target role requirements.
  4. `gap_analysis`: Identifies missing portfolio evidence (e.g., missing live demos, unquantified outcomes) and recommends improvements.
- Requires explicit user approval before any AI suggestion is saved to the database.

### 24.5 REST API Endpoints
All endpoints mounted under `/api/v1/portfolios` with tenant isolation and public access routes:
- `GET /api/v1/portfolios/me`: Retrieves current user's portfolio with all sections, projects, and version count.
- `PUT /api/v1/portfolios/profile`: Updates headline, title, and structured profile data.
- `PUT /api/v1/portfolios/theme`: Updates template ID, theme configuration, and custom CSS.
- `PUT /api/v1/portfolios/slug`: Sets custom unique public URL slug.
- `POST /api/v1/portfolios/publish`: Publishes portfolio to public web.
- `POST /api/v1/portfolios/unpublish`: Revokes public access immediately.
- `PUT /api/v1/portfolios/sections/reorder`: Reorders sections and toggles visibility.
- `PATCH /api/v1/portfolios/sections/{id}`: Updates individual section metadata.
- `POST /api/v1/portfolios/projects`: Adds a project to the portfolio.
- `PATCH /api/v1/portfolios/projects/{id}`: Updates project details.
- `DELETE /api/v1/portfolios/projects/{id}`: Deletes a project.
- `POST /api/v1/portfolios/projects/import-learning/{id}`: Imports completed learning roadmap project.
- `POST /api/v1/portfolios/import-resume`: Imports profile and skills from latest parsed resume.
- `POST /api/v1/portfolios/versions`: Creates version snapshot.
- `GET /api/v1/portfolios/versions`: Lists historical snapshots.
- `POST /api/v1/portfolios/versions/{id}/restore`: Restores portfolio to a past snapshot.
- `POST /api/v1/portfolios/ai-assist`: Generates grounded AI suggestions with deterministic fallback.
- `GET /api/v1/portfolios/export/pdf`: Exports user's portfolio as A4 PDF.
- `GET /api/v1/portfolios/export/html`: Exports user's portfolio as offline HTML.
- `GET /api/v1/portfolios/analytics`: Aggregated visitor stats, top-viewed projects, and referrers.
- `GET /api/v1/portfolios/public/{slug}`: Public unauthenticated endpoint for recruiters.
- `POST /api/v1/portfolios/public/{slug}/event`: Records public visitor interaction events.
- `GET /api/v1/portfolios/public/{slug}/export/pdf`: Public recruiter PDF download.
- `GET /api/v1/portfolios/public/{slug}/export/html`: Public recruiter offline HTML download.

## 25. Unified Career Workflow & Automation Architecture

### 25.1 Overview & System Invariants
The Unified Career Workflow & Automation engine transforms Nexora from independent career management tools into a connected, AI-guided autonomous journey:
`Upload resume → Understand candidate profile → Discover jobs → Rank opportunities → Prepare 8 connected assets → Candidate approval gate → Apply & Confirm → Track progress → Prepare for interviews`.

Core architectural invariants:
1. **Reuse of Existing Modules**: Reuses existing DB models and services (`resumes`, `job_intelligences`, `job_matches`, `application_preparations`, `cover_letters`, `application_emails`, `job_applications`, `company_intelligence`, `interview_preparation_sessions`). Avoids duplicate models or shadow workflows.
2. **Strict Candidate Approval Gate**: Consequential actions (email dispatch, formal application submission, status transitions to `applied`) require explicit candidate approval. Opening an application portal is strictly decoupled from submission confirmation.
3. **Audit Provenance & Grounded Evidence**: Opportunity recommendations and preparation materials cite source provenance, matching dimensions, and verified resume facts. Unverified AI inferences are flagged and never treated as confirmed facts without user verification.
4. **Resilient Background Orchestration**: Background workflows run asynchronously via Celery and Redis. The state machine enforces bounded retries ($\le 3$), idempotency, failure recovery, and voluntary cancellation.

### 25.2 Relational Database Models (`app/models/workflow.py`)
- **`CareerWorkflowRun` (`career_workflow_runs`)**: Orchestration session per user. Tracks `workflow_type` (`candidate_onboarding`, `application_preparation`, `recommendation_refresh`), execution `status` (`pending`, `running`, `paused_awaiting_input`, `completed`, `failed`, `cancelled`), `current_step`, `progress_pct` (0-100), `error_message`, `retry_count`, and `step_data` JSONB.
- **`CareerWorkflowStep` (`career_workflow_steps`)**: Individual discrete execution step within a workflow run. Tracks `step_number`, `step_name`, `status`, `input_payload` JSONB, `output_payload` JSONB, `error_message`, and timestamps.
- **`ApplicationPreparation` Extended Fields (`app/models/assistant.py`)**:
  - `execution_status`: Tracks fine-grained execution lifecycle: `not_started`, `preparation_in_progress`, `awaiting_approval`, `ready_to_apply`, `application_page_opened`, `submission_pending_confirmation`, `submitted_and_confirmed`, `failed`, `withdrawn`.
  - `execution_channel`: Selected delivery route: `gmail`, `official_portal`, `external_form`.
  - `execution_metadata`: JSONB audit record of confirmations, token IDs, and channel parameters.

### 25.3 Connected Application Preparation Workspace
Integrates 8 unified assets into one cohesive candidate cockpit:
1. **Job Intelligence**: Structured requirements, must-have skills, role summary, and work arrangement from `JobIntelligence`.
2. **Compatibility Assessment**: Deterministic match score, dimensional breakdown, strengths, and identified skill gaps from `JobMatch`.
3. **Tailored Resume**: Grounded tailored `ResumeVersion` linked to the job requisition.
4. **Cover Letter**: Evidence-grounded `CoverLetter` with version history and approval tracking.
5. **Recruiter Email**: Personalized `ApplicationEmail` for outreach with preview and send gate.
6. **Screening Q&A Prep**: Factual STAR talking points grounded in candidate resume bullets and portfolio projects.
7. **Company Research**: Verified tech stack, overview, and hiring trends from `CompanyIntelligence`.
8. **Interview Prep Starter**: Curated technical topics and mock interview readiness link.

### 25.4 REST API Endpoints (`/api/v1/career-workflow/*`)
- `GET /api/v1/career-workflow/dashboard`: Aggregated pipeline KPIs, candidate onboarding status, prioritized next actions, and recent workflow runs.
- `POST /api/v1/career-workflow/onboarding/start`: Extracts profile from resume, infers target roles and preferences, and initializes personalized job matching.
- `POST /api/v1/career-workflow/onboarding/confirm`: Candidate review gate to approve, correct, and persist career preferences to `UserMatchingPreference` and `Portfolio`.
- `GET /api/v1/career-workflow/discovery`: Unified opportunity ranking with early-career detection, employer tier prioritization, and verification provenance.
- `POST /api/v1/career-workflow/preparation/start`: Initializes the 8-asset application preparation workspace for a target job.
- `GET /api/v1/career-workflow/preparation/{job_id}`: Retrieves complete application preparation assets for a job requisition.
- `POST /api/v1/career-workflow/preparation/{job_id}/approve`: Explicit candidate sign-off gate setting status to `ready_to_apply`.
- `POST /api/v1/career-workflow/execution/portal-open/{job_id}`: Retrieves verified portal URL and assisted form auto-fill guidance; sets state to `application_page_opened` without claiming submission.
- `POST /api/v1/career-workflow/execution/portal-confirm/{job_id}`: Candidate explicit confirmation of completed portal submission, updating status to `applied`.
- `POST /api/v1/career-workflow/execution/gmail-send/{job_id}`: Dispatches approved email via Gmail OAuth requiring `confirm_send=True`.
- `POST /api/v1/career-workflow/execution/withdraw/{job_id}`: Withdraws application from active consideration.
- `GET /api/v1/career-workflow/runs`: Lists user's past and active workflow orchestration runs.
- `POST /api/v1/career-workflow/runs/{id}/cancel`: Cancels an active or pending workflow run.

## 26. Professional Networking & Recruiter Intelligence Architecture

### 26.1 System Invariants & Anti-Scraping Policies
The Professional Networking and Recruiter Intelligence system discovers hiring team contacts, matches candidates to recruiters, assists with grounded outreach drafting, and manages relationship states within a structured CRM.

Core architectural invariants:
1. **Zero Fabrication & Anti-Guessing**: Recruiter profiles are grounded in permitted public data or candidate additions. Nexora strictly forbids guessing recruiter email addresses (no synthetic permutation generation or pattern inference without verification).
2. **Permitted Public Sources Only**: Recruiter intelligence ingests only permitted public sources (official company careers pages, leadership/team directories, public company announcements, and candidate manual entries). Unpermitted LinkedIn scraping, session hijacking, and CAPTCHA bypass are strictly prohibited.
3. **LinkedIn Length Enforcement**: LinkedIn connection requests are strictly validated and constrained to $\le 300$ characters.
4. **Candidate Approval Gate**: All outreach messages are stored in draft status and require explicit candidate review and approval before copying or sending.
5. **Decoupled Gmail Dispatch**: Email dispatch via Gmail OAuth strictly requires immediate explicit confirmation (`confirm_send=True`), verified recipient address, and audit logging.

### 26.2 Relational Database Schema (`app/models/networking.py`)
- **`RecruiterProfile` (`recruiter_profiles`)**:
  - `id`: UUID primary key.
  - `full_name`: Candidate or source provided recruiter name.
  - `normalized_name`: Lowercase stripped name for deduplication.
  - `designation`: Professional title (e.g., "Senior Technical Recruiter").
  - `company_id`: Foreign key referencing `companies.id` (`ondelete=CASCADE`).
  - `company_name`: Normalized company name string.
  - `recruitment_specialization`: Area of focus (`Technical Recruitment`, `Campus & University`, `Executive`, etc.).
  - `relevant_departments`: JSON list of department names.
  - `public_profile_url`: Public profile link (LinkedIn or careers directory).
  - `contact_email`: Publicly available professional contact email (or `None`).
  - `phone`: Public phone contact (or `None`).
  - `associated_job_ids`: JSON list of related job UUIDs.
  - `source_type`: `official_careers_page`, `team_page`, `public_announcement`, `manual_user_addition`, `job_listing`.
  - `verification_status`: `verified`, `inferred`, `unverified`.
  - `is_global`: Boolean indicating shared platform profile vs private profile.
  - `created_by_user_id`: Foreign key referencing creator if manually added.
- **`NetworkingContact` (`networking_contacts`)**:
  - Unique constraint on `(user_id, recruiter_id)`.
  - Relationship lifecycle: `saved`, `outreach_prepared`, `contacted`, `awaiting_response`, `responded`, `follow_up_required`, `connected`, `archived`.
  - Channel: `linkedin`, `email`, `career_fair`, `referral`, `other`.
  - Response status: `pending`, `positive`, `neutral`, `declined`, `no_response`.
  - Timestamps: `initial_contact_date`, `last_contact_date`, `next_follow_up_date`, `response_received_at`.
  - Candidate notes: `networking_notes` and `tags` JSON.
- **`NetworkingOutreachMessage` (`networking_outreach_messages`)**:
  - Grounded communication draft.
  - Message types: `linkedin_connection`, `recruiter_intro`, `job_inquiry`, `internship_inquiry`, `follow_up`, `interview_thank_you`, `networking_email`.
  - Status: `draft`, `approved`, `sent`, `discarded`.
  - Approval timestamps: `approval_confirmed_at`, `sent_at`, `sent_via_gmail`, `gmail_message_id`.
  - Factual grounding: `grounded_claims` JSON array with verifiable candidate assertions.
- **`NetworkingActivity` (`networking_activities`)**:
  - Chronological interaction and audit record per user and contact.
  - Activity types: `status_change`, `outreach_created`, `outreach_approved`, `message_sent`, `response_recorded`, `follow_up_scheduled`.

### 26.3 Recruiter Matching Engine (`app/services/recruiter_matching_engine.py`)
Computes multi-dimensional explainable score (0-100):
$$S_{\text{recruiter}} = 0.35 \times S_{\text{role}} + 0.30 \times S_{\text{company}} + 0.20 \times S_{\text{skills}} + 0.15 \times S_{\text{dept}}$$
- **Role Alignment ($S_{\text{role}}$)**: Matches candidate target role families against recruiter specialization and hiring focus.
- **Company Fit ($S_{\text{company}}$)**: Higher score for preferred companies, companies with active candidate applications, or verified employer tiers.
- **Skills Relevance ($S_{\text{skills}}$)**: Evaluates overlap between verified resume skills and department technical competencies.
- **Department Score ($S_{\text{dept}}$)**: Department alignment (e.g., Engineering, Data, Product).

### 26.4 REST API Endpoints (`/api/v1/networking/*`)
- `GET /api/v1/networking/recruiters`: Search and discover recruiters with explainable match scoring.
- `POST /api/v1/networking/recruiters`: Manually record recruiter intelligence with deduplication.
- `GET /api/v1/networking/recruiters/{id}`: Detailed recruiter profile and company context.
- `PATCH /api/v1/networking/recruiters/{id}`: Update recruiter intelligence and verification details.
- `POST /api/v1/networking/recruiters/discover-company/{company_id}`: Auto-seed hiring team from company careers context.
- `GET /api/v1/networking/crm/overview`: Aggregated relationship KPIs, tracked companies, and response stats.
- `GET /api/v1/networking/crm/contacts`: Filter and list user's saved networking relationships.
- `POST /api/v1/networking/crm/contacts`: Add or update recruiter relationship in CRM.
- `PATCH /api/v1/networking/crm/contacts/{id}`: Update relationship status, follow-up dates, or notes.
- `DELETE /api/v1/networking/crm/contacts/{id}`: Remove contact from personal CRM.
- `POST /api/v1/networking/outreach/generate`: Generate personalized outreach draft across 7 message types.
- `POST /api/v1/networking/outreach/messages/{id}/approve`: Explicit candidate review and approval gate.
- `POST /api/v1/networking/outreach/messages/{id}/send-gmail`: Dispatch approved email via Gmail with `confirm_send=True`.
- `GET /api/v1/networking/follow-ups/due`: Returns contacts overdue for follow-up (>5 days or passed date).





