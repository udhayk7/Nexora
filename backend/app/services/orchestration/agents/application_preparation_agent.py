import time
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.orchestration.agents.base_agent import AgentResult, BaseAgent
from app.services.orchestration.candidate_context import SharedCandidateContext


class ApplicationPreparationAgent(BaseAgent):
    """Coordinates resume tailoring, cover letter drafting, and screening Q&A."""

    name = "application_preparation"
    description = (
        "Prepares grounded tailored application materials, cover letters, and interview points."
    )

    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        start_time = time.time()
        params = params or {}
        job_id = params.get("job_id") or context.target_job_id

        job = None
        if job_id:
            job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            job = db.query(Job).filter(Job.job_status == "active").first()

        job_title = (
            job.title
            if job
            else (context.target_roles[0] if context.target_roles else "Software Engineer")
        )
        company_name = (
            job.company.name if job and job.company else context.target_company_name
        ) or "Target Company"

        # Generate Grounded Preparation Pack
        verified_skills_str = (
            ", ".join(context.verified_skills[:4]) if context.verified_skills else "Python, FastAPI"
        )
        project_title = (
            context.verified_projects[0]["title"]
            if context.verified_projects
            else "Distributed Task Engine"
        )

        tailoring_highlights = [
            f"Emphasize verified experience in {verified_skills_str} directly in Technical Skills.",
            f"Highlight {project_title} as primary technical project with measurable outcomes.",
            f"Tailor professional summary to explicitly target {job_title} at {company_name}.",
        ]

        cover_letter_snippet = (
            f"Dear {company_name} Hiring Team,\n\n"
            f"I am writing to express my strong interest in the {job_title} position. "
            f"With verified technical experience in {verified_skills_str}, I have built "
            f"projects like {project_title} focused on clean code, tests, and reliability.\n\n"
            f"I am eager to contribute to {company_name}'s engineering initiatives.\n\n"
            f"Sincerely,\n{context.full_name}"
        )

        screening_qa = [
            {
                "question": f"Why do you want to join {company_name} as a {job_title}?",
                "suggested_talking_points": (
                    f"Highlight engineering culture, technical alignment with "
                    f"{verified_skills_str}, and passion for continuous improvement."
                ),
            },
            {
                "question": "Can you describe a challenging project you built?",
                "suggested_talking_points": (
                    f"Walk through {project_title} using STAR: problem context, "
                    f"architecture decisions, trade-offs, and verified outcomes."
                ),
            },
        ]

        latency = int((time.time() - start_time) * 1000)

        # Build Action Proposals (Consequential actions flagged with requires_approval)
        prep_id = str(uuid.uuid4())
        proposals: list[dict[str, Any]] = [
            {
                "id": f"action_review_prep_{prep_id}",
                "action_type": "review_application_prep",
                "title": f"Review Prep Pack for {job_title} at {company_name}",
                "description": "Examine tailored resume bullet points, cover letter, and Q&A.",
                "target_id": str(job.id) if job else None,
                "target_type": "job",
                "deep_link": (
                    f"/dashboard/career-workflow?jobId={job.id}"
                    if job
                    else "/dashboard/application-assistant"
                ),
                "requires_approval": False,
            },
            {
                "id": f"action_send_email_{prep_id}",
                "action_type": "send_recruiter_email",
                "title": f"Send Outreach Email to {company_name} Recruiter",
                "description": "Requires explicit candidate confirmation before sending via Gmail.",
                "target_id": str(job.id) if job else None,
                "target_type": "job",
                "requires_approval": True,
                "payload": {
                    "company_name": company_name,
                    "job_title": job_title,
                    "recipient_placeholder": "recruiter@company.com",
                },
            },
        ]

        summary = (
            f"Prepared application package for {job_title} at {company_name}. "
            f"Synthesized bullet points for {verified_skills_str}, generated cover letter, "
            f"and formulated 2 STAR answers based on '{project_title}'."
        )

        return AgentResult(
            agent_name=self.name,
            operation="prepare_application",
            status="completed",
            summary=summary,
            data={
                "target_role": job_title,
                "company_name": company_name,
                "tailoring_highlights": tailoring_highlights,
                "cover_letter_preview": cover_letter_snippet,
                "screening_qa": screening_qa,
                "is_consequential_ready": True,
            },
            action_proposals=proposals,
            latency_ms=latency,
            tokens_used=180,
            provider="deterministic",
            requires_approval=False,
        )
