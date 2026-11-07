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

### 7. AI Interview Preparation & Interview Coach (Completed — Prompt 16)
- Personalized Interview Preparation Plans grounded in verified candidate resume, target job requisition, company context, and interview stage.
- Technical topics to revise, relevant projects to explain, internship/work experience talking points, required technical skills, and potential skill gaps with mitigation strategies.
- AI Interview Question Generator with multi-provider abstraction and deterministic fallback covering 10 categories (`technical`, `coding_problem_solving`, `backend_python`, `frontend_fullstack`, `ai_ml_genai`, `database_sql`, `system_design`, `project_deep_dive`, `internship_experience`, `behavioral_hr`) across 3 difficulty tiers (`beginner`, `intermediate`, `advanced`).
- Question-by-question Interactive Mock Interview workspace with context hints, rubric previews, and code input support.
- 6-dimension standardized rubric evaluation ($0.30 \times \text{correctness} + 0.20 \times \text{relevance} + 0.20 \times \text{completeness} + 0.10 \times \text{clarity} + 0.10 \times \text{approach} + 0.10 \times \text{communication}$).
- Safe Static Code Analyzer (`SafeStaticCodeAnalyzer`) using Python AST parsing; arbitrary code execution on the application server is strictly prohibited.
- Resume-Based Project Deep-Dive Studio with STAR structured architectural breakdown, trade-off analysis, bottlenecks, and practice questions.
- Interview Performance Analytics dashboard aggregating real completion metrics, strong areas ($\ge 75\%$), weak areas ($< 70\%$), and score progression trends.
- Interview Notes and Preparation Checklist manager with pinned notes and category filtering.
- Automated preparation reminder alarms integrated into existing `NotificationService` and Celery infrastructure.
- Direct shortcut from Application Tracker interview rounds without automatically modifying application status.

### 8. Company Intelligence & Employer Research (Completed — Prompt 17, 17 Audit & Security Validation)
- Evidence-backed company intelligence profiles covering overview, industry domain, operating locations, products/services, size, and funding without fabrication.
- 6 genuinely supported public research source categories: official websites, company newsrooms, engineering blogs, investor relations, permitted public RSS/Atom feeds, and permitted public JSON feeds.
- Source verification semantics: sources are only verified (`is_verified=True`) when their final destination matches the company's verified official domain.
- Technology stack evidence integrity: confirmed technologies require direct verified official source documentation; unverified sources or single job postings classify as inferred.
- Hardened SSRF and content security: connection-time IP pinning (`SSRFSafeTransport`), multi-hop redirect destination validation, and 2MB streaming cap against decompression bombs.
- Automated `robots.txt` and crawl policy enforcement (`RobotsPolicyEnforcer`): user-agent evaluation (`NexoraBot` with fallback to `*`), 1-hour cache, strict disallow when policy cannot be established (401/403/5xx/timeout), 404 allow-all, per-domain rate limiting honoring `Crawl-delay`, and crawl session request deduplication.
- Strict non-bypass of authentication, paywalls, CAPTCHA, or anti-bot protections (Cloudflare Turnstile, challenge platforms); immediately aborts and logs diagnostic reason.
- Structural prompt-injection defense: `<UNTRUSTED_EXTERNAL_EVIDENCE_CATALOG>`, `<PASSIVE_EXCERPT>`, strict per-snippet (800 chars) and total payload (4,000 chars) caps, directive defusal (`sanitize_untrusted_content`), tag breakout neutralization (`</UNTRUSTED` -> `<_UNTRUSTED`), and explicit model instruction execution immunity invariants.
- 10-endpoint authorization audit: strict tenant isolation across report generation, detail retrieval, listing, deletion, and candidate-fit endpoints; shared company data endpoints return zero candidate-specific information.
- Grounded hiring intelligence strictly computed from active discovered DB jobs (entry-level, internships, categories, locations).
- Candidate-to-company fit assessment evaluating overlapping skills, flagged gap areas, role alignments, and customized interview preparation advice with strict resume-version ownership validation.
- Structured 10-section AI research reports (`company_research_reports`) with deterministic SHA-256 caching (incorporating job fingerprints), stale cache invalidation, and owner-isolated report deletion (`DELETE /company-intelligence/reports/{id}`).
- Documented boundaries: Nexora enforces crawling and content safety invariants; users are responsible for supplying legitimate public URLs and must not input gated or proprietary links.
- Dedicated frontend workspace (`/dashboard/company-intelligence`) with company search, technology breakdown, hiring trends, candidate fit, report viewer with deletion, and public source provenance viewer with redirect badges.
- Integrated shortcuts from Company Discovery and Job Discovery cards.

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

