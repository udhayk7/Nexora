import logging

from sqlalchemy.orm import Session

from app.models.match import UserMatchingPreference
from app.models.networking import RecruiterProfile
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.networking import RecruiterMatchExplanation, RecruiterMatchItem

logger = logging.getLogger("nexora.services.recruiter_matching")


class RecruiterMatchingEngine:
    """Intelligent recruiter matching and explainability engine.

    Scores recruiters against candidate's verified skills, target job roles,
    preferred companies, and active opportunities using deterministic scoring
    combined with contextual explainability.
    """

    @classmethod
    def compute_match(
        cls,
        db: Session,
        user: User,
        recruiter: RecruiterProfile,
        user_skills: set[str],
        target_roles: list[str],
        preferred_companies: set[str],
    ) -> RecruiterMatchExplanation:
        """Deterministic multi-dimensional matching calculation."""
        reasons: list[str] = []
        score = 40.0  # Base score for any active tech recruiter

        # 1. Company Preference Alignment (weight: 25)
        company_relevance = "general"
        if recruiter.company_name.lower() in preferred_companies:
            score += 25.0
            company_relevance = "preferred_target_company"
            reasons.append(
                f"Recruiter at {recruiter.company_name}, one of your preferred target companies."
            )
        elif recruiter.company and recruiter.company.category in ("product", "mnc", "gcc"):
            score += 15.0
            company_relevance = "premier_tier"
            reasons.append(f"Represents a top-tier {recruiter.company.category.upper()} employer.")

        # 2. Role Alignment (weight: 25)
        spec_text = (
            f"{recruiter.recruitment_specialization or ''} {recruiter.designation} "
            f"{' '.join(recruiter.relevant_departments)}"
        ).lower()

        role_aligned = False
        for role in target_roles:
            role_terms = role.lower().split()
            if any(term in spec_text for term in role_terms if len(term) > 3):
                role_aligned = True
                reasons.append(
                    f"Recruits specifically for {role} and related technical disciplines."
                )
                score += 25.0
                break

        if not role_aligned and any(
            dept.lower() in ("engineering", "technology", "software")
            for dept in recruiter.relevant_departments
        ):
            score += 15.0
            reasons.append("Covers software engineering and core technical hiring.")

        # 3. Candidate Skill Overlap (weight: 20)
        overlapping_skills: list[str] = []
        for skill in user_skills:
            if len(skill) > 2 and skill in spec_text:
                overlapping_skills.append(skill.title())
                if len(overlapping_skills) >= 4:
                    break

        if overlapping_skills:
            score += min(20.0, len(overlapping_skills) * 5.0)
            reasons.append(
                f"Specializes in your demonstrated skills: {', '.join(overlapping_skills)}."
            )

        # 4. Active Associated Opportunities (weight: 15)
        active_job_count = len(recruiter.associated_job_ids)
        if active_job_count > 0:
            score += 15.0
            reasons.append(
                f"Directly associated with {active_job_count} active tech opportunity listings."
            )

        # 5. Verification Bonus (weight: 5)
        if recruiter.verification_status == "verified":
            score += 5.0

        final_score = min(100.0, round(score, 1))

        # Primary summary reason
        if not reasons:
            reasons.append(f"Recruitment contact for technology roles at {recruiter.company_name}.")

        return RecruiterMatchExplanation(
            match_score=final_score,
            match_reasons=reasons,
            role_alignment="high" if role_aligned else "moderate",
            skill_overlap=overlapping_skills,
            company_relevance=company_relevance,
            active_opportunities_count=active_job_count,
            is_recommended=final_score >= 50.0,
        )

    @classmethod
    def match_and_rank_recruiters(
        cls,
        db: Session,
        user: User,
        recruiters: list[RecruiterProfile],
    ) -> list[RecruiterMatchItem]:
        """Rank recruiters against candidate profile, extracting verified skills & preferences."""
        # 1. Fetch user matching preferences
        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        target_roles = (
            (pref.target_role_families or ["Software Engineer"]) if pref else ["Software Engineer"]
        )
        preferred_companies: set[str] = set()
        if pref and pref.metadata_json:
            pref_list = pref.metadata_json.get("target_companies", [])
            preferred_companies = {c.lower().strip() for c in pref_list if isinstance(c, str)}

        # 2. Fetch candidate verified skills from latest parsed resume
        user_skills: set[str] = set()
        latest_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user.id)
            .order_by(Resume.created_at.desc())
            .first()
        )
        if latest_resume and latest_resume.current_version_id:
            ver = (
                db.query(ResumeVersion)
                .filter(ResumeVersion.id == latest_resume.current_version_id)
                .first()
            )
            if ver and ver.parsed_content:
                user_skills = {
                    s.lower().strip()
                    for s in ver.parsed_content.get("skills", [])
                    if isinstance(s, str) and s.strip()
                }

        # 3. Compute matches
        results: list[RecruiterMatchItem] = []
        for rec in recruiters:
            explanation = cls.compute_match(
                db=db,
                user=user,
                recruiter=rec,
                user_skills=user_skills,
                target_roles=target_roles,
                preferred_companies=preferred_companies,
            )
            results.append(
                RecruiterMatchItem(
                    recruiter=rec,  # type: ignore[arg-type]
                    match=explanation,
                )
            )

        # Sort descending by match_score
        results.sort(key=lambda r: r.match.match_score, reverse=True)
        return results
