import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.analysis import ResumeAnalysis
from app.models.resume import Resume
from app.services.orchestration.agents.base_agent import AgentResult, BaseAgent
from app.services.orchestration.candidate_context import SharedCandidateContext


class ResumeIntelligenceAgent(BaseAgent):
    """Understands candidate resumes, extracts verified facts, identifies strengths and gaps."""

    name = "resume_intelligence"
    description = "Analyzes candidate resume facts, extracts verified skills and role suitability."

    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        start_time = time.time()
        params = params or {}

        # 1. Fetch latest analysis if available
        resume = (
            db.query(Resume)
            .filter(Resume.user_id == context.user_id)
            .order_by(Resume.created_at.desc())
            .first()
        )

        analysis = None
        if resume and resume.current_version_id:
            analysis = (
                db.query(ResumeAnalysis)
                .filter(ResumeAnalysis.version_id == resume.current_version_id)
                .order_by(ResumeAnalysis.created_at.desc())
                .first()
            )

        # 2. Extract verified skills and strengths
        verified_skills = context.verified_skills
        target_roles = context.target_roles or ["Software Engineer"]

        strengths = []
        gaps = []
        if verified_skills:
            strengths.append(f"Demonstrated core competence in {', '.join(verified_skills[:4])}")
            if len(context.verified_projects) >= 1:
                strengths.append(
                    f"Evidence-backed projects: {len(context.verified_projects)} documented."
                )
        else:
            gaps.append("Resume contains limited explicit technical skill keywords")

        analysis_res = analysis.result if analysis and isinstance(analysis.result, dict) else {}
        extra_strengths = analysis_res.get("strengths")
        if isinstance(extra_strengths, list):
            strengths.extend([str(s) for s in extra_strengths[:2]])
        extra_gaps = analysis_res.get("gaps") or analysis_res.get("improvements")
        if isinstance(extra_gaps, list):
            gaps.extend([str(g) for g in extra_gaps[:2]])

        # Recommended roles
        rec_roles = list(target_roles)
        if ("Python" in verified_skills or "FastAPI" in verified_skills) and (
            "Backend Software Engineer" not in rec_roles
        ):
            rec_roles.append("Backend Software Engineer")
        if ("React" in verified_skills or "TypeScript" in verified_skills) and (
            "Frontend Engineer" not in rec_roles
        ):
            rec_roles.append("Frontend Engineer")

        latency = int((time.time() - start_time) * 1000)

        proposals = []
        if gaps:
            proposals.append(
                {
                    "id": "action_tailor_resume",
                    "action_type": "tailor_resume",
                    "title": "Tailor Resume for Target Role",
                    "description": (
                        f"Align resume sections and highlight evidence for {rec_roles[0]}."
                        if rec_roles
                        else "Align resume sections to your target role."
                    ),
                    "deep_link": "/dashboard/resumes/tailor",
                    "requires_approval": False,
                }
            )

        v_count = len(verified_skills)
        p_count = len(context.verified_projects)
        summary = (
            f"Evaluated candidate profile for {context.full_name}. Identified {v_count} verified "
            f"skills and {p_count} projects. Target roles: {', '.join(rec_roles[:3])}."
        )

        return AgentResult(
            agent_name=self.name,
            operation="analyze_profile",
            status="completed",
            summary=summary,
            data={
                "verified_skills": verified_skills,
                "strengths": strengths,
                "gaps": gaps,
                "recommended_roles": rec_roles[:4],
                "verified_projects_count": len(context.verified_projects),
                "has_current_resume": bool(context.resume_version_id),
            },
            action_proposals=proposals,
            latency_ms=latency,
            tokens_used=120,
            provider="deterministic",
        )
