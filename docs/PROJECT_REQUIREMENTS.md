# Project Requirements

## Product Statement

Nexora is an AI-powered career discovery and application management platform designed to help professionals navigate modern job search complexities. The platform aggregates career discovery, tailored resume preparation, intelligent application tracking, and automated communication management into a coherent workflow.

---

## Functional Requirements

### 1. User & Identity Management
- Secure user signup, login, and session persistence (JWT / OAuth2).
- User profile containing skills, target roles, preferred industries, location preferences, and compensation benchmarks.

### 2. Career & Company Discovery
- Search and browse companies, industries, and relevant open job listings.
- Automated company intelligence: culture signals, tech stacks, business stage, and growth trajectory.
- Role alignment scoring comparing user profiles with discovered job requisitions.

### 3. Resume & Opportunity Tailoring
- Multi-resume management (base resume + customized job-specific variants).
- AI resume analysis:
  - Skill extraction and categorization.
  - Keyword match rate against target job descriptions.
  - Actionable feedback and tailored bullet point suggestions.

### 4. Application Pipeline & Tracking
- Dynamic Kanban-style application management board (Saved, Applied, Screening, Technical Interview, Final Round, Offer, Archived).
- Deadline tracking, interview calendar scheduling, and status history logs.
- Recruiter and contact management per company and role.

### 5. Asynchronous Task Processing & AI Workflows
- Heavy processing (document parsing, embeddings generation, large LLM requests) delegated to Celery worker tasks via Redis queues.
- Real-time or polled progress feedback to the client.

### 6. AI Application Assistant & Communication Integrations (Completed — Prompt 15)
- Application Preparation Workspace with interactive milestone progress tracking (`not_started`, `in_progress`, `ready_for_review`, `completed`).
- AI-powered grounded cover letter generation with verbatim resume evidence citations and ReportLab PDF compilation.
- Recruiter outreach email composer supporting 6 communication types (`direct_application`, `recruiter_outreach`, `referral_request`, `follow_up`, `interview_follow_up`, `thank_you`).
- Zero-fabrication guardrail: Nexora never guesses or infers recruiter email addresses, and flags `missing_info` for candidate-specific legal/timeline details.
- Official Google OAuth 2.0 flow with minimal scopes (`userinfo.email`, `gmail.compose`) and AES-128-CBC + HMAC-SHA256 Fernet encryption at rest.
- CSRF-protected, HMAC-SHA256 signed timestamped state verification with 15-minute expiration.
- Gmail Draft creation and direct email dispatch requiring explicit, immediately-preceding confirmation (`confirm_send=True`).
- Strict duplicate-send prevention and 10MB total attachment size limits.
- External application portal checklist assistance with submission confirmation strictly decoupled from portal URL opens.

---

## Non-Functional Requirements

### 1. Performance & Scalability
- Sub-200ms latency for all non-AI REST API calls.
- Non-blocking asynchronous task execution for document and AI pipelines.
- Efficient connection pooling via PostgreSQL and SQLAlchemy.

### 2. Security & Compliance
- Strict storage isolation of personal user data and uploaded resume documents.
- Sanitized SQL queries via ORM parametrization (zero raw unsanitized SQL strings).
- Strict CORS rules and zero secret leakage in client-side bundles or repository commits.

### 3. Maintainability
- Type safety enforced end-to-end (TypeScript on frontend, Python typing with Pydantic and mypy on backend).
- Independent modularity: Frontend and backend deployable as standalone services.

