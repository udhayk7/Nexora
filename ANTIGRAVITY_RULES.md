# Nexora AI Agent Development Rules

These rules govern all AI coding agents working on the Nexora repository. Every agent must strictly adhere to these principles across every prompt and task.

---

## 1. Architectural Integrity & Approved Stack

- **Frontend**: Next.js App Router, React, TypeScript, Tailwind CSS, Lucide Icons.
- **Backend**: Python with FastAPI, Pydantic, SQLAlchemy 2.0, Alembic.
- **Background Workers**: Celery with Redis broker and result backend.
- **Database**: PostgreSQL 16.
- **Orchestration**: Docker Compose.
- **Prohibited Substitutions**:
  - NEVER replace the FastAPI backend with Next.js API routes or server actions for core domain logic.
  - NEVER introduce Prisma, Supabase, or SQLite as substitutes for PostgreSQL + SQLAlchemy + Alembic.
  - Maintain the frontend and backend as independently runnable projects.

---

## 2. Secrets & Security

- NEVER hardcode credentials, secrets, tokens, or API keys in code, configuration files, test files, or logs.
- All secrets must be loaded via environment variables (`.env`).
- Always update `.env.example` when introducing new environment variables, using empty or descriptive placeholder strings only.
- Verify `.gitignore` prevents `.env` or sensitive credentials from ever being tracked in Git.

---

## 3. Data Integrity & Realism

- NEVER create fake jobs, companies, application records, or mock resumes in production or migration seeds.
- When writing tests, use isolated test fixtures, explicit test databases, and mocked external network calls.
- Do not add speculative abstractions or install unused dependencies.

---

## 4. Inspection & Verification Before Changes

- Inspect the workspace and existing code before proposing or editing files.
- Run type checks, linters, and unit tests before declaring a task complete:
  - Frontend: `npm run type-check && npm run lint`
  - Backend: `pytest` and `ruff check .`
- NEVER claim a test or check passed unless the command was actually executed and succeeded.

---

## 5. Git & Version Control Discipline

- Do not push or force-push to GitHub without explicit user instruction and approval.
- Keep commits focused, clean, and atomic.
- Verify status with `git status` to ensure untracked artifacts or temporary files are not accidentally committed.

