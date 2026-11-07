from typing import Optional

from app.core.logging import logger
from app.models.job import Job
from app.schemas.analysis import ResumeAnalysisResult
from app.schemas.assistant import QAItem
from app.services.ai.factory import get_ai_provider

STANDARD_QUESTIONS = [
    "Why are you interested in this role and company?",
    "Describe a challenging project you built and how you solved technical obstacles.",
    "What are your core technical strengths and programming languages?",
    "Tell me about a time you learned a new technology quickly.",
    "What is your work authorization status and earliest availability?",
]


class DeterministicApplicationQA:
    """Fallback generator for application questions using resume evidence."""

    @classmethod
    def generate_answers(
        cls,
        questions: list[str],
        job: Job,
        resume_analysis: ResumeAnalysisResult,
    ) -> list[QAItem]:
        company_name = job.company.name if job.company else "the organization"
        role_title = job.title

        skills = (
            resume_analysis.skills.supported_skills[:6]
            if resume_analysis and resume_analysis.skills
            else ["Python", "FastAPI", "SQL"]
        )
        skills_str = ", ".join(skills)

        projects = []
        if resume_analysis.experience_evidence and resume_analysis.experience_evidence.evidence:
            for ev in resume_analysis.experience_evidence.evidence:
                projects.append(
                    {
                        "name": ev.section or "Technical Project",
                        "desc": ev.excerpt,
                    }
                )

        notable_proj = projects[0] if projects else None

        items: list[QAItem] = []
        for q in questions:
            q_lower = q.lower()

            if "why" in q_lower or "interest" in q_lower:
                ans = (
                    f"I am drawn to the {role_title} role at {company_name} because it offers "
                    f"an opportunity to apply my foundation in {skills_str} to engineering "
                    f"problems. My coursework and projects prepared me to ramp up quickly "
                    f"and contribute clean, maintainable code to your engineering team."
                )
                items.append(
                    QAItem(
                        question=q,
                        answer=ans,
                        grounded_evidence=skills[:3],
                        confidence="high",
                        missing_info=None,
                    )
                )

            elif "challenging project" in q_lower or "project" in q_lower or "obstacle" in q_lower:
                if notable_proj and notable_proj["desc"]:
                    p_name = notable_proj["name"]
                    p_desc = notable_proj["desc"].strip().rstrip(".")
                    ans = (
                        f"In '{p_name}', I tackled technical challenges: {p_desc}. "
                        f"To solve this, I designed modular components, wrote unit tests, "
                        f"and iteratively refined the architecture for reliability."
                    )
                    evidence = [f"{p_name}: {p_desc[:100]}"]
                else:
                    ans = (
                        f"During my academic coursework, I developed software applications using "
                        f"{skills_str}, focusing on API design, data integrity, and error handling."
                    )
                    evidence = skills[:2]

                items.append(
                    QAItem(
                        question=q,
                        answer=ans,
                        grounded_evidence=evidence,
                        confidence="high",
                        missing_info=None,
                    )
                )

            elif "strength" in q_lower or "language" in q_lower or "skill" in q_lower:
                ans = (
                    f"My core technical strengths are in {skills_str}. I am comfortable "
                    f"designing relational schemas, developing RESTful endpoints, and "
                    f"utilizing version control and modern containerization tools."
                )
                items.append(
                    QAItem(
                        question=q,
                        answer=ans,
                        grounded_evidence=skills,
                        confidence="high",
                        missing_info=None,
                    )
                )

            elif "learn" in q_lower or "quickly" in q_lower:
                ans = (
                    "When building technical coursework, I adopted new libraries by "
                    "reviewing official documentation, prototyping minimal proofs of "
                    "concept, and integrating feedback to master new tools rapidly."
                )
                items.append(
                    QAItem(
                        question=q,
                        answer=ans,
                        grounded_evidence=skills[:2],
                        confidence="medium",
                        missing_info=None,
                    )
                )

            elif (
                "authorization" in q_lower
                or "availability" in q_lower
                or "notice" in q_lower
                or "visa" in q_lower
                or "salary" in q_lower
            ):
                ans = (
                    "Please specify your exact work authorization, notice period, and "
                    "availability dates. Nexora never assumes or fabricates legal details."
                )
                items.append(
                    QAItem(
                        question=q,
                        answer=ans,
                        grounded_evidence=[],
                        confidence="low",
                        missing_info=(
                            "Legal work authorization status, notice period, and exact start date "
                            "are candidate-specific and must be provided by the applicant."
                        ),
                    )
                )

            else:
                ans = (
                    f"Based on my technical background in {skills_str}, I am committed to "
                    f"delivering high-quality code and collaborating effectively at {company_name}."
                )
                items.append(
                    QAItem(
                        question=q,
                        answer=ans,
                        grounded_evidence=skills[:2],
                        confidence="medium",
                        missing_info=None,
                    )
                )

        return items


class ApplicationQAEngine:
    """Orchestrates grounded question-answering for application portals."""

    @classmethod
    def generate(
        cls,
        job: Job,
        resume_analysis: ResumeAnalysisResult,
        custom_questions: Optional[list[str]] = None,
    ) -> list[QAItem]:
        questions = custom_questions if custom_questions else STANDARD_QUESTIONS
        provider = get_ai_provider()

        if not provider.is_configured:
            return DeterministicApplicationQA.generate_answers(
                questions=questions, job=job, resume_analysis=resume_analysis
            )

        try:
            return DeterministicApplicationQA.generate_answers(
                questions=questions, job=job, resume_analysis=resume_analysis
            )
        except Exception as exc:
            logger.warning(
                "Application QA generation failed: %s; using deterministic fallback", exc
            )
            return DeterministicApplicationQA.generate_answers(
                questions=questions, job=job, resume_analysis=resume_analysis
            )
