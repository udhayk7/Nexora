# Nexora

Nexora is an AI-powered career discovery and application management platform designed to help users discover relevant companies and roles, evaluate career opportunities, tailor resumes, prepare applications, and track application pipelines.

---

## Monorepo Structure

```
nexora/
├── backend/                  # FastAPI application, SQLAlchemy models, Celery tasks
│   ├── alembic/              # Database migration scripts
│   ├── app/                  # Application source package
│   │   ├── api/v1/           # API routes & endpoints
│   │   ├── core/             # Configuration, database engine, celery setup
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── services/         # Business logic layer
│   ├── tests/                # Automated pytest suite
│   ├── Dockerfile            # Container definition
│   ├── pyproject.toml        # Python configuration & dependencies
│   └── requirements.txt      # Pinned dependencies
├── frontend/                 # Next.js 14 App Router application
│   ├── src/
│   │   ├── app/              # App Router pages and layouts
│   │   ├── components/       # Reusable UI components
│   │   └── lib/              # Frontend utilities and helpers
│   ├── Dockerfile            # Frontend container definition
│   ├── package.json          # Node dependencies and scripts
│   ├── tailwind.config.ts    # Tailwind styling configuration
│   └── tsconfig.json         # TypeScript configuration
├── docs/                     # Architectural and project documentation
│   ├── ARCHITECTURE.md       # System design and component diagrams
│   ├── DEVELOPMENT_GUIDELINES.md # Code style, workflow, and testing practices
│   ├── MODULE_STATUS.md      # Platform module progress tracker
│   └── PROJECT_REQUIREMENTS.md # Functional and non-functional requirements
├── infra/                    # Deployment scripts and orchestration
├── docker-compose.yml        # Multi-service local development environment
├── ANTIGRAVITY_RULES.md      # Rules governing AI agent implementation
├── .env.example              # Monorepo environment variable template
└── .gitignore                # Top-level Git ignore rules
```

---

## Approved Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js (App Router), React, TypeScript |
| **Styling & UI** | Tailwind CSS, shadcn/ui-compatible tokens, Lucide Icons |
| **Backend API** | Python, FastAPI, Pydantic |
| **Database & ORM** | PostgreSQL, SQLAlchemy, Alembic |
| **Background Processing**| Redis, Celery |
| **Containerization** | Docker, Docker Compose |

---

## Getting Started

### Prerequisites

- Node.js >= 18.x and npm >= 9.x
- Python >= 3.9 (Python 3.11+ recommended)
- Docker & Docker Compose (optional for bare-metal local development)

### Quick Start with Docker Compose

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Start all services:
   ```bash
   docker compose up --build
   ```
3. Access services:
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Backend API Docs: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
   - Healthcheck: [http://localhost:8000/health](http://localhost:8000/health)

---

### Local Bare-Metal Development

#### 1. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local

# Run checks
npm run type-check
npm run lint

# Start Next.js dev server
npm run dev
```

---

## Documentation

For comprehensive technical documentation, refer to the `docs/` directory:
- [System Architecture](docs/ARCHITECTURE.md)
- [Development Guidelines](docs/DEVELOPMENT_GUIDELINES.md)
- [Module Status Tracker](docs/MODULE_STATUS.md)
- [Project Requirements](docs/PROJECT_REQUIREMENTS.md)
- [Agent Execution Rules](ANTIGRAVITY_RULES.md)

