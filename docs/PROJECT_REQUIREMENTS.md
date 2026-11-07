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

### 9. Career Command Center & Unified Analytics (Completed — Prompt 18)
- Centralized Career Command Center (`/dashboard/career-command-center`) consolidating intelligence from Discovery, Matching, Tailoring, Application Tracking, AI Application Assistant, Interview Prep Coach, and Company Intelligence without data duplication.
- 10 Real-Time Career KPIs: Discovered jobs, verified active opportunities, strong matches ($\ge 75\%$), saved opportunities, applications in progress, applications submitted, interviews scheduled, offers received, resume versions created, and completed mock interview sessions.
- 7-Stage Career Application Funnel (`Discovered` $\to$ `Matched` $\to$ `Saved` $\to$ `Preparing` $\to$ `Applied` $\to$ `Interview` $\to$ `Offer`) with step conversions and drop-offs strictly derived from `application_status_history` and verified submissions; external portal clicks (`open-link`) never falsely inflate application counts.
- Deterministic Career Readiness Scoring ($S_{\text{readiness}} = 0.40 \cdot S_{\text{skills}} + 0.30 \cdot S_{\text{match}} + 0.20 \cdot S_{\text{interview}} + 0.10 \cdot S_{\text{evidence}}$) with KaTeX formula display, component scores, and explicit preparation benchmark limitation disclosure (no hallucinated AI percentage).
- 3-Column Skills Analysis: Demonstrated skills backed by resume citations, top market demand skills from active job descriptions, and prioritized skill gaps.
- Prioritized Action Recommendation Engine: High, medium, and low priority actions for upcoming interviews, missing company research, incomplete application preparations, aging submitted applications, strong job matches, and resume tailoring with direct navigation deep links.
- Job Search Performance Analytics: Weekly and monthly activity trends, target role family distribution, company category breakdown, interview and offer conversion rates with small-sample safeguards ($N < 5$), application pipeline status distribution, and saved vs applied efficiency comparison.
- Career Goals & Preferences: Seamless integration with `UserMatchingPreference` metadata (`weekly_application_target`, `preferred_company_categories`), supporting target role families, locations, salary floor, and priority skills with live weekly goal progress tracking.
- Authenticated REST API endpoints mounted under `/api/v1/career-command-center/*` with strict multi-tenant user isolation and flexible date filtering (`30d`, `90d`, `all`).
- Direct quick-launch dashboard card on `/dashboard` hub.

### 10. Personalized Skill Development & Learning Roadmaps (Completed — Prompt 19)
- Personalized skill gap analysis synthesizing resume evidence, job market demand frequency, interview weaknesses, and target roles with deterministic priority scores ($0-100$) and tiers (`critical`, `high`, `medium`, `low`).
- Zero-fabrication boundary: never claims a candidate possesses a technical skill without supporting resume evidence or verified project artifacts.
- 4-Stage learning roadmaps (`Beginner` $\to$ `Intermediate` $\to$ `Advanced` $\to$ `Portfolio`) across 6 core technical tracks (`backend_python`, `fullstack`, `ai_ml`, `genai`, `data_analyst`, `sde`) adapted to candidate's demonstrated skills with automated prerequisite satisfaction.
- Deterministic template engine paired with AI provider abstraction (Gemini / OpenAI) with reliable rule-based fallback.
- Curated public educational resource catalog (Python Docs, FastAPI, React, MDN, PostgreSQL, Docker, Redis, FreeCodeCamp, Google Cloud Skills Boost, Microsoft Learn, AWS Skill Builder, Coursera) with verified URLs, difficulty levels, and cost tiers, plus custom candidate bookmarks.
- Interactive milestone progression and practical hands-on exercises checklist with hourly study velocity tracking.
- Curated and AI-recommended practical portfolio projects with functional requirements, suggested tech stacks, milestones, and expected portfolio outcomes.
- Strict resume integration policy: completing courses/lessons never modifies resumes automatically; completed projects require explicit candidate review, repository link verification, and architectural description before becoming resume evidence.
- Multi-tenant database architecture (`LearningRoadmap`, `LearningMilestone`, `LearningResource`, `LearningProject`, `LearningActivity`) with UUID keys, foreign key constraints, and user isolation.
- 16 REST API endpoints mounted under `/api/v1/learning-roadmaps/*`.
- Full SaaS UI workspace at `/dashboard/learning-roadmap` with Skill Gaps, Roadmaps, Resources, Projects, and Analytics tabs, plus quick-launch card on the main dashboard.

