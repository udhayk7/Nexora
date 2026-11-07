import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.orchestration.agents.base_agent import AgentResult, BaseAgent
from app.services.orchestration.candidate_context import SharedCandidateContext


class InterviewPreparationAgent(BaseAgent):
    """Generates personalized interview coaching plans, questions, and mock sessions."""

    name = "interview_preparation"
    description = (
        "Prepares tailored interview questions, STAR project breakdowns, and revision topics."
    )

    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        start_time = time.time()
        params = params or {}
        target_role = context.target_job_title or (
            context.target_roles[0] if context.target_roles else "Software Engineer"
        )
        target_company = context.target_company_name or "Target Employer"

        skills = context.verified_skills[:5] or ["Python", "FastAPI", "PostgreSQL", "Docker"]
        top_project = (
            context.verified_projects[0]["title"]
            if context.verified_projects
            else "Full Stack Architecture"
        )

        # Curate 3 tailored technical and behavioral questions
        tailored_questions = [
            {
                "category": "technical",
                "difficulty": "intermediate",
                "question": (
                    f"How do you design high-throughput REST APIs using {skills[0]} "
                    "and async request handling?"
                ),
                "rubric_focus": (
                    "Evaluates architectural correctness, performance optimization, and errors."
                ),
            },
            {
                "category": "project_deep_dive",
                "difficulty": "intermediate",
                "question": (
                    f"In '{top_project}', what was the primary architectural bottleneck "
                    "and how did you resolve it?"
                ),
                "rubric_focus": "Evaluates STAR structure, trade-offs, and measurable impact.",
            },
            {
                "category": "behavioral_hr",
                "difficulty": "beginner",
                "question": (
                    "Tell me about a time you encountered an ambiguous requirement "
                    "when building a software system."
                ),
                "rubric_focus": (
                    "Assesses communication clarity, proactive clarification, and collaboration."
                ),
            },
        ]

        revision_topics = [
            f"Core {skills[0]} concurrency models and async I/O patterns",
            "Database indexing strategies and connection pooling with PostgreSQL",
            "RESTful API security, authentication flows, and token rotation",
            "Docker containerization best practices and multi-stage builds",
        ]

        latency = int((time.time() - start_time) * 1000)

        proposals = [
            {
                "id": "action_start_mock_interview",
                "action_type": "start_mock_interview",
                "title": f"Start Mock Interview Session for {target_role}",
                "description": (
                    "Interactive question-by-question mock session with 6-dimension rubric scoring."
                ),
                "deep_link": "/dashboard/interview-prep",
                "requires_approval": False,
            }
        ]

        summary = (
            f"Constructed interview plan for {target_role} at {target_company}. "
            f"Curated {len(tailored_questions)} mock questions grounded in '{top_project}' and "
            f"formulated 4 core revision topics for {', '.join(skills[:3])}."
        )

        return AgentResult(
            agent_name=self.name,
            operation="plan_interview",
            status="completed",
            summary=summary,
            data={
                "target_role": target_role,
                "target_company": target_company,
                "featured_project": top_project,
                "revision_topics": revision_topics,
                "mock_questions": tailored_questions,
            },
            action_proposals=proposals,
            latency_ms=latency,
            tokens_used=150,
            provider="deterministic",
        )
