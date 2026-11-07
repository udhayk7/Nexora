import time
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.orchestration.agents.base_agent import AgentResult, BaseAgent
from app.services.orchestration.candidate_context import SharedCandidateContext


class JobDiscoveryAgent(BaseAgent):
    """Coordinates job source discovery and prioritizes verified entry/fresher roles."""

    name = "job_discovery"
    description = (
        "Searches verified job opportunities, prioritizing entry-level and matching roles."
    )

    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        start_time = time.time()
        params = params or {}
        limit = params.get("limit", 6)
        query_role = params.get("role_family") or (
            context.target_roles[0] if context.target_roles else None
        )

        query = db.query(Job).filter(Job.job_status == "active")

        # Filter by role keywords if specified
        if query_role:
            role_kw = query_role.split()[0].lower()
            query = query.filter(
                or_(
                    Job.title.ilike(f"%{role_kw}%"),
                    Job.role_family.ilike(f"%{role_kw}%"),
                    Job.description.ilike(f"%{role_kw}%"),
                )
            )

        # Order prioritizing entry level
        jobs = (
            query.order_by(
                (Job.seniority_level == "entry").desc(),
                Job.created_at.desc(),
            )
            .limit(limit)
            .all()
        )

        job_items = []
        for j in jobs:
            is_entry = (
                (j.seniority_level == "entry")
                or ("junior" in j.title.lower())
                or ("entry" in j.title.lower())
            )
            job_items.append(
                {
                    "id": str(j.id),
                    "title": j.title,
                    "company_name": j.company.name if j.company else "Unknown Company",
                    "location": j.location_text or "Remote / Flexible",
                    "work_arrangement": j.work_arrangement or "hybrid",
                    "is_entry_level": bool(is_entry),
                    "required_skills": j.skills_tags or [],
                    "job_url": j.job_url,
                    "verification_status": j.verification_status,
                }
            )

        latency = int((time.time() - start_time) * 1000)

        proposals = []
        if job_items:
            best_job = job_items[0]
            proposals.append(
                {
                    "id": f"action_prep_{best_job['id']}",
                    "action_type": "prepare_application",
                    "title": f"Prepare Application for {best_job['title']}",
                    "description": (
                        f"Tailor resume, draft cover letter and prepare Q&A for "
                        f"{best_job['company_name']}."
                    ),
                    "target_id": best_job["id"],
                    "target_type": "job",
                    "deep_link": f"/dashboard/career-workflow?jobId={best_job['id']}",
                    "requires_approval": False,
                }
            )

        entry_count = sum(1 for j in job_items if j["is_entry_level"])
        summary = (
            f"Discovered {len(job_items)} verified opportunities matching target criteria "
            f"({query_role or 'all roles'}). Prioritized {entry_count} entry/fresher listings."
        )

        return AgentResult(
            agent_name=self.name,
            operation="discover_jobs",
            status="completed",
            summary=summary,
            data={
                "discovered_jobs": job_items,
                "total_found": len(job_items),
                "role_queried": query_role,
            },
            action_proposals=proposals,
            latency_ms=latency,
            tokens_used=80,
            provider="deterministic",
        )