### 20. Portfolio Studio & Professional Showcase (Prompt 20)
- Recruiter-ready professional portfolio studio at `/dashboard/portfolio-studio` and standalone public showcase website at `/portfolio/[public_slug]`.
- Structured career profile containing professional headline, summary, target roles, technical skills, education, work experience, certifications, achievements, and contact links with user approval workflow and zero private account data exposure.
- Evidence-backed project showcase integrating directly with Learning Roadmap module (`learning_projects`) and Resume Studio (`resumes`), capturing problem statement, tech stack, architecture overview, contribution, repo URL, demo URL, and measurable outcomes.
- 3 responsive, professionally styled templates (`minimal`, `developer`, `ai_tech`) with customizable theme settings (accent color, typography, dark/light modes).
- Interactive visual portfolio editor with drag/order controls, section visibility toggling, project selection, live responsive preview, and version snapshot history with rollback.
- Grounded AI portfolio assistant (`AIPortfolioAssistantEngine`) supporting 4 assistance modes (`improve_summary`, `project_description`, `role_tailoring`, `gap_analysis`) with strict anti-hallucination boundaries, deterministic fallback, and required user confirmation.
- Multi-channel publishing and export: public unguessable slug with instant revocation, self-contained offline static HTML export, and high-quality ReportLab A4 PDF export.
- Privacy-conscious visitor analytics tracking page views, project clicks, downloads, referrers, and device categories without collecting visitor PII.
- Comprehensive database schema (`Portfolio`, `PortfolioSection`, `PortfolioProject`, `PortfolioVersion`, `PortfolioViewEvent`) and 20+ REST API endpoints under `/api/v1/portfolios/*`.

### 21. Unified Career Workflow & Automation (Prompt 21)
- Connected end-to-end AI career pipeline connecting all independent modules into a single journey: Upload resume → Understand candidate profile → Discover jobs → Rank opportunities → Prepare 8 connected assets → Candidate approval gate → Apply & Confirm → Track progress → Prepare for interviews.
- Unified candidate onboarding: Extracts facts from uploaded resume, infers target roles and preferences, updates `UserMatchingPreference` and `Portfolio`, initializes matching, and provides candidate review & correction gate (unverified inferences are never treated as confirmed facts).
- Unified opportunity discovery & prioritization: Active job ranking with early-career / fresher detection, premier employer tier prioritization (Product companies, MNCs, GCCs, Big 4, top tech startups), and verification provenance categorization (verified direct, corroborated, unverified portal).
- Intelligent application preparation workspace connecting 8 assets: Job Intelligence, Compatibility Assessment, Tailored Resume, Cover Letter, Recruiter Email, Screening Q&A Prep, Company Research, and Interview Prep Starter.
- Explicit candidate approval gates: Require explicit confirmation for consequential actions; Gmail dispatch requires `confirm_send=True`; official portal opening provides verified URL and assisted form auto-fill guidance while strictly decoupling opening from application submission confirmation.
- Resilient background orchestration: Persistent state machine (`CareerWorkflowRun`, `CareerWorkflowStep`) executed via Celery and Redis with bounded retries ($\le 3$), idempotency, failure recovery, and cancellation controls.
- Dedicated UI workspace at `/dashboard/career-workflow` featuring visual pipeline progress, KPI stats, prioritized recommended actions, discovery opportunities, 8-asset preparation modal, execution gates, onboarding review drawer, and workflow run history.

### 22. Professional Networking & Recruiter Intelligence (Prompt 22)
- Recruiter Intelligence: Structured profiles (`full_name`, `designation`, `company_name`, `recruitment_specialization`, `relevant_departments`, `public_profile_url`, `contact_email`, `phone`, `associated_job_ids`, `source_type`, `verification_status`). Distinguishes verified from inferred/unverified records; strictly forbids inventing recruiter identities or email addresses.
- Recruiter Discovery: Discovery restricted to permitted public sources (official company careers pages, leadership/team directories, public announcements, and manual candidate additions). Strict prohibition against unpermitted LinkedIn scraping, session hijacking, or CAPTCHA bypass.
- Explainable Recruiter Matching: Deterministic scoring formula ($S_{\text{recruiter}} = 0.35 \times S_{\text{role}} + 0.30 \times S_{\text{company}} + 0.20 \times S_{\text{skills}} + 0.15 \times S_{\text{dept}}$) paired with contextual AI explanations ("Why Recommended").
- AI Networking Outreach Assistant: Supports 7 message types (`linkedin_connection`, `recruiter_intro`, `job_inquiry`, `internship_inquiry`, `follow_up`, `interview_thank_you`, `networking_email`) across 4 customizable tones. Enforces strict $\le 300$ character constraint for LinkedIn connection notes; factual grounding in candidate's verified resume with zero hallucinated mutual connections or employment history.
- Candidate Approval Gate & Decoupled Dispatch: All generated messages require candidate review and approval before dispatch; Gmail dispatch requires explicit confirmation (`confirm_send=True`) and never sends to guessed email addresses.
- Networking CRM & Activity Timeline: Tracks relationship states (`saved`, `outreach_prepared`, `contacted`, `awaiting_response`, `responded`, `follow_up_required`, `connected`, `archived`), channels, response states, follow-up dates, notes, and activity timeline. Enforces single relationship per recruiter-candidate pair.
- Follow-up Intelligence: Automated Celery background task (`check_networking_followups_task`) detecting overdue outreach (>5 days) and surfacing deduplicated alerts.
- Dedicated SaaS UI workspace at `/dashboard/networking` with Overview KPIs, Recruiter Discovery, Networking CRM, AI Outreach Studio, and Activity Timeline.

