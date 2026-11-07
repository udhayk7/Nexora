# Development Guidelines

## Monorepo Standards

1. **Independent Execution**:
   - Both `frontend/` and `backend/` must run independently without relying on the other to be started during unit tests or builds.
2. **Strict Stack Boundary**:
   - The backend MUST remain Python FastAPI + PostgreSQL + SQLAlchemy + Alembic. Never introduce Node/Prisma backend layers.
   - The frontend MUST remain Next.js App Router + TypeScript + Tailwind CSS.
3. **No Hardcoded Secrets**:
   - Never commit `.env` files or API credentials. Use `.env.example` templates with empty/placeholder keys.

---

## Python Backend Guidelines

### Code Style & Formatting
- **PEP 8 Compliance**: Enforced via Ruff (`ruff check backend` and `ruff format backend`).
- **Static Typing**: Explicit type annotations across all functions, schemas, and endpoint signatures, checked via `mypy backend/app`.
- **Imports**: Group imports by standard library, third-party packages, and internal modules (`app.*`).

### Authentication & Current User Dependency
Protect endpoints using `get_current_active_user` from `app.api.deps`:
```python
from fastapi import Depends
from app.api.deps import get_current_active_user
from app.models.user import User

@router.get("/protected")
def protected_view(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {current_user.full_name}"}
```

### Password Security Policy
- Always validate password complexity before user creation using `validate_password_strength(password)`.
- Hash passwords with `hash_password(plain_password)`.
- Verify passwords in timing-safe manner using `verify_password(plain_password, user.hashed_password)`.
- Use generic failure messages ("Invalid email or password") across all login failures.

### Token Lifecycle & Endpoints
- `POST /api/v1/auth/register`: Creates active account, returns token pair, sets HttpOnly refresh cookie.
- `POST /api/v1/auth/login`: Verifies credentials, returns token pair, sets HttpOnly refresh cookie.
- `POST /api/v1/auth/refresh`: Validates refresh token from cookie or body, revokes old token, issues rotated token pair.
- `POST /api/v1/auth/logout`: Revokes active refresh token in database, clears HttpOnly cookie.
- `GET /api/v1/users/me`: Returns `UserResponse` without password hashes.

### AI Resume Intelligence Practices
- **Strict Evidence Grounding**: All claims, strengths, gaps, and role suitability assessments MUST be grounded in source resume excerpts (`EvidenceItem`).
- **No Overwriting / Fabrication**: AI analysis must never rewrite, fabricate, or overwrite user resume content.
- **Prompt Injection Defense**: Wrap resume text inside `<RESUME_DOCUMENT>` tags and treat as untrusted data.
- **Provider Switching**: Configure provider explicitly via `AI_PROVIDER` (`gemini`, `openai`, `none`). Do not switch silently.
- **Cost Safeguards**: Enforce `AI_MAX_INPUT_CHARS` (default 25,000) and request timeouts.
- **Testing Rule**: Never call live AI provider APIs in automated tests or CI. Always use deterministic mocks and fixtures.

### Unified Career Workflow & Candidate Approval Boundaries
- **Candidate in Control**: The platform never silently submits job applications, dispatches emails, or modifies candidate preferences without explicit sign-off.
- **Explicit Gate Enforcements**:
  - Email dispatch (`execute_gmail_application`) requires `confirm_send=True` and prior candidate approval.
  - Opening an official application portal (`open_application_portal`) provides assisted form data but strictly sets state to `application_page_opened`. It must NEVER transition to `applied` or claim submission.
  - Final application submission is recorded ONLY when the candidate explicitly confirms (`confirm_portal_submission`).
- **No Inferred Facts**: AI-extracted target roles, preferences, and skill alignments during onboarding must be presented as proposals for candidate verification, never treated as confirmed facts.
- **Bounded Background Retries**: Workflow orchestration runs via Celery enforce a maximum of 3 retries on transient errors and record failures deterministically.

### Alembic Migration Workflow
- Ensure PostgreSQL is running:
  ```bash
  docker compose exec backend alembic check
  ```
- Generate a new migration with autogenerate detection:
  ```bash
  docker compose exec backend alembic revision --autogenerate -m "descriptive_title"
  ```
- Review the generated migration file in `backend/alembic/versions/`.
- Apply migrations:
  ```bash
  docker compose exec backend alembic upgrade head
  ```

---

## Frontend Guidelines

### Authentication & Token Strategy
- Access tokens are stored exclusively in **memory** (React Context). Never write access or refresh tokens to `localStorage` or `sessionStorage`.
- Refresh tokens are transmitted via `HttpOnly`, `SameSite=Lax`, `Secure` cookies.
- Use the `useAuth()` hook to consume authentication state:
  ```tsx
  const { user, isLoading, login, register, logout } = useAuth();
  ```
- Use `apiClient()` from `@/lib/api` to make authenticated backend requests; it automatically attaches Bearer tokens and handles `credentials: "include"`.

### Code Style & Formatting
- **TypeScript**: Strict mode enabled (`noImplicitAny`, strict null checks).
- **Component Organization**:
  - Reusable presentation components reside in `src/components/ui/`.
  - Feature-specific views reside within route directories in `src/app/`.
- **Styling**: Tailwind utility classes only.

---

## Git & Version Control Practices

- Commit messages should be descriptive and conventional (e.g., `feat: ...`, `fix: ...`, `docs: ...`, `refactor: ...`).
- Never force-push (`git push -f`) to shared or main branches.
- Verify status with `git status` prior to staging files.
