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

