"""
Roadmap & Project Recommendation Engine.
Coordinates AI provider execution with deterministic fallback for structured learning roadmaps
and practical portfolio projects adapted to candidate resume evidence.
"""

import json
import logging
from typing import Any, Optional

from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("nexora.ai.roadmap")

# ---------------------------------------------------------------------------
# Deterministic Roadmap Track Templates
# ---------------------------------------------------------------------------

DETERMINISTIC_ROADMAP_TRACKS: dict[str, dict[str, Any]] = {
    "backend_python": {
        "title": "Python Backend Engineering Roadmap",
        "target_role": "backend_python",
        "description": (
            "Comprehensive path to building high-performance, asynchronous REST APIs, "
            "background task systems, and microservices with Python, FastAPI, PostgreSQL, "
            "and Docker."
        ),
        "target_skills": [
            "Python",
            "FastAPI",
            "PostgreSQL",
            "SQLAlchemy",
            "Redis",
            "Celery",
            "Docker",
            "Pytest",
        ],
        "difficulty_level": "intermediate",
        "total_estimated_hours": 85.0,
        "prerequisites": [
            {"topic": "Basic Python Syntax & Data Types", "required": True},
            {"topic": "Basic Git Version Control", "required": True},
            {"topic": "HTTP Request/Response Basics", "required": True},
        ],
        "stages": [
            {
                "title": "Core Python & Data Modeling",
                "stage": "beginner",
                "description": (
                    "Master advanced Python OOP, type hints, Pydantic data validation, and "
                    "relational database schema design with PostgreSQL."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    (
                        "Implement clean object-oriented domain models with modern Python "
                        "3.11+ type hints"
                    ),
                    (
                        "Design normalized relational database schemas with primary keys, "
                        "indexes, and foreign keys"
                    ),
                    "Enforce strict input validation and data serialization using Pydantic V2",
                ],
                "practical_exercises": [
                    {
                        "title": "Custom Type Validators",
                        "instructions": (
                            "Build custom Pydantic validators for complex formats (emails, "
                            "phone numbers, custom constraints)."
                        ),
                        "estimated_minutes": 45,
                        "completed": False,
                    },
                    {
                        "title": "Schema Normalization Lab",
                        "instructions": (
                            "Design a 3NF relational database schema for an e-commerce or "
                            "booking platform in PostgreSQL."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                    {
                        "title": "Database Query Optimization",
                        "instructions": (
                            "Write complex SQL queries with JOINs, aggregations, and "
                            "analyze execution plans using EXPLAIN ANALYZE."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Asynchronous REST APIs with FastAPI",
                "stage": "intermediate",
                "description": (
                    "Build production-ready, non-blocking REST APIs with FastAPI, "
                    "dependency injection, SQLAlchemy 2.0 ORM, and JWT authentication."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    (
                        "Construct asynchronous FastAPI endpoints with dependency injection "
                        "and lifespan management"
                    ),
                    (
                        "Manage database transactions and session lifecycles using "
                        "SQLAlchemy 2.0 async sessions"
                    ),
                    (
                        "Implement secure JWT authentication, password hashing, and role- "
                        "based access control"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "JWT Auth & Session Revocation",
                        "instructions": (
                            "Build an authentication service with access/refresh token "
                            "rotation and token blacklist in Redis."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "CRUD Repository Pattern",
                        "instructions": (
                            "Implement a decoupled repository and service layer "
                            "architecture for a database resource."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "API Test Suite with Pytest",
                        "instructions": (
                            "Write comprehensive unit and integration tests using pytest, "
                            "httpx TestClient, and in-memory test database."
                        ),
                        "estimated_minutes": 75,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Background Tasks & Distributed Systems",
                "stage": "advanced",
                "description": (
                    "Scale backend systems using Redis caching, distributed message queues "
                    "with Celery, and atomic rate limiters."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    (
                        "Offload heavy tasks (PDF generation, email sending, web scrapers) "
                        "to Celery worker processes"
                    ),
                    "Implement distributed caching and rate limiting strategies with Redis",
                    (
                        "Handle transient network failures using exponential backoff and "
                        "retry policies"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Distributed Task Queue",
                        "instructions": (
                            "Configure a Celery worker with Redis broker to asynchronously "
                            "process document parsing and notify subscribers."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "Redis Sliding-Window Rate Limiter",
                        "instructions": (
                            "Implement an atomic per-user or per-IP rate limiter using "
                            "Redis Lua scripting."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Portfolio Microservice & Container Deployment",
                "stage": "portfolio",
                "description": (
                    "Containerize the entire full-stack backend application with Docker and "
                    "Docker Compose, set up CI/CD workflows, and author documentation."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    "Author multi-stage Dockerfiles optimized for minimal image size and security",
                    (
                        "Orchestrate multi-container environments (App + Postgres + Redis + "
                        "Celery) via Docker Compose"
                    ),
                    (
                        "Document API architecture, ER diagrams, and deployment runbooks "
                        "for portfolio presentation"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Multi-Stage Dockerfile",
                        "instructions": (
                            "Create a production-hardened multi-stage Dockerfile that "
                            "builds with a non-root runner user."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                    {
                        "title": "GitHub Actions CI Pipeline",
                        "instructions": (
                            "Set up a CI workflow that runs ruff, mypy, and pytest on every "
                            "pull request."
                        ),
                        "estimated_minutes": 75,
                        "completed": False,
                    },
                ],
            },
        ],
    },
    "fullstack": {
        "title": "Modern Full-Stack Web Development Roadmap",
        "target_role": "fullstack",
        "description": (
            "Master end-to-end web engineering: Next.js/React frontend with TypeScript and "
            "Tailwind, paired with robust backend APIs, authentication, and database "
            "persistence."
        ),
        "target_skills": [
            "React",
            "Next.js",
            "TypeScript",
            "Tailwind CSS",
            "Node.js",
            "PostgreSQL",
            "REST APIs",
            "Docker",
        ],
        "difficulty_level": "intermediate",
        "total_estimated_hours": 90.0,
        "prerequisites": [
            {"topic": "HTML, CSS & JavaScript Fundamentals", "required": True},
            {"topic": "Git & GitHub Basics", "required": True},
        ],
        "stages": [
            {
                "title": "Modern Frontend with React, Next.js & TypeScript",
                "stage": "beginner",
                "description": (
                    "Build responsive, accessible user interfaces with React, Next.js App "
                    "Router, TypeScript, and Tailwind CSS."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    "Master React hooks, component lifecycles, and component composition patterns",
                    "Implement type-safe client and server components in Next.js App Router",
                    "Design accessible, responsive UI layouts using Tailwind CSS utility tokens",
                ],
                "practical_exercises": [
                    {
                        "title": "Interactive Kanban Board",
                        "instructions": (
                            "Build a drag-and-drop task board with React state and custom hooks."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "Responsive Dashboard Shell",
                        "instructions": (
                            "Create a responsive sidebar, header, and metrics grid layout "
                            "using Tailwind CSS."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Client-Server Communication & State Architecture",
                "stage": "intermediate",
                "description": (
                    "Integrate frontend applications with REST/GraphQL backends, manage "
                    "authentication tokens, and handle caching."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    (
                        "Handle global application state, authentication contexts, and "
                        "protected route wrappers"
                    ),
                    (
                        "Implement robust HTTP clients with interceptors, token refresh, "
                        "and error toast notifications"
                    ),
                    (
                        "Apply optimistic UI updates and skeleton loading states for "
                        "enhanced user experience"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Auth Context with Refresh Rotation",
                        "instructions": (
                            "Build a React AuthProvider that manages in-memory access "
                            "tokens with HttpOnly refresh cookie recovery."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "Paginated Search & Filter Table",
                        "instructions": (
                            "Implement a data table with debounced search, multi-filter "
                            "dropdowns, and URL query persistence."
                        ),
                        "estimated_minutes": 75,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Backend Services & Database Integration",
                "stage": "advanced",
                "description": (
                    "Design secure backend APIs, database migrations, connection pooling, "
                    "and multi-tenant security."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    "Build RESTful endpoints with input validation and centralized error handling",
                    "Execute database migrations and maintain referential integrity with ORMs",
                    (
                        "Safeguard APIs against common vulnerabilities (CORS, CSRF, SQL "
                        "injection, XSS)"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "REST API with Database Migration",
                        "instructions": (
                            "Develop a backend service with automated database migrations "
                            "and integration test suite."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Full-Stack SaaS Capstone & Deployment",
                "stage": "portfolio",
                "description": (
                    "Build and deploy a complete production full-stack SaaS application "
                    "with authentication, analytics, and automated deployments."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    (
                        "Integrate frontend client and backend microservices into a "
                        "cohesive SaaS product"
                    ),
                    (
                        "Deploy frontend to Vercel/Docker and backend to containerized "
                        "hosting with PostgreSQL"
                    ),
                    (
                        "Write comprehensive README with live demo URL, architecture "
                        "diagram, and setup instructions"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Full-Stack SaaS Launch",
                        "instructions": (
                            "Deploy complete full-stack web application with CI/CD and "
                            "public live demo."
                        ),
                        "estimated_minutes": 120,
                        "completed": False,
                    },
                ],
            },
        ],
    },
    "ai_ml": {
        "title": "AI & Machine Learning Engineering Roadmap",
        "target_role": "ai_ml",
        "description": (
            "From foundational mathematical modeling to deep learning with PyTorch, model "
            "evaluation, and production inference deployment."
        ),
        "target_skills": [
            "Python",
            "NumPy",
            "Pandas",
            "Scikit-Learn",
            "PyTorch",
            "Data Analysis",
            "Model Evaluation",
            "FastAPI",
        ],
        "difficulty_level": "advanced",
        "total_estimated_hours": 100.0,
        "prerequisites": [
            {"topic": "Python Programming", "required": True},
            {"topic": "Linear Algebra & Probability Basics", "required": True},
        ],
        "stages": [
            {
                "title": "Data Manipulation & Scientific Computing",
                "stage": "beginner",
                "description": (
                    "Master array programming with NumPy, exploratory data analysis with "
                    "Pandas, and data visualization."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    "Perform high-performance vector and matrix calculations using NumPy arrays",
                    "Clean, transform, and aggregate tabular datasets using Pandas",
                    (
                        "Visualize distributions, correlations, and anomalies using "
                        "Matplotlib and Seaborn"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Exploratory Data Analysis Lab",
                        "instructions": (
                            "Analyze real-world job posting data to uncover salary "
                            "distributions and skill frequency trends."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "Feature Engineering Pipeline",
                        "instructions": (
                            "Construct automated preprocessing pipelines for one-hot "
                            "encoding, scaling, and missing value imputation."
                        ),
                        "estimated_minutes": 75,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Classical Machine Learning & Validation",
                "stage": "intermediate",
                "description": (
                    "Build, evaluate, and tune supervised and unsupervised learning "
                    "algorithms with Scikit-Learn."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    (
                        "Train regression, classification, and clustering models (Random "
                        "Forests, Gradient Boosting, SVMs)"
                    ),
                    (
                        "Implement rigorous k-fold cross-validation and hyperparameter "
                        "tuning with GridSearchCV"
                    ),
                    (
                        "Evaluate models using precision, recall, F1-score, ROC-AUC, and "
                        "confusion matrices"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Resume Classification Model",
                        "instructions": (
                            "Train a text classification model to categorize resumes into "
                            "role families."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "Hyperparameter Optimization",
                        "instructions": (
                            "Tune Gradient Boosting models using Bayesian optimization or Optuna."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Deep Learning & Neural Networks with PyTorch",
                "stage": "advanced",
                "description": (
                    "Construct neural architectures, loss functions, optimizers, and "
                    "transfer learning workflows in PyTorch."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    (
                        "Understand computational graphs, automatic differentiation, and "
                        "custom PyTorch Modules"
                    ),
                    (
                        "Train feedforward and recurrent neural networks with dropout and "
                        "batch normalization"
                    ),
                    "Fine-tune pre-trained vision or text transformer backbones on domain datasets",
                ],
                "practical_exercises": [
                    {
                        "title": "PyTorch Neural Classifier",
                        "instructions": (
                            "Build and train a custom neural network module from scratch "
                            "with custom training loop and validation checkpoints."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Model Serving & MLOps Portfolio Project",
                "stage": "portfolio",
                "description": (
                    "Package trained models into high-throughput inference APIs with "
                    "FastAPI, Docker, and latency profiling."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    (
                        "Expose model inference via asynchronous FastAPI endpoints with "
                        "batching support"
                    ),
                    "Optimize model inference latency with ONNX runtime or quantization",
                    "Deploy containerized model service with monitoring and API documentation",
                ],
                "practical_exercises": [
                    {
                        "title": "End-to-End ML Microservice",
                        "instructions": (
                            "Deploy an inference API that accepts candidate profiles and "
                            "returns predictive job match scores with explainability."
                        ),
                        "estimated_minutes": 120,
                        "completed": False,
                    },
                ],
            },
        ],
    },
    "genai": {
        "title": "Generative AI & LLM Systems Roadmap",
        "target_role": "genai",
        "description": (
            "Specialize in building enterprise GenAI applications: advanced prompt "
            "engineering, RAG pipelines with vector databases, and multi-agent systems."
        ),
        "target_skills": [
            "Generative AI",
            "Python",
            "RAG",
            "Vector Databases",
            "Prompt Engineering",
            "FastAPI",
            "Gemini API",
            "OpenAI API",
        ],
        "difficulty_level": "intermediate",
        "total_estimated_hours": 75.0,
        "prerequisites": [
            {"topic": "Python Programming", "required": True},
            {"topic": "REST API Integration", "required": True},
        ],
        "stages": [
            {
                "title": "LLM Fundamentals & Structured Output Prompting",
                "stage": "beginner",
                "description": (
                    "Master foundation model architectures, temperature/top-p sampling, "
                    "structured JSON output enforcement, and prompt injection defense."
                ),
                "estimated_hours": 15.0,
                "learning_objectives": [
                    (
                        "Craft few-shot and chain-of-thought prompts that reliably produce "
                        "strictly valid JSON schemas"
                    ),
                    (
                        "Implement system-level prompt-injection defenses (delimiters, XML "
                        "wrappers, untrusted catalogs)"
                    ),
                    (
                        "Manage token context windows and estimate API cost optimizations "
                        "across models"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Structured Resume Extraction Engine",
                        "instructions": (
                            "Write an LLM pipeline that extracts structured skill and "
                            "project entities guaranteed to match a Pydantic schema."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                    {
                        "title": "Prompt Injection Stress Testing",
                        "instructions": (
                            "Test adversarial inputs against prompt isolation wrappers and "
                            "verify zero instruction escape."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Retrieval-Augmented Generation (RAG) Architecture",
                "stage": "intermediate",
                "description": (
                    "Build high-accuracy semantic search and question-answering systems "
                    "over private document corpuses."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    (
                        "Chunk and embed documents using modern dense embedding models "
                        "(e.g., text-embedding-004)"
                    ),
                    (
                        "Index and query vector databases (pgvector, Chroma, Qdrant, "
                        "Pinecone) with cosine similarity"
                    ),
                    (
                        "Implement reranking and grounded citation attribution to eliminate "
                        "hallucinations"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Document RAG System with Citations",
                        "instructions": (
                            "Build a RAG pipeline over corporate PDFs that includes exact "
                            "sentence-level citation references in responses."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "Hybrid Search with pgvector",
                        "instructions": (
                            "Implement hybrid dense vector + sparse keyword search in "
                            "PostgreSQL using pgvector and pg_trgm."
                        ),
                        "estimated_minutes": 75,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Autonomous Agents & Tool Calling",
                "stage": "advanced",
                "description": (
                    "Design multi-step autonomous agents equipped with tool execution, "
                    "memory management, and reasoning loops."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    (
                        "Implement function calling and tool schemas for external API and "
                        "database querying"
                    ),
                    (
                        "Build stateful conversation workflows with session persistence and "
                        "short/long-term memory"
                    ),
                    (
                        "Implement safety guardrails that prevent unauthorized tool "
                        "execution and runaway loops"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Multi-Tool Research Agent",
                        "instructions": (
                            "Build an agent that uses search, calculator, and DB lookup "
                            "tools to compile an evidence-backed intelligence briefing."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Portfolio GenAI Application",
                "stage": "portfolio",
                "description": (
                    "Build an end-to-end production GenAI application with evaluation "
                    "benchmarks, streaming responses, and UI."
                ),
                "estimated_hours": 15.0,
                "learning_objectives": [
                    (
                        "Implement Server-Sent Events (SSE) streaming for real-time "
                        "generative responses"
                    ),
                    (
                        "Establish automated evaluation metrics (faithfulness, answer "
                        "relevance, context recall)"
                    ),
                    "Deploy the application with cost controls and latency monitoring",
                ],
                "practical_exercises": [
                    {
                        "title": "Enterprise RAG Assistant Portfolio",
                        "instructions": (
                            "Launch a complete GenAI assistant with document upload, "
                            "semantic search, streaming chat, and evaluation report."
                        ),
                        "estimated_minutes": 120,
                        "completed": False,
                    },
                ],
            },
        ],
    },
    "data_analyst": {
        "title": "Data Analyst & Business Intelligence Roadmap",
        "target_role": "data_analyst",
        "description": (
            "Transform raw datasets into actionable executive insights through advanced "
            "SQL, Python data wrangling, statistical analysis, and interactive dashboards."
        ),
        "target_skills": [
            "SQL",
            "PostgreSQL",
            "Python",
            "Pandas",
            "Data Analysis",
            "Data Visualization",
            "Statistics",
        ],
        "difficulty_level": "beginner",
        "total_estimated_hours": 70.0,
        "prerequisites": [
            {"topic": "Basic Spreadsheet Literacy (Excel / Google Sheets)", "required": True},
        ],
        "stages": [
            {
                "title": "Advanced SQL & Relational Analytics",
                "stage": "beginner",
                "description": (
                    "Master SQL query writing, window functions, common table expressions "
                    "(CTEs), and relational data aggregation."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    (
                        "Write complex analytical SQL queries using CTEs, window functions "
                        "(ROW_NUMBER, RANK, LAG/LEAD)"
                    ),
                    "Calculate cohort retention, rolling averages, and cumulative distributions",
                    "Design analytical views and materialized summary tables in PostgreSQL",
                ],
                "practical_exercises": [
                    {
                        "title": "Cohort Retention Query Lab",
                        "instructions": (
                            "Write an analytical SQL query calculating monthly user "
                            "retention cohorts."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                    {
                        "title": "Window Function Financial Analytics",
                        "instructions": (
                            "Calculate month-over-month growth, rolling 7-day revenue, and "
                            "customer rank in SQL."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Python Data Wrangling with Pandas",
                "stage": "intermediate",
                "description": (
                    "Automate data cleaning, normalization, reshaping, and time-series "
                    "aggregation using Pandas."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    (
                        "Ingest and merge disparate data sources (CSV, JSON, SQL databases, "
                        "public APIs)"
                    ),
                    "Detect and clean corrupted records, anomalies, and inconsistent date formats",
                    "Perform multi-index pivoting, unstacking, and time-series resampling",
                ],
                "practical_exercises": [
                    {
                        "title": "Data Cleaning & Imputation Script",
                        "instructions": (
                            "Clean a messy real-world dataset, handling null values and "
                            "standardized categorical codes."
                        ),
                        "estimated_minutes": 75,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Statistical Testing & Business Storytelling",
                "stage": "advanced",
                "description": (
                    "Validate business hypotheses with statistical significance testing and "
                    "design impactful executive presentations."
                ),
                "estimated_hours": 15.0,
                "learning_objectives": [
                    (
                        "Conduct A/B test hypothesis validation (t-tests, chi-square, "
                        "confidence intervals)"
                    ),
                    "Translate complex quantitative metrics into clear business recommendations",
                    "Structure analytical case studies with executive summaries and action items",
                ],
                "practical_exercises": [
                    {
                        "title": "A/B Test Significance Analysis",
                        "instructions": (
                            "Analyze conversion rate results from an experiment and produce "
                            "an executive decision memo."
                        ),
                        "estimated_minutes": 60,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Interactive BI Dashboard Portfolio",
                "stage": "portfolio",
                "description": (
                    "Build an end-to-end analytics dashboard with automated data pipelines "
                    "and clear KPI scorecards."
                ),
                "estimated_hours": 15.0,
                "learning_objectives": [
                    (
                        "Build interactive visualizations with Plotly, Streamlit, or BI "
                        "dashboarding tools"
                    ),
                    (
                        "Deploy a public interactive dashboard with filterable dimensions "
                        "and KPI cards"
                    ),
                    (
                        "Publish a case study report explaining business problem, "
                        "methodology, and insights"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Executive Business Intelligence Dashboard",
                        "instructions": (
                            "Build and deploy a dashboard tracking job market hiring "
                            "velocity and salary trends."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                ],
            },
        ],
    },
    "sde": {
        "title": "Software Development Engineer (SDE) Core Roadmap",
        "target_role": "sde",
        "description": (
            "Rigorous software engineering path covering Data Structures & Algorithms, "
            "Clean Architecture, Low-Level and High-Level System Design, and Concurrency."
        ),
        "target_skills": [
            "Data Structures",
            "Algorithms",
            "System Design",
            "Python",
            "OOP",
            "Testing",
            "SQL",
            "Git",
        ],
        "difficulty_level": "advanced",
        "total_estimated_hours": 95.0,
        "prerequisites": [
            {"topic": "Programming Fundamentals (Python / C++ / Java)", "required": True},
        ],
        "stages": [
            {
                "title": "Data Structures & Algorithmic Problem Solving",
                "stage": "beginner",
                "description": (
                    "Master algorithmic patterns: two pointers, sliding window, binary "
                    "search, trees, graphs, and dynamic programming."
                ),
                "estimated_hours": 30.0,
                "learning_objectives": [
                    "Analyze time and space complexity with Big-O asymptotic notation",
                    (
                        "Implement and manipulate core data structures (HashMaps, Heaps, "
                        "BSTs, Graphs, Tries)"
                    ),
                    (
                        "Solve algorithmic problems using depth-first search, breadth-first "
                        "search, and memoization"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Graph Traversal Algorithms",
                        "instructions": (
                            "Implement BFS and DFS to solve connected components and "
                            "shortest path problems."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                    {
                        "title": "Dynamic Programming Practice",
                        "instructions": (
                            "Implement top-down memoization and bottom-up tabulation for "
                            "classic optimization problems."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Object-Oriented Design & Clean Architecture",
                "stage": "intermediate",
                "description": (
                    "Apply SOLID principles, design patterns (Factory, Strategy, Observer, "
                    "Decorator), and refactoring techniques."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    (
                        "Design maintainable codebases adhering to Single Responsibility "
                        "and Open-Closed principles"
                    ),
                    (
                        "Implement behavioral, creational, and structural design patterns "
                        "in real-world scenarios"
                    ),
                    (
                        "Structure software with clean separation of domain entities, use "
                        "cases, and interfaces"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "Parking Lot / Ride-Share LLD",
                        "instructions": (
                            "Design clean class interfaces and state machines for an "
                            "object-oriented system."
                        ),
                        "estimated_minutes": 75,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "System Design & Distributed Scalability",
                "stage": "advanced",
                "description": (
                    "Architect scalable distributed systems: load balancers, caching, "
                    "database sharding, consistency models, and message queues."
                ),
                "estimated_hours": 25.0,
                "learning_objectives": [
                    "Evaluate CAP theorem tradeoffs, replication, and distributed consensus",
                    (
                        "Design high-throughput systems handling millions of daily active "
                        "users and writes"
                    ),
                    (
                        "Model database partitioning, read replicas, and caching strategies "
                        "(Write-Through, Cache-Aside)"
                    ),
                ],
                "practical_exercises": [
                    {
                        "title": "URL Shortener / Rate Limiter HLD",
                        "instructions": (
                            "Design complete architecture diagram, data schema, and API "
                            "contracts for a high-volume service."
                        ),
                        "estimated_minutes": 90,
                        "completed": False,
                    },
                ],
            },
            {
                "title": "Production Engineering Capstone",
                "stage": "portfolio",
                "description": (
                    "Build and benchmark a concurrent, fault-tolerant backend system with "
                    "rigorous unit and load tests."
                ),
                "estimated_hours": 20.0,
                "learning_objectives": [
                    "Implement concurrency controls and thread-safe data structures",
                    (
                        "Perform load testing with Locust or k6 to identify bottlenecks and "
                        "optimize p99 latency"
                    ),
                    "Author production post-mortems and architectural documentation",
                ],
                "practical_exercises": [
                    {
                        "title": "High-Throughput Key-Value Cache",
                        "instructions": (
                            "Build an in-memory key-value store with TTL expiration, LRU "
                            "eviction, and load benchmarks."
                        ),
                        "estimated_minutes": 120,
                        "completed": False,
                    },
                ],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# Deterministic Portfolio Project Recommendations Catalog
# ---------------------------------------------------------------------------

DETERMINISTIC_PROJECT_CATALOG: list[dict[str, Any]] = [
    {
        "title": "Distributed Asynchronous Job Processing Platform",
        "role_family": "backend_python",
        "objective": (
            "Build a resilient distributed worker platform that accepts heavy document "
            "processing jobs via REST APIs, distributes work across workers via message "
            "queues, and streams live progress via WebSockets/SSE."
        ),
        "tech_stack": ["Python", "FastAPI", "PostgreSQL", "Celery", "Redis", "Docker", "Pytest"],
        "target_skills": ["Python", "FastAPI", "Redis", "Celery", "PostgreSQL", "Docker"],
        "functional_requirements": [
            "Secure REST API endpoints for job submission, cancellation, and status inspection",
            (
                "Distributed worker cluster executing background workloads with retry and "
                "dead-letter queues"
            ),
            "Atomic rate limiting and task deduplication per user using Redis Lua scripts",
            "Audit event logging and structured JSON logging with correlation IDs",
            "Comprehensive integration test suite achieving >= 85% code coverage",
        ],
        "suggested_milestones": [
            {
                "milestone_title": "Database Schema & API Contracts",
                "description": (
                    "Design jobs table, status enum, and FastAPI CRUD endpoints with "
                    "Pydantic schemas."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Celery Worker & Redis Pacing",
                "description": (
                    "Configure Celery background tasks with Redis broker and atomic rate limiting."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Docker Compose & Automated Tests",
                "description": (
                    "Package the entire multi-container stack in Docker Compose with "
                    "passing pytest suite."
                ),
                "is_done": False,
            },
        ],
        "expected_portfolio_outcome": (
            "A production-ready GitHub repository with clean architecture, Docker Compose "
            "setup, comprehensive README, and architectural flow diagrams."
        ),
        "difficulty": "intermediate",
        "estimated_hours": 25.0,
    },
    {
        "title": "Enterprise RAG Document Intelligence System",
        "role_family": "genai",
        "objective": (
            "Build an enterprise document search and extraction platform that embeds "
            "unstructured technical manuals, performs hybrid semantic search, and "
            "synthesizes answers with strict citation grounding."
        ),
        "tech_stack": ["Python", "FastAPI", "Gemini API", "pgvector", "PostgreSQL", "Docker"],
        "target_skills": [
            "Generative AI",
            "RAG",
            "Vector Databases",
            "Prompt Engineering",
            "FastAPI",
            "Python",
        ],
        "functional_requirements": [
            "Document parsing and smart semantic chunking pipeline for technical PDFs",
            "Vector embeddings generation and indexing in PostgreSQL using pgvector",
            "Hybrid dense vector + sparse keyword search with similarity reranking",
            "Grounded answer generation with exact sentence-level citation references",
            "Prompt injection defense isolating untrusted document content in structured catalogs",
        ],
        "suggested_milestones": [
            {
                "milestone_title": "Document Parsing & pgvector Setup",
                "description": (
                    "Implement chunking and vector storage with cosine similarity indexing "
                    "in PostgreSQL."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "RAG Retrieval & Citation Synthesis",
                "description": (
                    "Build the retrieval pipeline and LLM citation synthesis with "
                    "hallucination defenses."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Evaluation Benchmarks & UI",
                "description": (
                    "Establish automated faithfulness benchmarks and build an interactive "
                    "web interface."
                ),
                "is_done": False,
            },
        ],
        "expected_portfolio_outcome": (
            "Demonstrates practical enterprise GenAI competency with measurable retrieval "
            "accuracy and zero-hallucination citation grounding."
        ),
        "difficulty": "advanced",
        "estimated_hours": 30.0,
    },
    {
        "title": "Modern Full-Stack Career Tracker & Analytics Dashboard",
        "role_family": "fullstack",
        "objective": (
            "Develop a full-stack SaaS platform enabling job seekers to track applications "
            "across stages, visualize conversion funnels, and manage resume variants with "
            "real-time analytics."
        ),
        "tech_stack": ["Next.js", "React", "TypeScript", "Tailwind CSS", "FastAPI", "PostgreSQL"],
        "target_skills": [
            "React",
            "Next.js",
            "TypeScript",
            "Tailwind CSS",
            "FastAPI",
            "PostgreSQL",
        ],
        "functional_requirements": [
            "Next.js App Router frontend with type-safe server and client components",
            "Interactive Kanban board for drag-and-drop application pipeline management",
            "Time-series conversion analytics and charts (application-to-interview conversion)",
            "JWT authentication with HttpOnly refresh cookies and protected route wrappers",
            "RESTful backend API with relational PostgreSQL persistence and Docker orchestration",
        ],
        "suggested_milestones": [
            {
                "milestone_title": "Backend REST API & Auth",
                "description": (
                    "Build authenticated CRUD endpoints for applications, status history, "
                    "and analytics."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Frontend UI & Kanban Board",
                "description": (
                    "Build responsive dashboard layout and interactive application tracking "
                    "board in Next.js."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Analytics Charts & Production Build",
                "description": (
                    "Integrate time-series charts, test static generation, and deploy to staging."
                ),
                "is_done": False,
            },
        ],
        "expected_portfolio_outcome": (
            "A complete, deployed full-stack SaaS portfolio piece demonstrating modern "
            "frontend UX and robust backend engineering."
        ),
        "difficulty": "intermediate",
        "estimated_hours": 30.0,
    },
    {
        "title": "Predictive Job Market Analytics & Salary Benchmarker",
        "role_family": "data_analyst",
        "objective": (
            "Build an end-to-end analytical pipeline that scrapes or ingests public job "
            "requisitions, cleans and normalizes compensation and skill data, and serves an "
            "interactive BI insights dashboard."
        ),
        "tech_stack": [
            "Python",
            "SQL",
            "PostgreSQL",
            "Pandas",
            "Data Analysis",
            "Data Visualization",
        ],
        "target_skills": [
            "SQL",
            "Python",
            "Pandas",
            "PostgreSQL",
            "Data Analysis",
            "Data Visualization",
        ],
        "functional_requirements": [
            (
                "Automated data ingestion and cleaning pipeline handling missing salaries "
                "and skill synonyms"
            ),
            (
                "Analytical PostgreSQL views calculating salary percentiles by role family "
                "and location"
            ),
            (
                "Exploratory data analysis identifying high-demand emerging technologies "
                "and compensation premiums"
            ),
            "Statistical significance testing comparing compensation across remote vs onsite roles",
            "Interactive visual dashboard with filterable dimensions and executive summaries",
        ],
        "suggested_milestones": [
            {
                "milestone_title": "Data Normalization & SQL Views",
                "description": (
                    "Clean messy salary data and create relational aggregation views in PostgreSQL."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Statistical Analysis & EDA",
                "description": (
                    "Conduct hypothesis testing and correlation analysis in Python Pandas."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Interactive Dashboard Case Study",
                "description": (
                    "Build and publish interactive web dashboard with written executive findings."
                ),
                "is_done": False,
            },
        ],
        "expected_portfolio_outcome": (
            "An analytical portfolio case study showcasing business problem formulation, "
            "rigorous data cleaning, and actionable visual insights."
        ),
        "difficulty": "intermediate",
        "estimated_hours": 20.0,
    },
    {
        "title": "High-Throughput Distributed Rate Limiter & Token Bucket Cache",
        "role_family": "sde",
        "objective": (
            "Design and implement an in-memory, thread-safe distributed rate limiter using "
            "the Token Bucket and Sliding Window algorithms with sub-millisecond latency."
        ),
        "tech_stack": [
            "Python",
            "Redis",
            "Algorithms",
            "Data Structures",
            "System Design",
            "Docker",
        ],
        "target_skills": ["Data Structures", "Algorithms", "System Design", "Python", "Redis"],
        "functional_requirements": [
            "Implement sliding window log and token bucket algorithms with atomic Redis operations",
            "Thread-safe local in-memory fallback cache with TTL expiration and LRU eviction",
            (
                "Benchmarking suite measuring throughput (requests/sec) and p99 latency "
                "under concurrent load"
            ),
            "Fault-tolerant failover behavior when the central Redis instance becomes unreachable",
            (
                "Detailed architectural whitepaper documenting trade-offs, time "
                "complexities, and race conditions"
            ),
        ],
        "suggested_milestones": [
            {
                "milestone_title": "Algorithm Implementation",
                "instructions": (
                    "Implement Token Bucket and Sliding Window counter in Python with unit tests."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Redis Lua Atomic Scripting",
                "instructions": (
                    "Write single-threaded Redis Lua scripts guaranteeing atomic "
                    "reservation without races."
                ),
                "is_done": False,
            },
            {
                "milestone_title": "Concurrency & Benchmark Suite",
                "instructions": (
                    "Run load test with Locust/concurrent threads and generate latency "
                    "distribution report."
                ),
                "is_done": False,
            },
        ],
        "expected_portfolio_outcome": (
            "Demonstrates low-level systems engineering depth, algorithmic precision, and "
            "distributed systems reasoning."
        ),
        "difficulty": "advanced",
        "estimated_hours": 25.0,
    },
]


# ---------------------------------------------------------------------------
# Roadmap Generation Engine
# ---------------------------------------------------------------------------


class RoadmapGenerationEngine:
    """
    Generates personalized learning roadmaps adapted to candidate demonstrated resume skills.
    Coordinates AI provider execution when configured, falling back to deterministic templates.
    """

    @classmethod
    def generate_roadmap(
        cls,
        target_role: str,
        demonstrated_skills: list[str],
        custom_skills: Optional[list[str]] = None,
        target_difficulty: str = "intermediate",
        user_notes: Optional[str] = None,
        provider_name: Optional[str] = None,
    ) -> tuple[dict[str, Any], str, str, bool]:
        """
        Generate structured roadmap.
        Returns: (roadmap_dict, provider_name, model_name, is_fallback)
        """
        # 1. Normalize role key
        normalized_role = cls._normalize_role_key(target_role)

        # 2. Check if AI provider can be used
        try:
            provider = get_ai_provider(provider_name)
            if provider.is_configured:
                ai_roadmap = cls._generate_ai_roadmap(
                    provider=provider,
                    target_role=target_role,
                    demonstrated_skills=demonstrated_skills,
                    custom_skills=custom_skills,
                    target_difficulty=target_difficulty,
                    user_notes=user_notes,
                )
                if ai_roadmap:
                    return ai_roadmap, provider.name, provider.model_name, False
        except Exception as e:
            logger.info(
                f"AI roadmap generation unavailable or failed ({e}); using deterministic engine"
            )

        # 3. Deterministic Generation (adapts to demonstrated resume skills)
        fallback_data = cls._generate_deterministic_roadmap(
            normalized_role=normalized_role,
            raw_role=target_role,
            demonstrated_skills=demonstrated_skills,
            custom_skills=custom_skills,
            target_difficulty=target_difficulty,
        )
        return fallback_data, "deterministic", "rule_based_v1", True

    @classmethod
    def _normalize_role_key(cls, role: str) -> str:
        r = role.lower().strip().replace("-", "_").replace(" ", "_")
        if "python" in r or "backend" in r:
            return "backend_python"
        elif "full" in r or "front" in r or "react" in r or "web" in r:
            return "fullstack"
        elif "genai" in r or "llm" in r or "generative" in r:
            return "genai"
        elif "ai" in r or "ml" in r or "machine" in r:
            return "ai_ml"
        elif "analyst" in r or "data" in r or "bi" in r:
            return "data_analyst"
        elif "sde" in r or "software" in r or "engineer" in r:
            return "sde"
        return "backend_python"

    @classmethod
    def _generate_deterministic_roadmap(
        cls,
        normalized_role: str,
        raw_role: str,
        demonstrated_skills: list[str],
        custom_skills: Optional[list[str]] = None,
        target_difficulty: str = "intermediate",
    ) -> dict[str, Any]:
        """
        Produce a tailored roadmap from template, adapting stages based on
        candidate's demonstrated skills.
        """
        template = DETERMINISTIC_ROADMAP_TRACKS.get(
            normalized_role,
            DETERMINISTIC_ROADMAP_TRACKS["backend_python"],
        )

        demo_skills_lower = {s.lower().strip() for s in demonstrated_skills}
        target_skills_list = list(template["target_skills"])
        if custom_skills:
            for cs in custom_skills:
                if cs not in target_skills_list:
                    target_skills_list.append(cs)

        # Identify which target skills candidate already demonstrated
        already_mastered = [
            skill for skill in target_skills_list if skill.lower().strip() in demo_skills_lower
        ]

        # Adapt prerequisites: flag if candidate already demonstrates them
        prereqs: list[dict[str, Any]] = []
        for p in template.get("prerequisites", []):
            topic = p["topic"]
            is_satisfied = False
            evidence = None
            for ds in demonstrated_skills:
                if ds.lower() in topic.lower():
                    is_satisfied = True
                    evidence = f"Supported by resume skill: {ds}"
                    break
            prereqs.append(
                {
                    "topic": topic,
                    "required": p.get("required", True),
                    "is_satisfied": is_satisfied,
                    "evidence": evidence,
                }
            )

        # Build milestones adapting exercises based on candidate mastery
        milestones: list[dict[str, Any]] = []
        total_hours = 0.0
        completed_hours = 0.0

        for idx, stage in enumerate(template["stages"]):
            stage_name = stage["stage"]
            # If candidate already mastered primary beginner skills, mark stage as completed
            is_beginner = stage_name == "beginner"
            should_mark_done = is_beginner and len(already_mastered) >= 2

            adapted_exercises = []
            for ex in stage["practical_exercises"]:
                ex_copy = dict(ex)
                if should_mark_done:
                    ex_copy["completed"] = True
                adapted_exercises.append(ex_copy)

            stage_hours = float(stage["estimated_hours"])
            stage_completed_hours = stage_hours if should_mark_done else 0.0
            stage_status = (
                "completed"
                if should_mark_done
                else ("in_progress" if idx == 0 and not should_mark_done else "not_started")
            )

            total_hours += stage_hours
            completed_hours += stage_completed_hours

            milestones.append(
                {
                    "title": stage["title"],
                    "stage": stage_name,
                    "description": stage["description"],
                    "learning_objectives": list(stage["learning_objectives"]),
                    "practical_exercises": adapted_exercises,
                    "status": stage_status,
                    "estimated_hours": stage_hours,
                    "completed_hours": stage_completed_hours,
                    "order_index": idx + 1,
                    "completion_notes": "Prerequisites satisfied by verified resume evidence."
                    if should_mark_done
                    else None,
                }
            )

        completion_pct = (
            round((completed_hours / total_hours * 100.0), 1) if total_hours > 0 else 0.0
        )

        return {
            "title": template["title"],
            "target_role": raw_role,
            "description": template["description"],
            "target_skills": target_skills_list,
            "status": "active",
            "difficulty_level": target_difficulty or template["difficulty_level"],
            "total_estimated_hours": total_hours,
            "completed_hours": completed_hours,
            "completion_percentage": completion_pct,
            "prerequisites": prereqs,
            "already_mastered_skills": already_mastered,
            "milestones": milestones,
            "metadata_json": {
                "generated_by": "deterministic_track_engine",
                "demonstrated_skills_count": len(demonstrated_skills),
                "already_mastered_count": len(already_mastered),
            },
        }

    @classmethod
    def _invoke_provider(cls, provider: Any, prompt: str) -> Optional[str]:
        """Invoke underlying provider client with structured prompt."""
        system_instruction = (
            "You are an expert technical curriculum designer. Return strictly valid JSON."
        )
        if getattr(provider, "name", None) == "gemini":
            client = getattr(provider, "client", None)
            if client:
                response = client.models.generate_content(
                    model=provider.model_name,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction,
                        "temperature": 0.2,
                        "response_mime_type": "application/json",
                    },
                )
                raw_text = getattr(response, "text", None)
                return str(raw_text) if raw_text else None
        elif getattr(provider, "name", None) == "openai":
            client = getattr(provider, "client", None)
            if client:
                response = client.chat.completions.create(
                    model=provider.model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                msg_content = response.choices[0].message.content
                return str(msg_content) if msg_content else None
        return None

    @classmethod
    def _generate_ai_roadmap(
        cls,
        provider: Any,
        target_role: str,
        demonstrated_skills: list[str],
        custom_skills: Optional[list[str]],
        target_difficulty: str,
        user_notes: Optional[str],
    ) -> Optional[dict[str, Any]]:
        """Call AI provider for custom roadmap generation with JSON schema enforcement."""
        demo_str = (
            ", ".join(demonstrated_skills) if demonstrated_skills else "None demonstrated yet"
        )
        custom_str = ", ".join(custom_skills) if custom_skills else "None"
        prompt = f"""You are a Career Coach designing a personalized learning roadmap.
Target Role: {target_role}
Candidate's Demonstrated Skills from Resume: {demo_str}
Custom Skills Requested: {custom_str}
Difficulty Tier: {target_difficulty}
User Notes: {user_notes or "Standard roadmap"}

Instructions:
1. Adapt roadmap to candidate's existing skills (do NOT reteach verified skills).
2. Produce 4 stages: beginner, intermediate, advanced, portfolio.
3. For each stage provide title, description, learning_objectives (3 items),
   practical_exercises (2-3 items with title, instructions, estimated_minutes),
   and estimated_hours.
4. Output strictly valid JSON matching this schema:
{{
  "title": "string",
  "description": "string",
  "target_skills": ["string"],
  "total_estimated_hours": 75.0,
  "prerequisites": [{{"topic": "string", "required": true, "is_satisfied": false}}],
  "already_mastered_skills": ["string"],
  "milestones": [
    {{
      "title": "string",
      "stage": "beginner",
      "description": "string",
      "learning_objectives": ["string"],
      "practical_exercises": [
        {{"title": "string", "instructions": "string", "estimated_minutes": 60, "completed": false}}
      ],
      "status": "not_started",
      "estimated_hours": 20.0,
      "completed_hours": 0.0,
      "order_index": 1
    }}
  ]
}}
Do NOT output any markdown backticks outside the JSON string."""

        raw_text = cls._invoke_provider(provider, prompt)
        if not raw_text:
            return None
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        data: dict[str, Any] = json.loads(text)
        data["target_role"] = target_role
        data["status"] = "active"
        data["difficulty_level"] = target_difficulty
        data["completed_hours"] = 0.0
        data["completion_percentage"] = 0.0
        data["metadata_json"] = {
            "generated_by": f"ai_provider:{getattr(provider, 'name', 'unknown')}",
            "model": getattr(provider, "model_name", "unknown"),
        }
        return data

    @classmethod
    def get_project_recommendations(
        cls,
        target_role: Optional[str] = None,
        missing_skills: Optional[list[str]] = None,
        limit: int = 4,
    ) -> list[dict[str, Any]]:
        """
        Recommend practical, realistic portfolio projects based on target role and missing skills.
        """
        normalized_role = cls._normalize_role_key(target_role or "backend_python")

        results: list[dict[str, Any]] = []
        # First check matching role family
        for proj in DETERMINISTIC_PROJECT_CATALOG:
            if proj["role_family"] == normalized_role:
                results.append(proj)

        # Then add projects covering missing skills
        missing_skills_lower = {s.lower() for s in (missing_skills or [])}
        for proj in DETERMINISTIC_PROJECT_CATALOG:
            if proj in results:
                continue
            proj_skills = {s.lower() for s in proj["target_skills"]}
            if proj_skills.intersection(missing_skills_lower):
                results.append(proj)

        # Fallback: add remaining projects up to limit
        for proj in DETERMINISTIC_PROJECT_CATALOG:
            if len(results) >= limit:
                break
            if proj not in results:
                results.append(proj)

        return results[:limit]
