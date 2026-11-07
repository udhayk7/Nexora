"""Candidate-to-company fit evaluation grounded in resume facts and company technologies."""

import uuid
from typing import Any


def evaluate_company_fit(
    company_id: uuid.UUID,
    company_name: str,
    company_technologies: list[dict[str, Any]],
    candidate_skills: list[str],
    candidate_target_roles: list[str],
    company_jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate grounded fit assessment between candidate credentials and company intelligence."""
    # Normalize candidate skills
    candidate_skill_set = {s.strip().lower() for s in candidate_skills if s and s.strip()}

    matching_skills: list[str] = []
    gap_skills: list[str] = []

    for tech in company_technologies:
        tname = tech["name"]
        strength = tech.get("evidence_strength", "inferred")

        if tname.lower() in candidate_skill_set:
            matching_skills.append(f"{tname} ({strength})")
        else:
            # High priority gaps are confirmed or supported technologies
            if strength in ("confirmed", "supported"):
                gap_skills.append(f"{tname} ({strength})")
            elif len(gap_skills) < 6:
                gap_skills.append(f"{tname} (inferred)")

    # Match target roles against company active jobs
    target_role_matches: list[dict[str, Any]] = []
    target_role_lowers = [r.lower() for r in candidate_target_roles if r]

    for job in company_jobs:
        jtitle = (job.get("title") or "").lower()
        jfamily = (job.get("role_family") or "").lower()
        is_match = False

        if target_role_lowers:
            for tr in target_role_lowers:
                if tr in jtitle or tr in jfamily:
                    is_match = True
                    break
        else:
            # If candidate hasn't set preferences, treat all active jobs as potential match
            is_match = True

        if is_match:
            target_role_matches.append(
                {
                    "job_id": str(job.get("id")),
                    "title": job.get("title"),
                    "seniority_level": job.get("seniority_level") or "Entry-level / Unspecified",
                    "location": job.get("location_text") or "Not specified",
                    "job_status": job.get("job_status", "active"),
                }
            )

    # Fit scoring calculation
    total_tech_evaluated = len(company_technologies)
    match_count = len(matching_skills)

    base_score = 20
    if total_tech_evaluated > 0:
        skill_ratio = match_count / total_tech_evaluated
        skill_score = int(skill_ratio * 50)
    else:
        skill_score = 15

    # Bonus for open target role matches
    role_bonus = min(30, len(target_role_matches) * 15)
    final_score = min(100, max(15, base_score + skill_score + role_bonus))

    if final_score >= 70:
        fit_level = "strong"
    elif final_score >= 45:
        fit_level = "moderate"
    else:
        fit_level = "developing"

    # Role alignment summary
    if target_role_matches:
        role_alignment_summary = (
            f"{company_name} currently has {len(target_role_matches)} open position(s) directly "
            f"aligning with your target career track and skill profile."
        )
    elif company_jobs:
        role_alignment_summary = (
            f"{company_name} has active engineering requisitions, though none strictly match your "
            f"specified target role family at this moment."
        )
    else:
        role_alignment_summary = (
            f"No active public job requisitions currently indexed for {company_name}. "
            f"Fit is assessed from verified technology stack and corporate focus."
        )

    # Recommended interview preparation topics
    prep_focus: list[str] = []
    if gap_skills:
        top_gaps = [g.split(" (")[0] for g in gap_skills[:3]]
        prep_focus.append(
            f"Review core concepts and architectural trade-offs in {', '.join(top_gaps)}."
        )
    if matching_skills:
        top_matches = [m.split(" (")[0] for m in matching_skills[:3]]
        prep_focus.append(
            f"Prepare in-depth project walk-throughs demonstrating practical experience with "
            f"{', '.join(top_matches)}."
        )
    prep_focus.append(
        f"Familiarize yourself with {company_name}'s core products, industry sector, "
        f"and engineering workflow."
    )

    # Concrete evidence
    fit_evidence: list[str] = []
    if matching_skills:
        fit_evidence.append(
            f"Candidate resume demonstrates {len(matching_skills)} "
            f"overlapping technical competencies."
        )
    if target_role_matches:
        fit_evidence.append(
            f"Identified {len(target_role_matches)} matching open opportunity requisition(s)."
        )
    if gap_skills:
        fit_evidence.append(
            f"Flagged {len(gap_skills)} technology areas for revision prior to interviews."
        )

    return {
        "company_id": str(company_id),
        "company_name": company_name,
        "fit_score": final_score,
        "fit_level": fit_level,
        "matching_skills": matching_skills,
        "missing_or_gap_skills": gap_skills,
        "role_alignment_summary": role_alignment_summary,
        "target_role_matches": target_role_matches,
        "recommended_interview_focus": prep_focus,
        "fit_evidence": fit_evidence,
    }
