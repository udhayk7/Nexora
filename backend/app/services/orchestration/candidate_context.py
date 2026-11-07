import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.application import ApplicationInterview, JobApplication
from app.models.learning_roadmap import LearningProject
from app.models.match import UserMatchingPreference
from app.models.portfolio import Portfolio
from app.models.resume import Resume, ResumeVersion
from app.models.user import User


@dataclass
class SharedCandidateContext:
    """Secure, user-isolated candidate context projection.

    Provides a lean, structured view of candidate qualifications, verified facts,
    career preferences, and application metrics without repeatedly sending
    complete multi-megabyte document strings or leaking private data.
    """

    user_id: uuid.UUID
    full_name: str
    email: str
    target_roles: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    preferred_arrangements: list[str] = field(default_factory=list)
    verified_skills: list[str] = field(default_factory=list)
    verified_projects: list[dict[str, Any]] = field(default_factory=list)
    verified_education: list[str] = field(default_factory=list)
    professional_summary: Optional[str] = None
    resume_version_id: Optional[uuid.UUID] = None
    portfolio_slug: Optional[str] = None
    portfolio_published: bool = False
    career_readiness_score: float = 70.0
    active_applications_count: int = 0
    interviews_scheduled_count: int = 0
    completed_learning_projects_count: int = 0
    target_job_id: Optional[uuid.UUID] = None
    target_job_title: Optional[str] = None
    target_company_name: Optional[str] = None
    target_company_id: Optional[uuid.UUID] = None
    metadata_json: dict[str, Any] = field(default_factory=dict)

    def to_lean_summary(self) -> dict[str, Any]:
        """Returns a compact dictionary representation safe for model prompting."""
        return {
            "candidate_name": self.full_name,
            "target_roles": self.target_roles[:3] or ["Software Engineer"],
            "top_verified_skills": self.verified_skills[:8],
            "total_verified_skills": len(self.verified_skills),
            "verified_projects_count": len(self.verified_projects),
            "readiness_score": round(self.career_readiness_score, 1),
            "active_applications": self.active_applications_count,
            "interviews_scheduled": self.interviews_scheduled_count,
            "portfolio_active": bool(self.portfolio_slug),
            "target_focus": self.target_job_title
            or (self.target_roles[0] if self.target_roles else "General Tech"),
        }

    @classmethod
    def build(
        cls,
        db: Session,
        user: User,
        target_job_id: Optional[uuid.UUID] = None,
        target_company_id: Optional[uuid.UUID] = None,
    ) -> "SharedCandidateContext":
        """Constructs an isolated, verified context snapshot from database state."""
        ctx = cls(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
        )

        # 1. Matching Preferences & Target Roles
        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if pref:
            ctx.target_roles = pref.target_role_families or ["Software Engineer"]
            ctx.preferred_locations = pref.preferred_locations or []
            ctx.preferred_arrangements = pref.work_arrangement_preferences or ["remote", "hybrid"]
        else:
            ctx.target_roles = ["Software Engineer"]
            ctx.preferred_arrangements = ["remote", "hybrid"]

        # 2. Verified Resume Facts (Current Version)
        resume = (
            db.query(Resume)
            .filter(Resume.user_id == user.id)
            .order_by(Resume.created_at.desc())
            .first()
        )
        if resume and resume.current_version_id:
            version = (
                db.query(ResumeVersion)
                .filter(ResumeVersion.id == resume.current_version_id)
                .first()
            )
            if version and version.parsed_content:
                ctx.resume_version_id = version.id
                content = version.parsed_content
                ctx.verified_skills = content.get("skills", [])
                ctx.professional_summary = content.get("summary")

                raw_projs = content.get("projects", [])
                formatted_projs = []
                for p in raw_projs[:5]:
                    if isinstance(p, dict):
                        formatted_projs.append(
                            {
                                "title": p.get("title") or p.get("name") or "Project",
                                "tech": p.get("technologies") or p.get("skills") or [],
                            }
                        )
                    elif isinstance(p, str):
                        formatted_projs.append({"title": p, "tech": []})
                ctx.verified_projects = formatted_projs

                raw_edu = content.get("education", [])
                edu_list = []
                for e in raw_edu[:2]:
                    if isinstance(e, dict):
                        degree = e.get("degree") or "Degree"
                        inst = e.get("institution") or e.get("school") or ""
                        edu_list.append(f"{degree} ({inst})" if inst else degree)
                    elif isinstance(e, str):
                        edu_list.append(e)
                ctx.verified_education = edu_list

        # 3. Portfolio
        port = db.query(Portfolio).filter(Portfolio.user_id == user.id).first()
        if port:
            ctx.portfolio_slug = port.public_slug
            ctx.portfolio_published = port.is_published

        # 4. Applications and Interviews counts
        apps = db.query(JobApplication).filter(JobApplication.user_id == user.id).all()
        ctx.active_applications_count = sum(
            1
            for a in apps
            if a.status in ("applied", "screening", "interview", "assessment", "shortlisted")
        )

        now = datetime.now(timezone.utc)
        interviews = (
            db.query(ApplicationInterview)
            .join(JobApplication, ApplicationInterview.application_id == JobApplication.id)
            .filter(JobApplication.user_id == user.id, ApplicationInterview.scheduled_at >= now)
            .all()
        )
        ctx.interviews_scheduled_count = len(interviews)

        # 5. Learning Projects
        l_projs = (
            db.query(LearningProject)
            .filter(LearningProject.user_id == user.id, LearningProject.status == "completed")
            .count()
        )
        ctx.completed_learning_projects_count = l_projs

        # 6. Target Job Context (if provided)
        if target_job_id:
            from app.models.job import Job

            job = db.query(Job).filter(Job.id == target_job_id).first()
            if job:
                ctx.target_job_id = job.id
                ctx.target_job_title = job.title
                ctx.target_company_name = job.company.name if job.company else None
                ctx.target_company_id = job.company_id

        # 7. Target Company Context (if provided)
        if target_company_id and not ctx.target_company_name:
            from app.models.company import Company

            comp = db.query(Company).filter(Company.id == target_company_id).first()
            if comp:
                ctx.target_company_id = comp.id
                ctx.target_company_name = comp.name

        # Calculate approximate readiness score
        skills_weight = min(len(ctx.verified_skills) * 8.0, 40.0)
        apps_weight = min(ctx.active_applications_count * 5.0, 20.0)
        proj_weight = min(
            (len(ctx.verified_projects) + ctx.completed_learning_projects_count) * 10.0, 30.0
        )
        port_weight = 10.0 if ctx.portfolio_published else 5.0
        ctx.career_readiness_score = min(
            max(skills_weight + apps_weight + proj_weight + port_weight, 35.0), 98.0
        )

        return ctx
