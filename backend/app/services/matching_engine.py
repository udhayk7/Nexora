import re
from typing import Any, Optional

from app.models.job import Job
from app.models.match import UserMatchingPreference
from app.schemas.analysis import ResumeAnalysisResult
from app.schemas.match import (
    GapSignal,
    PositiveSignal,
    SalaryStatusType,
    ScoreBreakdown,
    SignalEvidenceRef,
)

ENGINE_VERSION = "v1.0-deterministic"

# Canonical tech skill aliases for robust normalized comparison
_SKILL_SYNONYMS: dict[str, str] = {
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "python3": "python",
    "py": "python",
    "postgres": "postgresql",
    "psql": "postgresql",
    "golang": "go",
    "k8s": "kubernetes",
    "aws": "amazon web services",
    "gcp": "google cloud",
    "ts": "typescript",
    "js": "javascript",
    "cicd": "ci/cd",
    "ci-cd": "ci/cd",
    "restful": "rest",
    "rest api": "rest",
    "graphql": "graphql",
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "tailwind": "tailwindcss",
    "nextjs": "next.js",
    "next.js": "next.js",
    "docker": "docker",
}


def normalize_skill_name(term: str) -> str:
    """Normalize a skill token for deterministic matching."""
    cleaned = re.sub(r"[^\w\s\.\-\/\#\+]", "", term.lower()).strip()
    return _SKILL_SYNONYMS.get(cleaned, cleaned)


def normalize_salary_annual(amount: float, period: Optional[str]) -> float:
    """Normalize salary figures to an annual baseline for comparison."""
    if not period or period.lower() == "annual":
        return amount
    if period.lower() == "monthly":
        return amount * 12.0
    if period.lower() == "hourly":
        return amount * 2080.0  # 40 hrs * 52 weeks
    if period.lower() == "weekly":
        return amount * 52.0
    return amount


