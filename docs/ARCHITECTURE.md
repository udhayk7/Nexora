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

---

## Token & Cookie Security Strategy

| Aspect | Strategy & Implementation | Tradeoff / Mitigation |
|---|---|---|
| **Access Token Storage** | Kept strictly in client **memory** (React Context state). | Access token disappears on page reload. Mitigated by instant background refresh via HttpOnly cookie. |
| **Refresh Token Storage** | Transmitted as an `HttpOnly`, `SameSite=Lax`, `Secure` (in production) cookie scoped to `/api/v1/auth`. Also provided in JSON body for non-browser clients. | Immune to browser JavaScript XSS extraction. Cross-Site Request Forgery is mitigated by `SameSite=Lax` and explicit endpoint paths. |
| **Database Token Security** | Stored strictly as SHA-256 hashes (`token_hash`), never raw token strings. | In the event of a database snapshot leak, refresh tokens cannot be used to forge user sessions. |
| **Rotation Protection** | Single-use refresh tokens: each refresh revokes the old token. | Revocation tracking detects replay attacks and invalidates compromised token chains. |
