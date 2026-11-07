import json
import re
from typing import Any, Optional

from app.core.logging import logger
from app.models.job import Job
from app.schemas.analysis import ResumeAnalysisResult
from app.services.ai.factory import get_ai_provider

QUESTION_GENERATION_SYSTEM_INSTRUCTION = """You are Nexora's Senior Technical Interviewer.
Your objective is to generate rigorous, authentic, role-specific interview questions.

CONSTRAINTS & RULES:
1. ROLE SPECIFICITY: Questions must test concepts strictly relevant to <JOB_DATA>.
2. REAL RESUME CONTEXT: Ground questions in projects and skills in <RESUME_DATA>.
   Never invent or assume projects the candidate never built.
3. DIFFICULTY CALIBRATION:
   - beginner: Fundamental syntax, core data structures, basic API endpoints.
   - intermediate: Concurrency, error handling, query optimization, trade-offs.
   - advanced: Distributed systems, caching, race conditions, resilience patterns.
4. CODE SAFETY: Evaluate code statically. Never execute arbitrary code.
5. FORMAT: Return strictly valid JSON array conforming to the requested schema.
"""


class DeterministicQuestionGenerator:
    """Provides category-specific questions when AI is unavailable."""

    QUESTION_BANK = {
        "technical": {
            "beginner": [
                {
                    "question_text": (
                        "How do value types and reference types differ in memory, "
                        "and how does garbage collection affect application "
                        "performance?"
                    ),
                    "context_hint": (
                        "Consider stack vs heap allocation and pointer dereferencing."
                    ),
                    "expected_points": [
                        ("Stack holds primitive types with fixed size and deterministic lifetime"),
                        ("Heap stores dynamic reference objects managed by garbage collection"),
                        "Garbage collection pauses can introduce latency spikes",
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Accurately differentiates stack and heap memory semantics"
                        ),
                        "completeness": (
                            "Mentions both memory layout and garbage collection impact"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Stack allocation. 2. Heap allocation. 3. GC overhead trade-offs."
                    ),
                },
                {
                    "question_text": (
                        "Explain the difference between synchronous and asynchronous "
                        "operations. When should you use async programming in web "
                        "services?"
                    ),
                    "context_hint": (
                        "Think about I/O-bound operations versus CPU-bound computation."
                    ),
                    "expected_points": [
                        ("Synchronous blocks execution thread until operation completes"),
                        ("Asynchronous frees event loop to handle other requests during I/O wait"),
                        ("Ideal for database queries, network requests, and streaming"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Correctly identifies event loop mechanics and non-blocking I/O"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Blocking vs non-blocking. 2. Concurrency model. 3. "
                        "Practical web API example."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "How do you detect, debug, and resolve memory leaks in a "
                        "production service?"
                    ),
                    "context_hint": (
                        "Discuss heap dumps, profiling tools, and common circular references."
                    ),
                    "expected_points": [
                        ("Use memory profiling tools (e.g. tracemalloc, pprof, heap snapshots)"),
                        ("Monitor Resident Set Size (RSS) and garbage collection frequency"),
                        ("Identify unclosed resources, persistent global state, or circular refs"),
                    ],
                    "evaluation_criteria": {
                        "correctness": "Describes real production diagnostic workflows",
                    },
                    "ideal_answer_outline": (
                        "1. Telemetry and detection. 2. Profiling snapshots. 3. Remediation."
                    ),
                },
                {
                    "question_text": (
                        "Explain database connection pooling. What problems happen "
                        "if pool size is configured too small or too large?"
                    ),
                    "context_hint": (
                        "Consider PostgreSQL connection process overhead versus file descriptors."
                    ),
                    "expected_points": [
                        ("Connection handshakes (TCP + TLS + auth) are computationally expensive"),
                        (
                            "Too small: incoming requests queue up, resulting in latency "
                            "and timeouts"
                        ),
                        ("Too large: exhausts database backend processes, RAM, and disk I/O"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Accurately analyzes database resource contention and queueing"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Purpose of pools. 2. Undersized risks. 3. Oversized contention."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "How would you design a distributed rate limiter that "
                        "handles 50,000 requests per second across multiple data "
                        "centers?"
                    ),
                    "context_hint": (
                        "Consider sliding window log vs token bucket and Redis synchronization."
                    ),
                    "expected_points": [
                        "Token bucket or sliding window counter algorithm",
                        ("Atomic Redis operations (e.g. Lua scripts) to prevent race conditions"),
                        ("Local in-memory batching with asynchronous centralized sync for latency"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Addresses concurrency, clock skew, and partition fail-open policies"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Algorithm choice. 2. Storage architecture. 3. Cross-region trade-offs."
                    ),
                },
            ],
        },
        "coding_problem_solving": {
            "beginner": [
                {
                    "question_text": (
                        "Given an array of integers nums and target, return indices "
                        "of the two numbers that add up to target. Explain time and "
                        "space complexity."
                    ),
                    "context_hint": (
                        "Consider using a hash map to look up the complement in O(1) time."
                    ),
                    "expected_points": [
                        "Brute force O(N^2) checks every pair",
                        ("Optimal O(N) time and O(N) space using single-pass hash map"),
                        ("Check if target - num exists in map before adding current number"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Provides optimal O(N) hash map solution with accurate complexity"
                        ),
                    },
                    "ideal_answer_outline": "1. Constraints. 2. Hash map algorithm. 3. Edge cases.",
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "Given a list of job application intervals [[start, end]], "
                        "merge all overlapping intervals and return an array of "
                        "non-overlapping intervals."
                    ),
                    "context_hint": (
                        "Sorting intervals by start time simplifies overlap detection."
                    ),
                    "expected_points": [
                        "Sort intervals primarily by start time O(N log N)",
                        (
                            "Iterate through sorted intervals and compare current start "
                            "with previous end"
                        ),
                        ("If overlapping: prev.end = max(prev.end, current.end); else append"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Correctly sorts before merging with O(N log N) time and O(N) space"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Sorting step. 2. Linear merge loop. 3. Complexity analysis."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "Implement a Least Recently Used (LRU) Cache with get and "
                        "put operations in O(1) time complexity."
                    ),
                    "context_hint": "Combine a hash map with a doubly linked list.",
                    "expected_points": [
                        "Hash map provides O(1) lookup of node pointers",
                        ("Doubly linked list allows O(1) removal and insertion at head/tail"),
                        ("When capacity exceeded, evict tail node and remove from hash map"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Integrates doubly linked list with hash map for strict O(1) runtime"
                        ),
                    },
                    "ideal_answer_outline": "1. Data structures. 2. get logic. 3. put/eviction.",
                },
            ],
        },
        "backend_python": {
            "beginner": [
                {
                    "question_text": (
                        "What is Python's Global Interpreter Lock (GIL), and how "
                        "does it influence multithreaded versus multiprocessing "
                        "applications?"
                    ),
                    "context_hint": (
                        "Consider CPython's reference counting and multi-core CPU utilization."
                    ),
                    "expected_points": [
                        (
                            "GIL is a mutex preventing multiple native threads from "
                            "executing bytecodes"
                        ),
                        (
                            "I/O-bound tasks benefit from threading because GIL is "
                            "released during I/O"
                        ),
                        ("CPU-bound tasks require multiprocessing to utilize multiple CPU cores"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Distinguishes between I/O-bound concurrency and CPU parallelism"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Definition of GIL. 2. Threading for I/O. 3. Multiprocessing for CPU."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "In FastAPI, how does dependency injection work with "
                        "Depends(), and how do async def and def route handlers "
                        "differ in concurrency?"
                    ),
                    "context_hint": (
                        "Consider AnyIO threadpool execution for def versus event "
                        "loop for async def."
                    ),
                    "expected_points": [
                        (
                            "Depends() resolves hierarchical dependencies, sharing db "
                            "sessions per request"
                        ),
                        ("async def runs cooperatively on main event loop without blocking calls"),
                        ("def routes are automatically dispatched to worker threadpool by FastAPI"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Distinguishes async event loop execution from AnyIO "
                            "threadpool dispatch"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Dependency lifecycle. 2. async def rule. 3. def threadpool."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "How would you optimize a high-throughput Celery background "
                        "worker setup consuming messages from Redis under heavy burst "
                        "loads?"
                    ),
                    "context_hint": (
                        "Think about worker concurrency (prefork vs gevent), task "
                        "prefetch, and ACK late."
                    ),
                    "expected_points": [
                        ("Tune worker_prefetch_multiplier=1 to prevent task starvation"),
                        ("Configure task_acks_late=True with idempotency to survive restarts"),
                        ("Select prefork for CPU-bound tasks, gevent for high-volume I/O tasks"),
                    ],
                    "evaluation_criteria": {
                        "correctness": "Demonstrates real production Celery tuning knowledge",
                    },
                    "ideal_answer_outline": (
                        "1. Prefetch multiplier. 2. Acks late and retries. 3. Concurrency pool."
                    ),
                },
            ],
        },
        "frontend_fullstack": {
            "beginner": [
                {
                    "question_text": (
                        "Explain how React's Virtual DOM works and how "
                        "reconciliation optimizes browser rendering performance."
                    ),
                    "context_hint": "Discuss diffing algorithms, key props, and batched updates.",
                    "expected_points": [
                        ("Virtual DOM is an in-memory lightweight representation of the real DOM"),
                        (
                            "Reconciliation compares previous and next virtual trees "
                            "using diffing heuristics"
                        ),
                        (
                            "Key props allow React to identify moved, added, or deleted "
                            "list items efficiently"
                        ),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Clearly explains diffing heuristics, keys, and batched mutations"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Virtual DOM concept. 2. Reconciliation diffing. 3. Key "
                        "prop significance."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "How do you manage client-side state versus server-cache "
                        "state in a modern Next.js/React application?"
                    ),
                    "context_hint": (
                        "Compare React Context/Zustand with React Query/SWR for cache invalidation."
                    ),
                    "expected_points": [
                        ("Client state (modals, drafts) managed with Zustand or React useState"),
                        ("Server state (jobs, applications) managed with React Query / SWR"),
                        (
                            "Server state includes caching, revalidation on focus, and "
                            "optimistic updates"
                        ),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Differentiates ephemeral client state from asynchronous server cache"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Client vs server state. 2. Stale-while-revalidate. 3. Optimistic UI."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "How would you diagnose and eliminate layout shifts (CLS) "
                        "and slow interaction to next paint (INP) in a complex "
                        "dashboard?"
                    ),
                    "context_hint": (
                        "Discuss Web Vitals, heavy JavaScript main-thread blocking, "
                        "and CSS layout containment."
                    ),
                    "expected_points": [
                        (
                            "Audit with Chrome DevTools Performance panel and Core Web "
                            "Vitals profiler"
                        ),
                        (
                            "Reserve explicit aspect-ratio or dimensions for dynamic "
                            "images and skeletons"
                        ),
                        (
                            "Break long JavaScript tasks (>50ms) using "
                            "requestAnimationFrame or web workers"
                        ),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Mastery of Core Web Vitals optimization and main-thread scheduling"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Measurement metrics. 2. Layout shift prevention. 3. INP task slicing."
                    ),
                },
            ],
        },
        "ai_ml_genai": {
            "beginner": [
                {
                    "question_text": (
                        "What is the difference between Retrieval-Augmented "
                        "Generation (RAG) and model fine-tuning? When would you "
                        "choose RAG?"
                    ),
                    "context_hint": (
                        "Consider dynamic private knowledge versus learning "
                        "linguistic style/domain syntax."
                    ),
                    "expected_points": [
                        (
                            "RAG injects relevant external context dynamically into "
                            "prompt window at inference"
                        ),
                        (
                            "Fine-tuning updates model weights for style, format, or "
                            "specialized domain tasks"
                        ),
                        (
                            "RAG is preferred for rapidly changing factual data and "
                            "transparent source citation"
                        ),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Clearly articulates the distinct use cases of RAG versus "
                            "weight updates"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. RAG architecture. 2. Fine-tuning mechanism. 3. Cost and "
                        "latency comparison."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "How do you prevent prompt injection and guarantee "
                        "deterministic JSON output from LLMs in a production backend?"
                    ),
                    "context_hint": (
                        "Discuss structured outputs, schema enforcement, and "
                        "delimiter boundary defense."
                    ),
                    "expected_points": [
                        (
                            "Enforce strict JSON schemas (OpenAI structured outputs or "
                            "Pydantic validation)"
                        ),
                        ("Isolate untrusted user input within explicit XML/markdown boundaries"),
                        (
                            "Add automated retries with deterministic heuristic "
                            "fallbacks upon parse failure"
                        ),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Comprehensive security defense against injection and schema drift"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Schema constraints. 2. Prompt delimiters. 3. Fallback resilience."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "How would you design a vector embedding search pipeline for "
                        "10 million resume passages with low-latency similarity "
                        "search?"
                    ),
                    "context_hint": (
                        "Compare HNSW versus IVF indexing, dimension reduction, and "
                        "metadata filtering."
                    ),
                    "expected_points": [
                        (
                            "Use HNSW (Hierarchical Navigable Small World) graphs for "
                            "sub-10ms recall"
                        ),
                        (
                            "Pre-filter or post-filter metadata (e.g. user_id, date) "
                            "with hybrid search indexes"
                        ),
                        ("Implement chunking strategies with overlap to preserve semantic context"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Deep understanding of vector quantization, HNSW graphs, and "
                            "hybrid search"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Chunking and embedding. 2. Vector index selection. 3. "
                        "Hybrid query execution."
                    ),
                },
            ],
        },
        "database_sql": {
            "beginner": [
                {
                    "question_text": (
                        "What is the difference between INNER JOIN, LEFT OUTER JOIN, "
                        "and FULL OUTER JOIN? When would you use a LEFT JOIN?"
                    ),
                    "context_hint": (
                        "Think about finding users who have not yet submitted any job applications."
                    ),
                    "expected_points": [
                        "INNER JOIN returns only rows with matches in both tables",
                        (
                            "LEFT JOIN returns all rows from left table, filling NULLs "
                            "for non-matching right"
                        ),
                        ("Use LEFT JOIN to find missing relationships (WHERE right.id IS NULL)"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Clearly explains result set cardinality and NULL handling"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Conceptual definitions. 2. NULL value semantics. 3. Example query."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "What is the N+1 query problem in ORMs, and how do you "
                        "resolve it in PostgreSQL using SQLAlchemy or SQL joins?"
                    ),
                    "context_hint": (
                        "Think about fetching 100 applications and querying company "
                        "details individually."
                    ),
                    "expected_points": [
                        (
                            "Initial query loads parent records, then N separate queries "
                            "fetch children"
                        ),
                        ("Resolved using eager loading (joinedload, selectinload in SQLAlchemy)"),
                        ("Reduces round trips from N+1 network requests to 1 or 2 batched queries"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Accurately identifies ORM laziness trap and batched loading strategies"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Symptom analysis. 2. Eager loading solutions. 3. Performance impact."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "Explain PostgreSQL transaction isolation levels (Read "
                        "Committed, Repeatable Read, Serializable). What is write "
                        "skew?"
                    ),
                    "context_hint": (
                        "Discuss Multi-Version Concurrency Control (MVCC) and predicate locking."
                    ),
                    "expected_points": [
                        ("Read Committed is default: sees commits prior to statement start"),
                        ("Repeatable Read: transaction sees snapshot taken at transaction start"),
                        (
                            "Serializable uses SSI (Serializable Snapshot Isolation) "
                            "with predicate locks"
                        ),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Mastery of MVCC snapshot isolation and concurrency anomalies"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Isolation levels. 2. Phantom reads. 3. SSI and serialization failures."
                    ),
                },
            ],
        },
        "system_design": {
            "beginner": [
                {
                    "question_text": (
                        "What is the difference between vertical scaling and "
                        "horizontal scaling? What are the key trade-offs?"
                    ),
                    "context_hint": "Consider single point of failure, cost, and load balancing.",
                    "expected_points": [
                        ("Vertical scaling adds more CPU/RAM to a single node; limited by ceiling"),
                        (
                            "Horizontal scaling adds more instances behind a load "
                            "balancer; resilient"
                        ),
                        (
                            "Horizontal scaling requires stateless application design "
                            "and distributed data"
                        ),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Explains architectural trade-offs, state management, and redundancy"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Definitions. 2. Stateless servers. 3. Database "
                        "bottleneck considerations."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "How would you design a notifications service that sends "
                        "interview reminders via email, web push, and in-app alerts "
                        "at scheduled times?"
                    ),
                    "context_hint": (
                        "Think about message queues, delayed job scheduling, "
                        "idempotency, and preferences."
                    ),
                    "expected_points": [
                        (
                            "Scheduled jobs queue (e.g. Celery beat / Redis sorted sets) "
                            "to query upcoming"
                        ),
                        ("Idempotency keys on notifications to prevent duplicate dispatch"),
                        ("Check user notification preferences and timezone before dispatch"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Covers scheduling mechanics, retry backoff, and duplicate prevention"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Ingestion and scheduling. 2. Worker idempotency. 3. "
                        "Channel dispatchers."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "Design a high-scale real-time Job Search & Filtering "
                        "platform indexing 10 million postings. How do you handle "
                        "rapid faceted filtering?"
                    ),
                    "context_hint": (
                        "Consider search engines like Elasticsearch, inverted "
                        "indexes, and TTL caches."
                    ),
                    "expected_points": [
                        ("Inverted index for keyword search combined with columnar doc-values"),
                        (
                            "CDC (Change Data Capture) pipeline from primary DB to "
                            "search cluster via Kafka"
                        ),
                        ("Scheduled freshness recheck workers with TTL-based state transitions"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Separates transactional OLTP from search indexing and "
                            "eventual consistency"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Primary DB vs Search index. 2. Ingestion pipeline. 3. "
                        "Faceted filtering."
                    ),
                },
            ],
        },
        "project_deep_dive": {
            "beginner": [
                {
                    "question_text": (
                        "Give an elevator pitch of the primary technical project on "
                        "your resume. What problem did it solve, and what "
                        "technologies did you choose?"
                    ),
                    "context_hint": (
                        "Summarize user problem, solution architecture, and your direct role."
                    ),
                    "expected_points": [
                        "Clear statement of user problem and business context",
                        ("Concise description of technical stack and components built"),
                        "Your specific personal ownership and contributions",
                    ],
                    "evaluation_criteria": {
                        "correctness": "Concise, structured delivery without unnecessary jargon",
                    },
                    "ideal_answer_outline": (
                        "1. Problem statement. 2. Tech stack choice. 3. What you built. 4. Results."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "Walk me through the architecture of a major technical "
                        "project listed on your resume. What was the most challenging "
                        "technical decision you made?"
                    ),
                    "context_hint": (
                        "Structure your answer: Context -> Architecture -> Technical "
                        "Decision -> Trade-off."
                    ),
                    "expected_points": [
                        ("Clear summary of the project goal and business motivation"),
                        (
                            "Specific architectural components (frontend, API server, "
                            "database, worker queue)"
                        ),
                        ("A concrete trade-off (e.g. sync vs async, datastore choice)"),
                        "Measurable outcome or lesson learned from implementation",
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Grounded in actual evidenced work without hand-waving architecture"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Elevator pitch. 2. Architecture overview. 3. Tough "
                        "decision. 4. Reflection."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "If traffic to your resume project suddenly increased by "
                        "100x tomorrow, which component would bottleneck first, and "
                        "how would you redesign it?"
                    ),
                    "context_hint": (
                        "Analyze database queries, connection limits, synchronous "
                        "endpoints, and cache misses."
                    ),
                    "expected_points": [
                        (
                            "Identifies exact bottleneck (e.g. unindexed SQL queries, "
                            "single-node writes)"
                        ),
                        (
                            "Proposes concrete mitigation: Redis caching, read replicas, "
                            "async workers"
                        ),
                        ("Explains how to monitor and verify the fix using telemetry"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Realistic bottleneck identification and horizontal scaling strategy"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Current bottleneck analysis. 2. Scaling strategy. 3. "
                        "Verification metrics."
                    ),
                },
            ],
        },
        "internship_experience": {
            "beginner": [
                {
                    "question_text": (
                        "What was the most important engineering practice or "
                        "workflow you learned during your internship or team "
                        "projects?"
                    ),
                    "context_hint": (
                        "Discuss version control, code reviews, writing tests, or agile standups."
                    ),
                    "expected_points": [
                        ("Mentions code review feedback and addressing PR comments constructively"),
                        "Discusses writing automated tests to prevent regressions",
                        ("Highlights communicating blockers early during daily standups"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Demonstrates team collaboration maturity and engineering discipline"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Workflow context. 2. Specific lesson learned. 3. "
                        "Long-term impact on habits."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "Describe a production feature or bug fix you delivered "
                        "during your internship or project. How did you verify it was "
                        "safe to deploy?"
                    ),
                    "context_hint": (
                        "Walk through requirement understanding, implementation, "
                        "testing, and deployment."
                    ),
                    "expected_points": [
                        ("Clear scope of the feature or bug and acceptance criteria"),
                        (
                            "Testing strategy: unit tests, integration tests, and "
                            "staging verification"
                        ),
                        ("Monitoring after rollout (error logs, metrics dashboards)"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Shows thorough end-to-end delivery awareness and safety precautions"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Context. 2. Implementation details. 3. Testing and "
                        "verification. 4. Rollout."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "Tell me about a time you had to push back on a technical "
                        "requirement or proposed an architectural improvement during "
                        "a project."
                    ),
                    "context_hint": (
                        "Focus on data-driven reasoning, collaborative discussion, "
                        "and user outcome."
                    ),
                    "expected_points": [
                        ("Identified risk or inefficiency with evidence or benchmarks"),
                        ("Proposed alternative approach with clear trade-offs explained"),
                        ("Collaborated with team/mentor to reach consensus and deliver outcome"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Highlights professional, evidence-based advocacy and team alignment"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Initial requirement. 2. Evidence-based concern. 3. "
                        "Solution. 4. Outcome."
                    ),
                },
            ],
        },
        "behavioral_hr": {
            "beginner": [
                {
                    "question_text": (
                        "Tell me about a time you encountered a software bug that "
                        "was difficult to reproduce. How did you diagnose and solve "
                        "it?"
                    ),
                    "context_hint": "Use the STAR method: Situation, Task, Action, Result.",
                    "expected_points": [
                        "Situation: Clear context of the bug and its impact",
                        "Task: What you personally investigated",
                        ("Action: Concrete diagnostic steps (logs, isolated test, git bisect)"),
                        ("Result: Fix implemented, verified, and regression test added"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Demonstrates structured technical troubleshooting and STAR narrative"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Situation. 2. Task. 3. Action. 4. Result and post-mortem."
                    ),
                },
            ],
            "intermediate": [
                {
                    "question_text": (
                        "How do you prioritize competing deadlines when working on "
                        "multiple features or coursework projects simultaneously?"
                    ),
                    "context_hint": (
                        "Discuss communication with stakeholders and breaking tasks "
                        "into milestones."
                    ),
                    "expected_points": [
                        "Assess urgency vs impact",
                        (
                            "Communicate proactively with managers/team members rather "
                            "than going silent"
                        ),
                        "Break work into incremental verifiable milestones",
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Highlights proactive communication, time estimation, and "
                            "milestone delivery"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Triage framework. 2. Stakeholder alignment. 3. Example story."
                    ),
                },
            ],
            "advanced": [
                {
                    "question_text": (
                        "Tell me about a disagreement you had with a team member "
                        "about a technical approach. How did you resolve it?"
                    ),
                    "context_hint": (
                        "Focus on decoupling ego from decisions, running benchmarks, "
                        "and team alignment."
                    ),
                    "expected_points": [
                        ("Listen actively to understand the other perspective's technical merits"),
                        (
                            "Use objective data, prototypes, or benchmarks rather than "
                            "subjective opinions"
                        ),
                        ("Commit fully to the agreed direction once decision is made"),
                    ],
                    "evaluation_criteria": {
                        "correctness": (
                            "Shows professional maturity, empathy, and collaborative "
                            "conflict resolution"
                        ),
                    },
                    "ideal_answer_outline": (
                        "1. Context of dispute. 2. Objective evaluation. 3. Resolution and impact."
                    ),
                },
            ],
        },
    }

    @classmethod
    def generate(
        cls,
        job: Job,
        resume_analysis: ResumeAnalysisResult,
        category: str = "technical",
        difficulty: str = "intermediate",
        question_count: int = 5,
        project_name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        bank = cls.QUESTION_BANK.get(category, cls.QUESTION_BANK["technical"])
        pool = bank.get(difficulty, bank.get("intermediate", []))

        if not pool:
            pool = cls.QUESTION_BANK["technical"].get(
                difficulty, cls.QUESTION_BANK["technical"]["intermediate"]
            )

        questions: list[dict[str, Any]] = []
        for i in range(min(question_count, len(pool) * 3)):
            template = pool[i % len(pool)]
            q_copy: dict[str, Any] = dict(template)
            q_copy["question_order"] = len(questions) + 1
            q_copy["category"] = category
            q_copy["difficulty"] = difficulty
            if project_name:
                q_copy["project_name"] = project_name
                if "project" in category:
                    comp = job.company.name if job and job.company else "production"
                    q_copy["question_text"] = (
                        f"In your project '{project_name}', walk me through the architecture. "
                        f"How did you implement data persistence and scaling for {comp}?"
                    )
            questions.append(q_copy)
            if len(questions) >= question_count:
                break

        return questions


class InterviewQuestionEngine:
    """Coordinates AI-powered question generation with fallback."""

    @classmethod
    def _invoke_provider(cls, provider: Any, prompt: str) -> Optional[str]:
        """Invoke underlying provider client with structured prompt."""
        if provider.name == "gemini":
            client = getattr(provider, "client", None)
            if client:
                response = client.models.generate_content(
                    model=provider.model_name,
                    contents=prompt,
                    config={
                        "system_instruction": QUESTION_GENERATION_SYSTEM_INSTRUCTION,
                        "temperature": 0.3,
                        "response_mime_type": "application/json",
                    },
                )
                raw_text = getattr(response, "text", None)
                return str(raw_text) if raw_text else None
        elif provider.name == "openai":
            client = getattr(provider, "client", None)
            if client:
                response = client.chat.completions.create(
                    model=provider.model_name,
                    messages=[
                        {"role": "system", "content": QUESTION_GENERATION_SYSTEM_INSTRUCTION},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )
                msg_content = response.choices[0].message.content
                return str(msg_content) if msg_content else None
        return None

    @classmethod
    def generate_questions(
        cls,
        job: Job,
        resume_analysis: ResumeAnalysisResult,
        category: str = "technical",
        difficulty: str = "intermediate",
        question_count: int = 5,
        user_instructions: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> tuple[list[dict[str, Any]], str, str, bool]:
        """
        Generate grounded interview questions.
        Returns: (questions_list, provider, model, is_fallback)
        """
        provider = get_ai_provider()
        if not provider or not provider.is_configured:
            fallback = DeterministicQuestionGenerator.generate(
                job=job,
                resume_analysis=resume_analysis,
                category=category,
                difficulty=difficulty,
                question_count=question_count,
                project_name=project_name,
            )
            return fallback, "deterministic", "rule_based_v1", True

        try:
            prompt = cls._build_prompt(
                job=job,
                resume_analysis=resume_analysis,
                category=category,
                difficulty=difficulty,
                question_count=question_count,
                user_instructions=user_instructions,
                project_name=project_name,
            )

            raw_text = cls._invoke_provider(provider, prompt)
            if raw_text:
                parsed = cls._parse_ai_output(raw_text)
                if parsed and len(parsed) > 0:
                    for idx, q in enumerate(parsed, 1):
                        q["question_order"] = idx
                        q["category"] = q.get("category", category)
                        q["difficulty"] = q.get("difficulty", difficulty)
                        if project_name:
                            q["project_name"] = project_name
                    return parsed[:question_count], provider.name, provider.model_name, False

            fallback = DeterministicQuestionGenerator.generate(
                job=job,
                resume_analysis=resume_analysis,
                category=category,
                difficulty=difficulty,
                question_count=question_count,
                project_name=project_name,
            )
            return fallback, provider.name, provider.model_name, True

        except Exception as exc:
            logger.info("AI question generation failed; using deterministic generator: %s", exc)
            fallback = DeterministicQuestionGenerator.generate(
                job=job,
                resume_analysis=resume_analysis,
                category=category,
                difficulty=difficulty,
                question_count=question_count,
                project_name=project_name,
            )
            return fallback, "deterministic", "rule_based_v1", True

    @classmethod
    def _build_prompt(
        cls,
        job: Job,
        resume_analysis: ResumeAnalysisResult,
        category: str,
        difficulty: str,
        question_count: int,
        user_instructions: Optional[str],
        project_name: Optional[str],
    ) -> str:
        job_ctx = {
            "title": job.title,
            "company": job.company.name if job.company else "Company",
            "skills": job.skills_tags or [],
            "description": job.description[:2000],
        }
        candidate_ctx = {
            "supported_skills": (
                resume_analysis.skills.supported_skills if resume_analysis.skills else []
            ),
            "projects": [
                {"section": ev.section, "excerpt": ev.excerpt}
                for ev in (
                    resume_analysis.experience_evidence.evidence[:4]
                    if resume_analysis.experience_evidence
                    else []
                )
            ],
            "selected_project": project_name,
        }

        default_inst = "Focus on practical problem solving, clear architecture, and trade-offs."
        header = f"Generate {question_count} questions for '{category}' at '{difficulty}'."
        return f"""{header}

<JOB_DATA>
{json.dumps(job_ctx, indent=2)}
</JOB_DATA>

<RESUME_DATA>
{json.dumps(candidate_ctx, indent=2)}
</RESUME_DATA>

<INSTRUCTIONS>
{user_instructions or default_inst}
</INSTRUCTIONS>

Return a JSON array of objects with keys:
- question_text: str
- context_hint: str
- expected_points: list of str
- evaluation_criteria: object with correctness, completeness, clarity
- ideal_answer_outline: str
"""

    @classmethod
    def _parse_ai_output(cls, raw_response: Any) -> Optional[list[dict[str, Any]]]:
        text = raw_response if isinstance(raw_response, str) else str(raw_response)
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            json_match = re.search(r"(\[.*\])", text, re.DOTALL)
            if json_match:
                text = json_match.group(1)

        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return None