### 23. Advanced AI Agent Orchestration & Career Copilot (Prompt 23)
- Central AI Orchestrator: Dynamic intent-driven coordination layer connecting 8 specialized agents (`ResumeIntelligenceAgent`, `JobDiscoveryAgent`, `JobMatchingAgent`, `CompanyIntelligenceAgent`, `ApplicationPreparationAgent`, `RecruiterNetworkingAgent`, `InterviewPreparationAgent`, `CareerStrategyAgent`).
- Reuse of Domain Assets: Orchestration reuses existing database tables and services without duplicate models or unnecessary micro-architectures.
- Secure Shared Candidate Context: Projects lean qualifications, verified skills, and funnel KPIs while omitting passwords, credentials, and raw unstructured multi-megabyte payloads.
- Bounded Multi-Agent Workflows: Maximum 4 sequential agent steps per pipeline with strict cycle protection to prevent infinite loops and control AI inference costs.
- Deterministic Python Fallback: Zero-failure guarantee ensuring all operations synthesize grounded responses when AI provider credentials are missing or services fail.
- Human-in-the-Loop Approval Safeguards: Consequential actions (dispatching emails via Gmail, submitting job applications, publishing portfolio studio) strictly enforce explicit candidate approval (`requires_approval=True`).
- Audit Transparency & Tracking: Persists every agent operation, latency, token usage, and candidate approval state in `agent_execution_records`.
- Dedicated SaaS UI Workspace: `/dashboard/ai-copilot` featuring full conversational thread, live collapsible agent execution traces, structured recommendation cards, candidate approval dialogs, suggested prompt chips, and a right-side candidate context drawer.

### 24. Production Integration & API Configuration (Prompt 24)
- Production Multi-Provider AI Architecture: Centralized routing supporting OpenAI (`gpt-4o-mini` routine, `gpt-4o` strong) as primary and Google Gemini (`gemini-2.5-flash` routine, `gemini-1.5-pro` strong) as secondary with automated fallback.
- Server-Side AI Budget & Cost Management: Enforces daily ($10.00) and monthly ($100.00) platform budget ceilings, per-user daily token limits (150,000 tokens), SHA-256 duplicate request fingerprint caching, and persistent audit logging in `ai_usage_logs`.
- Google OAuth 2.0 & Gmail Integration: Tamper-proof OAuth state tokens, AES-256-GCM token encryption at rest, explicit candidate confirmation (`confirm_send=True`), and RFC-5322 recipient validation.
- Database & Redis Production Hardening: PostgreSQL connection pooling with `DB_SSL_MODE` enforcement; Redis password authentication and TLS/SSL transport security for Celery workers.
- Job Discovery Operational Verification: Status, rate-limit policies, and normalization specifications for 5 automated adapters (Greenhouse, Lever, Ashby, RSS/Atom, Generic JSON).
- Centralized Diagnostic Health Endpoints: `/api/v1/integrations/health`, `/test/{service}`, `/ai-usage`, and `/job-sources`.
- Dedicated Health & Cost Dashboard: SaaS page at `/dashboard/integrations` displaying real-time service health, live ping probes, budget progress bars, token consumption breakdowns, and recent execution audit logs.

### 25. Final Security, Testing & Production Readiness (Prompt 25)
- Comprehensive Application Security Audit: Complete audit covering authentication, JWT rotation, password hashing, session management, IDOR defense, SQL injection, XSS, SSRF, path traversal, and file upload validation.
- Security Headers & Middleware: Global injection of baseline security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`, and conditional HSTS in production) across both FastAPI and Next.js.
- Copilot Session IDOR Defense: Fixed unauthorized session access in `OrchestratorService.process_message` by enforcing strict user ownership on requested sessions.
- Multi-User Isolation Test Suite: 8 automated tests in `tests/test_multi_user_security.py` verifying strict cross-tenant isolation and data privacy.
- End-to-End Workflow Testing: 8 comprehensive end-to-end workflow tests in `tests/test_end_to_end_workflows.py` covering Workflows A through H.
- Security Audit & Hardening Suite: 7 tests in `tests/test_security_audit_hardening.py` covering SQL injection resilience, XSS handling, path traversal prevention, file upload magic bytes and size limits, AI budget caps, and OAuth state HMAC verification.
- Database & Migration Validation: Verified single contiguous migration chain ending at head `f6764b34df63` with zero schema drift and successful backup/restore validation.
- Final Quality Gates: 347/347 backend tests passing, 0 TypeScript errors, 0 ESLint errors, Next.js production build verified (27 routes), Ruff and Mypy 100% verified.

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

