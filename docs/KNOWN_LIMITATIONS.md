# Known Limitations & Operational Invariants — Nexora

This document details intentional architectural constraints, known technical trade-offs, and operational boundaries of the Nexora platform.

---

## 1. Zero-Fabrication AI Boundary
- **Resume Grounding**: Nexora never manufactures or fabricates candidate qualifications, work experience, education, or achievements.
- **Evidence Requirement**: Cover letters, tailored resumes, and outreach emails cite verbatim evidence from parsed resume versions. If evidence is missing, the platform flags the gap rather than hallucinating credentials.
- **Coursework & Projects**: Learning roadmaps and practical exercises do **not** automatically update a candidate's resume upon completion. Only verifiable projects with candidate review and repository URLs may be added.

---

## 2. Human-in-the-Loop Consequential Actions
- **No Autonomous Application Dispatch**: Nexora strictly forbids autonomous, unattended submission of job applications.
- **Gmail Dispatch Gate**: Sending an email via Gmail requires explicit, immediately preceding candidate confirmation (`confirm_send=True`).
- **Application Portal Assistance**: For external applicant tracking portals (Workday, Greenhouse, Taleo, etc.), Nexora assists with form field guidance, but never claims autonomous form submission. The candidate manually submits on the external portal and confirms submission via the UI.

---

## 3. Crawling, Anti-Scraping & Legal Boundaries
- **Robots.txt Adherence**: Nexora strictly honors `robots.txt` disallow directives and crawl delays across all domain research adapters.
- **Zero Anti-Bot Bypass**: Nexora does not bypass CAPTCHAs, Cloudflare Turnstile, proof-of-work gates, or paywalls. If a target domain triggers a challenge, research halts cleanly and reports the challenge.
- **Distributed Redis Pacing**: Crawl pacing uses Redis `TIME` Lua scripts to prevent thundering herds and adhere strictly to server rate limits across distributed Celery worker processes.

---

## 4. AI Provider & Quota Boundaries
- **Token & Cost Quotas**: When cumulative daily ($10.00) or monthly ($100.00) platform budget caps are reached, AI features transition to deterministic fallbacks to safeguard against billing overruns.
- **Deterministic Fallbacks**: Every AI-driven feature in Nexora (resume parsing, job intelligence, cover letters, recruiter matching, interview evaluation) possesses a high-quality deterministic fallback engine that operates without external API connectivity.

---

## 5. Storage & File Formats
- **Resume File Formats**: Strictly limited to `.pdf` and `.docx` formats up to 10MB in size. Other formats (`.pages`, `.txt`, `.rtf`, `.odt`) are currently unsupported by design to ensure parsing fidelity.
- **Local Filesystem Isolation**: In default standalone deployments, files are stored on the local filesystem under `STORAGE_LOCAL_PATH`. S3/GCS blob storage adapters can be plugged into the existing `StorageService` interface for distributed multi-node storage.
