import re
from typing import Any, Optional

from app.models.job import Job
from app.models.match import JobMatch
from app.models.resume import ResumeVersion
from app.schemas.analysis import ResumeAnalysisResult
from app.schemas.tailoring import JobRequirementAnalysis


def normalize_term(term: str) -> str:
    """Normalize a technology or skill string for case-insensitive comparison."""
    clean = re.sub(r"[^\w\s\.\-\/\#\+]", "", term.lower()).strip()
    return clean


class TailoringAnalyzer:
    """
    Grounded job requirement analyzer.
    Identifies relevant skills, relevant experiences, missing requirements,
    and truthful keyword opportunities without ever fabricating qualifications.
    """

    @classmethod
    def analyze_requirements(
        cls,
        job: Job,
        version: ResumeVersion,
        analysis: Optional[ResumeAnalysisResult] = None,
        job_match: Optional[JobMatch] = None,
    ) -> JobRequirementAnalysis:
        parsed_content: dict[str, Any] = version.parsed_content or {}

        # 1. Collect candidate skills
        candidate_skills_raw: list[str] = list(parsed_content.get("skills") or [])
        if analysis and analysis.skills and analysis.skills.supported_skills:
            for s in analysis.skills.supported_skills:
                if s not in candidate_skills_raw:
                    candidate_skills_raw.append(s)

        candidate_skills_norm = {normalize_term(s): s for s in candidate_skills_raw if s.strip()}

        # 2. Collect job requirements
        job_skills_raw: list[str] = list(job.skills_tags or [])
        desc_text = (job.description or "") + " " + (job.title or "")
        desc_lower = desc_text.lower()

        # If job skills_tags is empty, detect mentions in title and description
        detected_job_skills: list[str] = list(job_skills_raw)
        if not detected_job_skills:
            # Common tech stack tokens
            common_tokens = [
                "python",
                "fastapi",
                "django",
                "flask",
                "react",
                "typescript",
                "javascript",
                "postgresql",
                "sql",
                "docker",
                "kubernetes",
                "aws",
                "gcp",
                "git",
                "node.js",
                "rest api",
                "graphql",
                "ci/cd",
                "linux",
                "java",
                "c++",
                "golang",
            ]
            for token in common_tokens:
                if token in desc_lower:
                    detected_job_skills.append(token.title())

        # 3. Partition into Relevant vs Missing
        relevant_skills: list[str] = []
        missing_requirements: list[str] = []

        for req in detected_job_skills:
            req_norm = normalize_term(req)
            if not req_norm:
                continue

            if req_norm in candidate_skills_norm:
                canonical = candidate_skills_norm[req_norm]
                if canonical not in relevant_skills:
                    relevant_skills.append(canonical)
            elif any(
                req_norm in s_norm or s_norm in req_norm for s_norm in candidate_skills_norm
            ):
                matched_s = next(
                    candidate_skills_norm[s_norm]
                    for s_norm in candidate_skills_norm
                    if req_norm in s_norm or s_norm in req_norm
                )
                if matched_s not in relevant_skills:
                    relevant_skills.append(matched_s)
            else:
                if req not in missing_requirements:
                    missing_requirements.append(req)

        # 4. Extract Relevant Experience
        relevant_experience: list[str] = []
        experiences = parsed_content.get("experience") or []
        for exp in experiences:
            if isinstance(exp, dict):
                exp_title = exp.get("title") or ""
                exp_company = exp.get("company") or ""
                bullets = exp.get("bullets") or []

                # Check if experience mentions role family or relevant skills
                matches_rel = False
                for bullet in bullets:
                    bullet_lower = str(bullet).lower()
                    if any(rs.lower() in bullet_lower for rs in relevant_skills):
                        matches_rel = True
                        relevant_experience.append(
                            f"{exp_title} at {exp_company}: {bullet[:140]}..."
                        )
                        break
                if not matches_rel and (
                    job.role_family and job.role_family.lower() in exp_title.lower()
                ):
                    relevant_experience.append(f"{exp_title} at {exp_company}")

        projects = parsed_content.get("projects") or []
        for proj in projects:
            if isinstance(proj, dict):
                p_title = proj.get("title") or "Project"
                p_bullets = proj.get("bullets") or []
                for b in p_bullets:
                    b_lower = str(b).lower()
                    if any(rs.lower() in b_lower for rs in relevant_skills):
                        relevant_experience.append(f"Project '{p_title}': {b[:140]}...")
                        break

        # 5. Identify Truthful Keyword Opportunities
        keyword_opportunities: list[str] = []
        # Look for tech keywords present in job description that candidate has related experience in
        keyword_candidate_map = {
            "rest api": "FastAPI, Flask, or backend services demonstrated in resume",
            "microservices": "Distributed systems or service architecture referenced",
            "relational database": "PostgreSQL or SQL databases present in skills",
            "version control": "Git and GitHub workflows present in experience",
            "unit testing": "Automated testing or test coverage evidenced in projects",
            "agile": "Sprint delivery and team collaboration mentioned",
            "docker": "Containerized deployment referenced in skills or projects",
        }

        for kw, support_rationale in keyword_candidate_map.items():
            if kw in desc_lower and kw not in [s.lower() for s in candidate_skills_raw]:
                # Check if supporting context exists
                has_context = (
                    ("api" in kw and any("api" in s.lower() for s in candidate_skills_raw))
                    or (
                        "database" in kw
                        and any(
                            db_term in s.lower()
                            for s in candidate_skills_raw
                            for db_term in ["sql", "postgres", "mysql"]
                        )
                    )
                    or ("docker" in kw and any("docker" in s.lower() for s in candidate_skills_raw))
                    or ("testing" in kw and any("test" in s.lower() for s in candidate_skills_raw))
                )

                if has_context:
                    keyword_opportunities.append(
                        f"'{kw.title()}' (supported by {support_rationale})"
                    )

        # 6. Actionable Improvement Opportunities
        improvement_opportunities: list[str] = []
        if len(relevant_skills) < len(detected_job_skills) and missing_requirements:
            improvement_opportunities.append(
                f"Clarify project bullet points to highlight {', '.join(missing_requirements[:2])} "
                "if you have academic or self-directed project exposure."
            )

        comp_name = job.company.name if job.company else "target employer"
        if not parsed_content.get("summary"):
            improvement_opportunities.append(
                f"Add a targeted Professional Summary directly addressing the {job.title} role."
            )
        else:
            improvement_opportunities.append(
                f"Tailor professional summary opening to align with {job.title} at {comp_name}."
            )

        improvement_opportunities.append(
            "Emphasize measurable outcomes and technical scope in project bullets."
        )

        # Summary Notes
        job_match_score = f"{job_match.match_score:.0f}%" if job_match else "computed"
        summary_notes = (
            f"Role: {job.title} ({job.company.name if job.company else 'Direct'}). "
            f"Found {len(relevant_skills)} matching candidate skills, "
            f"{len(missing_requirements)} missing requisitions (neutral, unpenalized), "
            f"and {len(relevant_experience)} relevant project/experience anchors. "
            f"Baseline alignment score: {job_match_score}."
        )

        return JobRequirementAnalysis(
            relevant_skills=relevant_skills[:15],
            relevant_experience=relevant_experience[:8],
            missing_requirements=missing_requirements[:10],
            keyword_opportunities=keyword_opportunities[:6],
            improvement_opportunities=improvement_opportunities[:5],
            summary_notes=summary_notes,
        )