class MatchingEngine:
    """Deterministic, explainable career matching and ranking engine.

    Calculates grounded alignment scores between a candidate's verified resume analysis
    and early-career job requisitions without relying on non-deterministic LLM calls.
    """

    @classmethod
    def evaluate_match(
        cls,
        job: Job,
        resume_analysis: ResumeAnalysisResult,
        preferences: Optional[UserMatchingPreference] = None,
    ) -> tuple[float, ScoreBreakdown, list[PositiveSignal], list[GapSignal]]:
        """Evaluate a job listing against candidate profile and preferences.

        Returns:
            (final_score, breakdown, positive_signals, gap_signals)
        """
        positive_signals: list[PositiveSignal] = []
        gap_signals: list[GapSignal] = []

        # 1. Evaluate Skills Alignment (Base Weight: 35%)
        skills_score, skill_positives, skill_gaps = cls._evaluate_skills(
            job=job,
            analysis=resume_analysis,
            preferences=preferences,
        )
        positive_signals.extend(skill_positives)
        gap_signals.extend(skill_gaps)

        # 2. Evaluate Role Family & Domain Alignment (Base Weight: 25%)
        role_score, role_positives, role_gaps = cls._evaluate_role(
            job=job,
            analysis=resume_analysis,
            preferences=preferences,
        )
        positive_signals.extend(role_positives)
        gap_signals.extend(role_gaps)

        # 3. Evaluate Experience & Seniority Compatibility (Base Weight: 15%)
        exp_score, exp_positives, exp_gaps = cls._evaluate_experience(
            job=job,
            analysis=resume_analysis,
            preferences=preferences,
        )
        positive_signals.extend(exp_positives)
        gap_signals.extend(exp_gaps)

        # 4. Evaluate Location & Work Arrangement (Base Weight: 15%)
        loc_score, loc_positives, loc_gaps = cls._evaluate_location(
            job=job,
            preferences=preferences,
        )
        positive_signals.extend(loc_positives)
        gap_signals.extend(loc_gaps)

        # 5. Evaluate Compensation (Base Weight: 10% - reallocated if undisclosed)
        sal_score, sal_status, sal_positives, sal_gaps = cls._evaluate_compensation(
            job=job,
            preferences=preferences,
        )
        positive_signals.extend(sal_positives)
        gap_signals.extend(sal_gaps)

        # 6. Apply Weights & Dynamic Reallocation for Undisclosed Compensation
        has_salary_evaluation = sal_score is not None
        if has_salary_evaluation:
            weights = {
                "skills": 0.35,
                "role": 0.25,
                "experience": 0.15,
                "location": 0.15,
                "salary": 0.10,
            }
            raw_weighted_score = (
                skills_score * weights["skills"]
                + role_score * weights["role"]
                + exp_score * weights["experience"]
                + loc_score * weights["location"]
                + sal_score * weights["salary"]  # type: ignore[operator]
            )
        else:
            # Reallocate the 10% salary weight proportionally across other 4 dimensions
            weights = {
                "skills": round(0.35 / 0.90, 4),
                "role": round(0.25 / 0.90, 4),
                "experience": round(0.15 / 0.90, 4),
                "location": round(0.15 / 0.90, 4),
                "salary": 0.0,
            }
            raw_weighted_score = (
                skills_score * weights["skills"]
                + role_score * weights["role"]
                + exp_score * weights["experience"]
                + loc_score * weights["location"]
            )

        # 7. Trust Signals & Verification/Freshness Adjustment
        trust_adjustment, trust_details = cls._calculate_trust_adjustment(job)

        # 8. Negative Filter / Exclusion Penalties
        exclusion_deduction, exclusion_gaps = cls._evaluate_exclusions(job, preferences)
        gap_signals.extend(exclusion_gaps)

        final_score = max(
            0.0,
            min(100.0, round(raw_weighted_score + trust_adjustment - exclusion_deduction, 1)),
        )

        breakdown = ScoreBreakdown(
            skills_score=round(skills_score, 1),
            role_score=round(role_score, 1),
            experience_score=round(exp_score, 1),
            location_score=round(loc_score, 1),
            salary_score=round(sal_score, 1) if sal_score is not None else None,
            salary_status=sal_status,
            trust_adjustment=round(trust_adjustment, 1),
            trust_signals=trust_details,
            weights_applied=weights,
            raw_weighted_score=round(raw_weighted_score, 1),
            final_score=final_score,
            disclaimer=(
                "Match scores represent deterministic alignment between your parsed resume and "
                "job listing criteria. They do not predict hiring outcomes or guarantee interviews."
            ),
        )

        return final_score, breakdown, positive_signals, gap_signals

    @classmethod
    def _evaluate_skills(
        cls,
        job: Job,
        analysis: ResumeAnalysisResult,
        preferences: Optional[UserMatchingPreference],
    ) -> tuple[float, list[PositiveSignal], list[GapSignal]]:
        """Compute skills alignment grounded in evidenced resume experience."""
        positives: list[PositiveSignal] = []
        gaps: list[GapSignal] = []

        # Candidate skills
        supported_set: set[str] = set()
        for s in analysis.skills.supported_skills or []:
            supported_set.add(normalize_skill_name(s))

        unevidenced_set: set[str] = set()
        for s in analysis.skills.unevidenced_skills or []:
            unevidenced_set.add(normalize_skill_name(s))

        # Build evidence lookup from resume analysis
        evidence_map: dict[str, SignalEvidenceRef] = {}
        for ev in analysis.skills.evidence or []:
            for term in supported_set:
                if term in ev.excerpt.lower() and term not in evidence_map:
                    evidence_map[term] = SignalEvidenceRef(
                        section=ev.section, excerpt=ev.excerpt[:180]
                    )

        # Fallback to general resume strengths if specific term excerpt isn't found
        default_evidence: Optional[SignalEvidenceRef] = None
        if analysis.strengths and len(analysis.strengths) > 0:
            first_strength = analysis.strengths[0]
            default_evidence = SignalEvidenceRef(
                section=first_strength.evidence.section,
                excerpt=first_strength.evidence.excerpt[:180],
            )

        # Job requirements
        raw_job_skills = list(job.skills_tags or [])
        norm_job_skills = [normalize_skill_name(st) for st in raw_job_skills if st.strip()]

        if not norm_job_skills:
            # Fallback: scan description for candidate skills
            desc_lower = (job.description or "").lower()
            detected_matches = [s for s in supported_set if s in desc_lower]
            if detected_matches:
                positives.append(
                    PositiveSignal(
                        dimension="skills",
                        title=f"Core skills matched in job description ({len(detected_matches)})",
                        description=(
                            "Evidenced skills found in job description: "
                            f"{', '.join(sorted(detected_matches)[:4])}"
                        ),
                        evidence=evidence_map.get(detected_matches[0], default_evidence),
                    )
                )
                return 75.0, positives, gaps
            return 50.0, positives, [
                GapSignal(
                    type="missing",
                    dimension="skills",
                    title="No explicit skill tags on job listing",
                    description="The employer did not specify structured technology requirements.",
                )
            ]

        matched_supported: list[str] = []
        matched_unevidenced: list[str] = []
        missing_skills: list[str] = []

        for term in norm_job_skills:
            if term in supported_set:
                matched_supported.append(term)
            elif term in unevidenced_set:
                matched_unevidenced.append(term)
            else:
                missing_skills.append(term)

        # Additional preference bonus
        pref_matches: list[str] = []
        if preferences and preferences.preferred_skills:
            for ps in preferences.preferred_skills:
                norm_ps = normalize_skill_name(ps)
                if norm_ps in norm_job_skills and norm_ps not in pref_matches:
                    pref_matches.append(norm_ps)

        # Calculate score: supported = 1.0, unevidenced = 0.6
        total_req = len(norm_job_skills)
        matched_value = (len(matched_supported) * 1.0) + (len(matched_unevidenced) * 0.6)
        raw_ratio = matched_value / total_req
        score = min(100.0, raw_ratio * 100.0 + (len(pref_matches) * 5.0))

        # Create Positive Signals
        if matched_supported:
            primary_term = matched_supported[0]
            positives.append(
                PositiveSignal(
                    dimension="skills",
                    title=f"Evidenced technical skills ({len(matched_supported)} matched)",
                    description=(
                        "Strong project-backed evidence found for: "
                        f"{', '.join(matched_supported[:5])}"
                    ),
                    evidence=evidence_map.get(primary_term, default_evidence),
                )
            )

        if matched_unevidenced:
            positives.append(
                PositiveSignal(
                    dimension="skills",
                    title=f"Additional listed skills ({len(matched_unevidenced)} present)",
                    description=(
                        f"Resume lists {', '.join(matched_unevidenced[:4])}, "
                        "though with less direct project evidence."
                    ),
                )
            )

        if pref_matches:
            positives.append(
                PositiveSignal(
                    dimension="skills",
                    title="Target skills matched user preferences",
                    description=(
                        f"Job requisitions include your priority skills: "
                        f"{', '.join(pref_matches[:4])}."
                    ),
                )
            )

        # Create Gap Signals
        if missing_skills:
            gaps.append(
                GapSignal(
                    type="missing",
                    dimension="skills",
                    title=f"Missing technical requirements ({len(missing_skills)} skills)",
                    description=f"Not found in parsed resume: {', '.join(missing_skills[:5])}.",
                )
            )

        return max(0.0, min(100.0, score)), positives, gaps

    @classmethod
    def _evaluate_role(
        cls,
        job: Job,
        analysis: ResumeAnalysisResult,
        preferences: Optional[UserMatchingPreference],
    ) -> tuple[float, list[PositiveSignal], list[GapSignal]]:
        """Evaluate role family alignment with user preferences and resume domains."""
        positives: list[PositiveSignal] = []
        gaps: list[GapSignal] = []

        job_family = (job.role_family or "").lower().strip()
        job_title = (job.title or "").lower().strip()

        # Check candidate's evidenced domains
        candidate_domains = [d.lower() for d in (analysis.profile.domains or [])]
        user_target_roles = [
            r.lower()
            for r in ((preferences.target_role_families or []) if preferences else [])
        ]

        score = 60.0  # baseline

        # Direct user preference match
        if user_target_roles:
            if job_family in user_target_roles or any(tr in job_title for tr in user_target_roles):
                score = 95.0
                positives.append(
                    PositiveSignal(
                        dimension="role_family",
                        title="Target Role Family Match",
                        description=(
                            "Matches your specified target role preference: "
                            f"{job.role_family or job.title}."
                        ),
                    )
                )
            else:
                score = 45.0
                gaps.append(
                    GapSignal(
                        type="mismatch",
                        dimension="role_family",
                        title="Role family outside preferred targets",
                        description=(
                            f"Listing role '{job.role_family or job.title}' does not match "
                            f"your active target role families "
                            f"({', '.join(user_target_roles[:3])})."
                        ),
                    )
                )

        # Complement with AI role suitability assessment if available
        if analysis.role_suitability:
            for rs in analysis.role_suitability:
                norm_rs_name = rs.role_name.lower()
                if (
                    norm_rs_name in job_family
                    or job_family in norm_rs_name
                    or any(w in job_title for w in norm_rs_name.split())
                ):
                    evidence_ref: Optional[SignalEvidenceRef] = None
                    if rs.evidence and len(rs.evidence) > 0:
                        evidence_ref = SignalEvidenceRef(
                            section=rs.evidence[0].section,
                            excerpt=rs.evidence[0].excerpt[:180],
                        )

                    suitability_score = float(rs.heuristic_score)
                    score = (score + suitability_score) / 2.0
                    positives.append(
                        PositiveSignal(
                            dimension="role_family",
                            title=f"Resume Profile Alignment: {rs.suitability_band}",
                            description=f"Resume exhibits strong indicators for {rs.role_name}.",
                            evidence=evidence_ref,
                        )
                    )
                    break

        # Check domain intersection
        matching_domains = [d for d in candidate_domains if d in job_title or d in job_family]
        if matching_domains and not positives:
            score = max(score, 75.0)
            positives.append(
                PositiveSignal(
                    dimension="role_family",
                    title="Domain Experience Alignment",
                    description=f"Evidenced domain experience in: {', '.join(matching_domains)}.",
                )
            )

        return max(0.0, min(100.0, score)), positives, gaps

    @classmethod
    def _evaluate_experience(
        cls,
        job: Job,
        analysis: ResumeAnalysisResult,
        preferences: Optional[UserMatchingPreference],
    ) -> tuple[float, list[PositiveSignal], list[GapSignal]]:
        """Evaluate experience tier and seniority compatibility."""
        positives: list[PositiveSignal] = []
        gaps: list[GapSignal] = []

        job_seniority = (job.seniority_level or "").lower().strip()
        candidate_level = (analysis.profile.career_level_estimate or "Entry Level").lower()
        pref_seniority = [
            s.lower()
            for s in ((preferences.seniority_preferences or []) if preferences else [])
        ]

        if not job_seniority:
            # Missing seniority info on job: neutral, do not penalize
            gaps.append(
                GapSignal(
                    type="missing",
                    dimension="experience",
                    title="Seniority level not specified by employer",
                    description=(
                        "Listing does not specify required years of experience; "
                        "treated as flexible."
                    ),
                )
            )
            return 75.0, positives, gaps

        # Direct match with user preferred seniority
        if pref_seniority and job_seniority in pref_seniority:
            positives.append(
                PositiveSignal(
                    dimension="experience",
                    title="Desired Career Level Match",
                    description=(
                        f"Role seniority '{job_seniority.replace('_', ' ')}' "
                        "aligns with your target preference."
                    ),
                )
            )
            return 95.0, positives, gaps

        # Early career compatibility checks
        is_early_career_job = job_seniority in {"entry_level", "internship", "junior", "fresher"}
        is_early_career_candidate = any(
            t in candidate_level for t in {"entry", "junior", "intern", "student", "graduate"}
        )

        if is_early_career_job and is_early_career_candidate:
            positives.append(
                PositiveSignal(
                    dimension="experience",
                    title="Early-Career Requisition Match",
                    description=(
                        "Role is calibrated for early-career technologists and new graduates."
                    ),
                )
            )
            return 90.0, positives, gaps

        if job_seniority in {"senior", "staff", "lead", "principal"} and is_early_career_candidate:
            gaps.append(
                GapSignal(
                    type="mismatch",
                    dimension="experience",
                    title="Seniority Level Mismatch",
                    description=(
                        f"Position seeks {job_seniority.replace('_', ' ')} experience, whereas "
                        f"candidate resume reflects {analysis.profile.career_level_estimate}."
                    ),
                )
            )
            return 35.0, positives, gaps

        return 70.0, positives, gaps

    @classmethod
    def _evaluate_location(
        cls,
        job: Job,
        preferences: Optional[UserMatchingPreference],
    ) -> tuple[float, list[PositiveSignal], list[GapSignal]]:
        """Evaluate geographic location and remote/hybrid work arrangement."""
        positives: list[PositiveSignal] = []
        gaps: list[GapSignal] = []

        job_arrangement = (job.work_arrangement or "unspecified").lower()
        job_city = (job.city or "").lower()
        job_country = (job.country or "").lower()
        job_loc_text = (job.location_text or "").lower()

        pref_arrangements = [
            a.lower()
            for a in ((preferences.work_arrangement_preferences or []) if preferences else [])
        ]
        pref_locations = [
            loc.lower()
            for loc in ((preferences.preferred_locations or []) if preferences else [])
        ]

        score = 75.0  # neutral baseline

        # 1. Work Arrangement check
        if pref_arrangements:
            if job_arrangement in pref_arrangements:
                score += 15.0
                positives.append(
                    PositiveSignal(
                        dimension="location",
                        title=f"Work Arrangement Match: {job.work_arrangement.capitalize()}",
                        description=(
                            f"The {job.work_arrangement} work arrangement "
                            "matches your selected preference."
                        ),
                    )
                )
            elif job_arrangement == "unspecified":
                gaps.append(
                    GapSignal(
                        type="missing",
                        dimension="location",
                        title="Work arrangement not specified",
                        description=(
                            "Employer listing does not explicitly state remote/hybrid/onsite terms."
                        ),
                    )
                )
            else:
                score -= 30.0
                gaps.append(
                    GapSignal(
                        type="mismatch",
                        dimension="location",
                        title="Work arrangement mismatch",
                        description=(
                            f"Listing requires {job.work_arrangement}, which does not match "
                            f"your preference for {', '.join(pref_arrangements)}."
                        ),
                    )
                )

        # 2. Geographic Location check
        if pref_locations:
            matched_loc = any(
                pl in job_city or pl in job_country or pl in job_loc_text for pl in pref_locations
            )
            if matched_loc:
                loc_disp = job.location_text or job.city or job.country or ""
                score += 10.0
                positives.append(
                    PositiveSignal(
                        dimension="location",
                        title="Preferred Location Match",
                        description=f"Location aligns with your preference: {loc_disp}.",
                    )
                )
            elif job_arrangement == "remote":
                score += 10.0
                positives.append(
                    PositiveSignal(
                        dimension="location",
                        title="Remote Location Flexibility",
                        description=(
                            "Role is remote-eligible, accommodating candidates across regions."
                        ),
                    )
                )
            elif not (job.location_text or job.city or job.country):
                gaps.append(
                    GapSignal(
                        type="missing",
                        dimension="location",
                        title="Location details not specified",
                        description="No specific city or region was provided by the employer.",
                    )
                )
            else:
                score -= 20.0
                loc_disp = job.location_text or job.city or ""
                gaps.append(
                    GapSignal(
                        type="mismatch",
                        dimension="location",
                        title="Location does not match preferred cities",
                        description=f"Role is located in {loc_disp}, outside preferred targets.",
                    )
                )

        return max(0.0, min(100.0, score)), positives, gaps

    @classmethod
    def _evaluate_compensation(
        cls,
        job: Job,
        preferences: Optional[UserMatchingPreference],
    ) -> tuple[
        Optional[float],
        SalaryStatusType,
        list[PositiveSignal],
        list[GapSignal],
    ]:
        """Evaluate salary only when explicitly available; never penalize undisclosed salary."""
        positives: list[PositiveSignal] = []
        gaps: list[GapSignal] = []

        has_job_salary = job.salary_min is not None or job.salary_max is not None
        has_pref_salary = preferences and preferences.min_salary is not None

        if not has_job_salary:
            gaps.append(
                GapSignal(
                    type="missing",
                    dimension="compensation",
                    title="Compensation undisclosed in job listing",
                    description=(
                        "Employer did not publish salary figures. Listing is evaluated neutrally "
                        "without any score penalty."
                    ),
                )
            )
            return None, "undisclosed", positives, gaps

        if not has_pref_salary:
            # Job published salary, but candidate set no minimum filter
            s_dash = ' - ' if job.salary_min and job.salary_max else ''
            positives.append(
                PositiveSignal(
                    dimension="compensation",
                    title="Transparent Salary Disclosed",
                    description=(
                        f"Listing provides explicit compensation: {job.salary_currency or ''} "
                        f"{job.salary_min or ''}{s_dash}{job.salary_max or ''} "
                        f"/{job.salary_period or 'yr'}."
                    ),
                )
            )
            return None, "no_preference", positives, gaps

        # Both job salary and user minimum preference are explicit
        assert preferences is not None
        assert preferences.min_salary is not None

        user_annual_min = normalize_salary_annual(
            preferences.min_salary, preferences.salary_period
        )
        job_max = job.salary_max or job.salary_min or 0.0
        job_annual_max = normalize_salary_annual(job_max, job.salary_period)

        if job_annual_max >= user_annual_min:
            positives.append(
                PositiveSignal(
                    dimension="compensation",
                    title="Compensation Meets Desired Minimum",
                    description=(
                        f"Published compensation meets or exceeds your baseline preference of "
                        f"{preferences.salary_currency or ''} {preferences.min_salary:,.0f}."
                    ),
                )
            )
            return 100.0, "matched", positives, gaps
        else:
            ratio = (job_annual_max / user_annual_min) if user_annual_min > 0 else 0.5
            calc_score = max(20.0, min(85.0, ratio * 100.0))
            gaps.append(
                GapSignal(
                    type="mismatch",
                    dimension="compensation",
                    title="Offered salary is below desired minimum",
                    description=(
                        f"Max salary of {job.salary_currency or ''} {job_max:,.0f} "
                        f"is below your desired minimum of {preferences.min_salary:,.0f}."
                    ),
                )
            )
            return calc_score, "below_minimum", positives, gaps

    @classmethod
    def _calculate_trust_adjustment(cls, job: Job) -> tuple[float, dict[str, Any]]:
        """Calculate documented trust score modifier for verification and freshness."""
        adj = 0.0
        details: dict[str, Any] = {
            "freshness": job.freshness if hasattr(job, "freshness") else "unknown",
            "verification_status": job.verification_status,
        }

        # Verification status modifier
        if job.verification_status == "verified":
            adj += 3.0
            details["verification_modifier"] = "+3 (Verified official listing)"
        elif job.verification_status == "corroborated":
            adj += 2.0
            details["verification_modifier"] = "+2 (Multiple corroborating sources)"
        elif job.verification_status == "suspicious":
            adj -= 30.0
            details["verification_modifier"] = "-30 (Flagged suspicious/scam)"
        elif job.verification_status == "expired" or job.job_status == "closed":
            adj -= 25.0
            details["verification_modifier"] = "-25 (Listing closed or expired)"
        else:
            details["verification_modifier"] = "0 (Unverified / awaiting community review)"

        # Freshness modifier
        freshness_tier = getattr(job, "freshness", "unknown")
        if freshness_tier == "recent":
            adj += 2.0
            details["freshness_modifier"] = "+2 (Checked within last 7 days)"
        elif freshness_tier == "stale":
            adj -= 3.0
            details["freshness_modifier"] = "-3 (Unchecked for over 14 days)"
        else:
            details["freshness_modifier"] = "0 (Freshness due or unknown)"

        return adj, details

    @classmethod
    def _evaluate_exclusions(
        cls,
        job: Job,
        preferences: Optional[UserMatchingPreference],
    ) -> tuple[float, list[GapSignal]]:
        """Check for user-specified negative filters (excluded roles, terms, industries)."""
        if not preferences:
            return 0.0, []

        penalty = 0.0
        gaps: list[GapSignal] = []

        title_lower = (job.title or "").lower()
        desc_lower = (job.description or "").lower()

        # 1. Excluded roles
        for er in preferences.excluded_roles or []:
            if er.lower().strip() and er.lower().strip() in title_lower:
                penalty += 25.0
                gaps.append(
                    GapSignal(
                        type="mismatch",
                        dimension="role_family",
                        title=f"Contains excluded role term: '{er}'",
                        description=f"Role title '{job.title}' contains an excluded term.",
                    )
                )
                break

        # 2. Excluded terms
        for et in preferences.excluded_terms or []:
            term = et.lower().strip()
            if term and (term in title_lower or term in desc_lower):
                penalty += 20.0
                gaps.append(
                    GapSignal(
                        type="mismatch",
                        dimension="skills",
                        title=f"Contains excluded keyword: '{et}'",
                        description=f"Listing mentions excluded term: '{et}'.",
                    )
                )
                break

        # 3. Excluded company industries
        if job.company and (preferences.excluded_industries or []):
            comp_ind = [i.lower() for i in (job.company.industry_tags or [])]
            for ei in preferences.excluded_industries:
                if ei.lower() in comp_ind or ei.lower() == (job.company.category or "").lower():
                    penalty += 20.0
                    gaps.append(
                        GapSignal(
                            type="mismatch",
                            dimension="role_family",
                            title=f"Excluded industry sector: '{ei}'",
                            description=(
                                f"Company belongs to an excluded industry category: '{ei}'."
                            ),
                        )
                    )
                    break

        return penalty, gaps
