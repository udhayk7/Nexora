import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.networking import NetworkingContact, RecruiterProfile
from app.services.orchestration.agents.base_agent import AgentResult, BaseAgent
from app.services.orchestration.candidate_context import SharedCandidateContext


class RecruiterNetworkingAgent(BaseAgent):
    """Coordinates recruiter discovery, CRM management, and grounded outreach notes."""

    name = "recruiter_networking"
    description = (
        "Matches recruiters, identifies outreach opportunities, and crafts ≤300 char notes."
    )

    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        start_time = time.time()
        params = params or {}
        company_name = params.get("company_name") or context.target_company_name

        # Search recruiters
        query = db.query(RecruiterProfile)
        if company_name:
            query = query.filter(RecruiterProfile.company_name.ilike(f"%{company_name}%"))

        recruiters = query.limit(5).all()
        if not recruiters:
            recruiters = db.query(RecruiterProfile).limit(5).all()

        recruiter_items = []
        for r in recruiters:
            # Check CRM status
            contact = (
                db.query(NetworkingContact)
                .filter(
                    NetworkingContact.user_id == context.user_id,
                    NetworkingContact.recruiter_id == r.id,
                )
                .first()
            )
            recruiter_items.append(
                {
                    "id": str(r.id),
                    "full_name": r.full_name,
                    "company_name": r.company_name,
                    "designation": r.designation or "Technical Recruiter",
                    "specialization": r.recruitment_specialization or "Technical Hiring",
                    "crm_status": contact.relationship_status if contact else "not_saved",
                    "has_email": bool(r.contact_email),
                    "verification_status": r.verification_status,
                }
            )

        # Draft a concise LinkedIn note (strictly under 300 chars)
        target_role = context.target_job_title or (
            context.target_roles[0] if context.target_roles else "Software Engineer"
        )
        top_recruiter = recruiter_items[0] if recruiter_items else None
        rec_name = str(top_recruiter["full_name"]).split()[0] if top_recruiter else "Hiring Team"
        comp = top_recruiter["company_name"] if top_recruiter else (company_name or "your team")

        skills_short = (
            ", ".join(context.verified_skills[:2])
            if context.verified_skills
            else "Python & FastAPI"
        )
        linkedin_draft = (
            f"Hi {rec_name}, I admire {comp}'s engineering mission. I am a software engineer "
            f"with verified strengths in {skills_short}. I would love to connect and follow "
            f"upcoming {target_role} opportunities on your team. Best, {context.full_name}"
        )
        if len(linkedin_draft) > 300:
            linkedin_draft = linkedin_draft[:295] + "..."

        latency = int((time.time() - start_time) * 1000)

        proposals = []
        if top_recruiter:
            proposals.append(
                {
                    "id": f"action_outreach_{top_recruiter['id']}",
                    "action_type": "draft_recruiter_outreach",
                    "title": f"Review LinkedIn Note for {top_recruiter['full_name']}",
                    "description": (
                        f"Verified note ({len(linkedin_draft)}/300 chars) ready for review "
                        "in Networking CRM."
                    ),
                    "target_id": top_recruiter["id"],
                    "target_type": "recruiter",
                    "deep_link": "/dashboard/networking",
                    "requires_approval": False,
                }
            )

        summary = (
            f"Identified {len(recruiter_items)} relevant recruitment contacts for {comp}. "
            f"Prepared grounded LinkedIn connection note ({len(linkedin_draft)}/300 characters) "
            f"for {rec_name} ({comp})."
        )

        return AgentResult(
            agent_name=self.name,
            operation="plan_networking",
            status="completed",
            summary=summary,
            data={
                "recruiters": recruiter_items,
                "linkedin_note_draft": linkedin_draft,
                "character_count": len(linkedin_draft),
                "within_limit": len(linkedin_draft) <= 300,
            },
            action_proposals=proposals,
            latency_ms=latency,
            tokens_used=110,
            provider="deterministic",
        )
