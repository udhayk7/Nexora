import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.orchestration.agents.base_agent import AgentResult, BaseAgent
from app.services.orchestration.candidate_context import SharedCandidateContext


class JobMatchingAgent(BaseAgent):
    """Evaluates candidate-job compatibility, explains matching dimensions, and identifies gaps."""

    name = "job_matching"
    description = (
        "Computes deterministic match scores, highlights overlapping skills and eligibility gaps."
    )

    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        start_time = time.time()
        params = params or {}
        candidate_skills = {s.lower() for s in context.verified_skills}

        # Get jobs to evaluate
        jobs_input = params.get("jobs")
        if not jobs_input:
            # Query active jobs
            jobs = db.query(Job).filter(Job.job_status == "active").limit(10).all()
        else:
            job_ids = [j["id"] for j in jobs_input if isinstance(j, dict) and "id" in j]
            jobs = db.query(Job).filter(Job.id.in_(job_ids)).all() if job_ids else []

        ranked_matches: list[dict[str, Any]] = []
        for j in jobs:
            required = [r.lower() for r in (j.skills_tags or [])]
            if required:
                matched_skills = [s for s in required if s in candidate_skills]
                missing_skills = [s for s in required if s not in candidate_skills]
                skill_ratio = len(matched_skills) / len(required)
            else:
                matched_skills = list(context.verified_skills[:3])
                missing_skills = []
                skill_ratio = 0.75

            # Role match
            target_kw = (context.target_roles[0] if context.target_roles else "software").lower()
            role_match = (
                0.9
                if target_kw in j.title.lower() or target_kw in (j.role_family or "").lower()
                else 0.7
            )

            is_entry = (j.seniority_level == "entry") or ("junior" in j.title.lower())
            overall_score = round(
                (skill_ratio * 55.0 + role_match * 35.0 + (10.0 if is_entry else 5.0)), 1
            )
            overall_score = min(max(overall_score, 45.0), 98.0)

            ranked_matches.append(
                {
                    "job_id": str(j.id),
                    "title": j.title,
                    "company_name": j.company.name if j.company else "Tech Company",
                    "match_score": overall_score,
                    "matched_skills": matched_skills[:5],
                    "missing_skills": missing_skills[:4],
                    "why_matched": f"Overlap ({len(matched_skills)} skills) and fit for {j.title}.",
                    "is_strong_match": overall_score >= 75.0,
                }
            )

        ranked_matches.sort(key=lambda x: float(x.get("match_score", 0.0)), reverse=True)
        top_matches = ranked_matches[:5]

        latency = int((time.time() - start_time) * 1000)

        proposals = []
        if top_matches:
            best = top_matches[0]
            matched_len = (
                len(best["matched_skills"]) if isinstance(best["matched_skills"], list) else 0
            )
            proposals.append(
                {
                    "id": f"action_view_match_{best['job_id']}",
                    "action_type": "view_match",
                    "title": f"Review Match: {best['title']} ({best['match_score']}%)",
                    "description": f"Verified match with {matched_len} skills.",
                    "target_id": best["job_id"],
                    "target_type": "job",
                    "deep_link": "/dashboard/matches",
                    "requires_approval": False,
                }
            )

        strong_count = sum(1 for m in ranked_matches if m["is_strong_match"])
        top_str = (
            f"Top fit: {top_matches[0]['title']} ({top_matches[0]['match_score']}%)."
            if top_matches
            else "No active jobs available."
        )
        summary = (
            f"Evaluated compatibility for {len(ranked_matches)} jobs against verified skills. "
            f"Found {strong_count} strong matches (≥75%). {top_str}"
        )

        return AgentResult(
            agent_name=self.name,
            operation="rank_matches",
            status="completed",
            summary=summary,
            data={
                "matches": top_matches,
                "evaluated_count": len(ranked_matches),
                "strong_matches_count": sum(1 for m in ranked_matches if m["is_strong_match"]),
            },
            action_proposals=proposals,
            latency_ms=latency,
            tokens_used=100,
            provider="deterministic",
        )
