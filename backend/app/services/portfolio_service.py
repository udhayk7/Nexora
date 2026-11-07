"""
Portfolio Service Layer.
Manages candidate portfolio lifecycle, section configuration, project showcases,
versioning, publishing, public view authorization, and privacy-conscious analytics.
"""

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis import ResumeAnalysis
from app.models.learning_roadmap import LearningProject
from app.models.portfolio import (
    Portfolio,
    PortfolioProject,
    PortfolioSection,
    PortfolioVersion,
    PortfolioViewEvent,
)
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioAnalyticsResponse,
    PortfolioProfileUpdate,
    PortfolioProjectCreate,
    PortfolioProjectUpdate,
    PortfolioSectionsReorderRequest,
    PortfolioSectionUpdate,
    PortfolioThemeUpdate,
    ProjectViewStat,
    ViewTrendPoint,
)

DEFAULT_SECTIONS = [
    {"type": "about", "title": "About Me", "order": 0},
    {"type": "projects", "title": "Featured Projects", "order": 1},
    {"type": "skills", "title": "Technical Skills", "order": 2},
    {"type": "experience", "title": "Work Experience", "order": 3},
    {"type": "education", "title": "Education", "order": 4},
    {"type": "certifications", "title": "Certifications & Achievements", "order": 5},
    {"type": "contact", "title": "Contact", "order": 6},
]


class PortfolioService:
    """Core business logic for Portfolio Studio."""

    @classmethod
    def get_or_create_portfolio(cls, db: Session, user: User) -> Portfolio:
        """Retrieve existing user portfolio or initialize a fresh structured portfolio."""
        stmt = select(Portfolio).where(Portfolio.user_id == user.id)
        portfolio = db.execute(stmt).scalars().first()
        if portfolio:
            return portfolio

        # Initialize new portfolio with unguessable slug
        random_suffix = secrets.token_urlsafe(9).replace("-", "").replace("_", "")
        slug = f"p_{random_suffix}"

        # Prepopulate profile data
        initial_name = user.email.split("@")[0].replace(".", " ").title() if user.email else ""
        portfolio = Portfolio(
            user_id=user.id,
            public_slug=slug,
            title=f"{initial_name} Portfolio" if initial_name else "Professional Portfolio",
            headline="Software Engineer",
            is_published=False,
            template_id="minimal",
            theme_config={
                "accent_color": "#3B82F6",
                "font_family": "inter",
                "dark_mode": "system",
                "show_contact_form": False,
                "show_view_counter": True,
            },
            profile_data={
                "full_name": initial_name,
                "headline": "Software Engineer",
                "avatar_url": None,
                "summary": "Software engineer focused on scalable architectures.",
                "location": "",
                "target_roles": ["Software Engineer"],
                "technical_skills": ["Python", "REST APIs", "SQL"],
                "contact_email": user.email,
                "phone": None,
                "github_url": None,
                "linkedin_url": None,
                "website_url": None,
                "education": [],
                "work_experience": [],
                "certifications": [],
                "achievements": [],
            },
        )
        db.add(portfolio)
        db.flush()

        # Add default sections
        for s in DEFAULT_SECTIONS:
            sec = PortfolioSection(
                portfolio_id=portfolio.id,
                section_type=s["type"],
                title=s["title"],
                order_index=s["order"],
                is_visible=True,
            )
            db.add(sec)

        # Create initial version snapshot
        cls.create_version_snapshot(db, user, portfolio, "Initial Portfolio Creation")
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @classmethod
    def update_profile(
        cls,
        db: Session,
        user: User,
        data: PortfolioProfileUpdate,
    ) -> Portfolio:
        """Update candidate portfolio headline and profile data."""
        portfolio = cls.get_or_create_portfolio(db, user)
        if data.title is not None:
            portfolio.title = data.title.strip()
        if data.headline is not None:
            portfolio.headline = data.headline.strip()

        # Update profile data dict
        portfolio.profile_data = data.profile_data.model_dump()
        portfolio.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @classmethod
    def update_theme(
        cls,
        db: Session,
        user: User,
        data: PortfolioThemeUpdate,
    ) -> Portfolio:
        """Update portfolio template and theme settings."""
        portfolio = cls.get_or_create_portfolio(db, user)
        if data.template_id:
            if data.template_id not in ("minimal", "developer", "ai_tech"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid template_id. Choose 'minimal', 'developer', or 'ai_tech'.",
                )
            portfolio.template_id = data.template_id

        portfolio.theme_config = data.theme_config.model_dump()
        if data.custom_css is not None:
            portfolio.custom_css = data.custom_css.strip()

        portfolio.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @classmethod
    def update_public_slug(cls, db: Session, user: User, new_slug: str) -> Portfolio:
        """Update public unguessable or custom URL slug."""
        clean_slug = new_slug.strip().lower()
        if not re.match(r"^[a-z0-9_-]{3,64}$", clean_slug):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Slug must be 3-64 characters using lowercase letters, numbers, and dashes.",
            )

        # Check collision with other portfolios
        existing = (
            db.execute(
                select(Portfolio).where(
                    Portfolio.public_slug == clean_slug,
                    Portfolio.user_id != user.id,
                )
            )
            .scalars()
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This portfolio URL slug is already taken. Please choose another.",
            )

        portfolio = cls.get_or_create_portfolio(db, user)
        portfolio.public_slug = clean_slug
        portfolio.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @classmethod
    def reorder_sections(
        cls,
        db: Session,
        user: User,
        req: PortfolioSectionsReorderRequest,
    ) -> list[PortfolioSection]:
        """Update section ordering and visibility flags."""
        portfolio = cls.get_or_create_portfolio(db, user)
        sec_map = {s.id: s for s in portfolio.sections}

        for item in req.sections:
            if item.id in sec_map:
                sec_map[item.id].order_index = item.order_index
                sec_map[item.id].is_visible = item.is_visible
                sec_map[item.id].updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(portfolio)
        return portfolio.sections

    @classmethod
    def update_section(
        cls,
        db: Session,
        user: User,
        section_id: uuid.UUID,
        data: PortfolioSectionUpdate,
    ) -> PortfolioSection:
        """Update single section details."""
        portfolio = cls.get_or_create_portfolio(db, user)
        sec = next((s for s in portfolio.sections if s.id == section_id), None)
        if not sec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found in your portfolio.",
            )

        if data.title is not None:
            sec.title = data.title.strip()
        if data.is_visible is not None:
            sec.is_visible = data.is_visible
        if data.order_index is not None:
            sec.order_index = data.order_index
        if data.content_json is not None:
            sec.content_json = data.content_json

        sec.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(sec)
        return sec

    @classmethod
    def create_project(
        cls,
        db: Session,
        user: User,
        data: PortfolioProjectCreate,
    ) -> PortfolioProject:
        """Add a showcase project to portfolio."""
        portfolio = cls.get_or_create_portfolio(db, user)
        current_count = len(portfolio.projects)

        proj = PortfolioProject(
            portfolio_id=portfolio.id,
            learning_project_id=data.learning_project_id,
            title=data.title.strip(),
            problem_statement=data.problem_statement,
            description=data.description.strip(),
            tech_stack=data.tech_stack,
            key_features=data.key_features,
            architecture_overview=data.architecture_overview,
            candidate_contribution=data.candidate_contribution,
            repository_url=data.repository_url,
            live_demo_url=data.live_demo_url,
            image_urls=data.image_urls,
            challenges=data.challenges,
            outcomes=data.outcomes,
            status=data.status,
            is_featured=data.is_featured,
            is_visible=data.is_visible,
            order_index=data.order_index or (current_count + 1),
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
        db.refresh(portfolio)
        return proj

    @classmethod
    def update_project(
        cls,
        db: Session,
        user: User,
        project_id: uuid.UUID,
        data: PortfolioProjectUpdate,
    ) -> PortfolioProject:
        """Update portfolio project details."""
        portfolio = cls.get_or_create_portfolio(db, user)
        proj = next((p for p in portfolio.projects if p.id == project_id), None)
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in your portfolio.",
            )

        if data.title is not None:
            proj.title = data.title.strip()
        if data.problem_statement is not None:
            proj.problem_statement = data.problem_statement.strip()
        if data.description is not None:
            proj.description = data.description.strip()
        if data.tech_stack is not None:
            proj.tech_stack = data.tech_stack
        if data.key_features is not None:
            proj.key_features = data.key_features
        if data.architecture_overview is not None:
            proj.architecture_overview = data.architecture_overview.strip()
        if data.candidate_contribution is not None:
            proj.candidate_contribution = data.candidate_contribution.strip()
        if data.repository_url is not None:
            proj.repository_url = data.repository_url.strip() or None
        if data.live_demo_url is not None:
            proj.live_demo_url = data.live_demo_url.strip() or None
        if data.image_urls is not None:
            proj.image_urls = data.image_urls
        if data.challenges is not None:
            proj.challenges = data.challenges.strip() or None
        if data.outcomes is not None:
            proj.outcomes = data.outcomes.strip() or None
        if data.status is not None:
            proj.status = data.status
        if data.is_featured is not None:
            proj.is_featured = data.is_featured
        if data.is_visible is not None:
            proj.is_visible = data.is_visible
        if data.order_index is not None:
            proj.order_index = data.order_index

        proj.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(proj)
        return proj

    @classmethod
    def delete_project(cls, db: Session, user: User, project_id: uuid.UUID) -> None:
        """Remove a project from portfolio."""
        portfolio = cls.get_or_create_portfolio(db, user)
        proj = next((p for p in portfolio.projects if p.id == project_id), None)
        if not proj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found in your portfolio.",
            )
        db.delete(proj)
        db.commit()
        db.refresh(portfolio)

    @classmethod
    def import_from_learning_project(
        cls,
        db: Session,
        user: User,
        learning_project_id: uuid.UUID,
    ) -> PortfolioProject:
        """Import a project created in the Learning Roadmap module into portfolio."""
        lp = (
            db.execute(
                select(LearningProject).where(
                    LearningProject.id == learning_project_id,
                    LearningProject.user_id == user.id,
                )
            )
            .scalars()
            .first()
        )
        if not lp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning project not found.",
            )

        portfolio = cls.get_or_create_portfolio(db, user)
        current_count = len(portfolio.projects)

        proj = PortfolioProject(
            portfolio_id=portfolio.id,
            learning_project_id=lp.id,
            title=lp.title,
            problem_statement=lp.objective,
            description=lp.objective,
            tech_stack=lp.tech_stack or [],
            key_features=lp.functional_requirements or [],
            architecture_overview=lp.architecture_summary,
            candidate_contribution="Primary developer and architect.",
            repository_url=lp.repository_url,
            live_demo_url=lp.live_demo_url,
            image_urls=[],
            challenges="Architectural separation of concerns and automated testing.",
            outcomes=lp.evidence_notes,
            status="completed" if lp.status == "completed" else "in_progress",
            is_featured=True,
            is_visible=True,
            order_index=current_count + 1,
        )
        db.add(proj)
        db.commit()
        db.refresh(proj)
        db.refresh(portfolio)
        return proj

    @classmethod
    def import_from_latest_resume(cls, db: Session, user: User) -> Portfolio:
        """Pre-fill portfolio profile details from user's latest verified resume analysis."""
        stmt = (
            select(ResumeAnalysis)
            .join(ResumeAnalysis.resume)
            .where(ResumeAnalysis.resume.has(user_id=user.id))
            .order_by(ResumeAnalysis.created_at.desc())
        )
        latest_analysis = db.execute(stmt).scalars().first()
        portfolio = cls.get_or_create_portfolio(db, user)

        if not latest_analysis or not latest_analysis.result:
            return portfolio

        res_dict = latest_analysis.result
        profile_data = dict(portfolio.profile_data or {})

        # Extract profile summary
        cand_profile = res_dict.get("profile") or {}
        if cand_profile.get("summary") and not profile_data.get("summary"):
            profile_data["summary"] = cand_profile["summary"]

        # Extract skills
        skills_sec = res_dict.get("skills") or {}
        supported = skills_sec.get("supported_skills") or []
        if supported:
            existing_skills = set(profile_data.get("technical_skills") or [])
            for s in supported:
                existing_skills.add(s)
            profile_data["technical_skills"] = list(existing_skills)

        # Extract experience
        exp_sec = res_dict.get("experience_evidence") or {}
        roles = exp_sec.get("roles") or []
        if roles and not profile_data.get("work_experience"):
            parsed_exp = []
            for r in roles:
                parsed_exp.append(
                    {
                        "company": r.get("company", ""),
                        "role": r.get("role", ""),
                        "location": r.get("location", ""),
                        "start_date": r.get("start_date", ""),
                        "end_date": r.get("end_date", ""),
                        "is_current": False,
                        "description": r.get("responsibilities_summary", ""),
                        "bullet_points": r.get("key_achievements", []),
                    }
                )
            profile_data["work_experience"] = parsed_exp

        portfolio.profile_data = profile_data
        portfolio.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @classmethod
    def set_publication_status(cls, db: Session, user: User, is_published: bool) -> Portfolio:
        """Publish or revoke public availability of the portfolio."""
        portfolio = cls.get_or_create_portfolio(db, user)
        portfolio.is_published = is_published
        if is_published:
            portfolio.published_at = datetime.now(timezone.utc)
        portfolio.updated_at = datetime.now(timezone.utc)

        summary = "Published Portfolio" if is_published else "Unpublished Portfolio"
        cls.create_version_snapshot(db, user, portfolio, summary)

        db.commit()
        db.refresh(portfolio)
        return portfolio

    @classmethod
    def create_version_snapshot(
        cls,
        db: Session,
        user: User,
        portfolio: Optional[Portfolio] = None,
        summary: Optional[str] = None,
    ) -> PortfolioVersion:
        """Capture an immutable serialized snapshot of portfolio state."""
        if not portfolio:
            portfolio = cls.get_or_create_portfolio(db, user)

        version_count = (
            db.scalar(
                select(func.count(PortfolioVersion.id)).where(
                    PortfolioVersion.portfolio_id == portfolio.id
                )
            )
            or 0
        )

        snapshot = {
            "title": portfolio.title,
            "headline": portfolio.headline,
            "template_id": portfolio.template_id,
            "theme_config": portfolio.theme_config,
            "profile_data": portfolio.profile_data,
            "custom_css": portfolio.custom_css,
            "sections": [
                {
                    "section_type": s.section_type,
                    "title": s.title,
                    "is_visible": s.is_visible,
                    "order_index": s.order_index,
                    "content_json": s.content_json,
                }
                for s in portfolio.sections
            ],
            "projects": [
                {
                    "title": p.title,
                    "problem_statement": p.problem_statement,
                    "description": p.description,
                    "tech_stack": p.tech_stack,
                    "key_features": p.key_features,
                    "architecture_overview": p.architecture_overview,
                    "candidate_contribution": p.candidate_contribution,
                    "repository_url": p.repository_url,
                    "live_demo_url": p.live_demo_url,
                    "challenges": p.challenges,
                    "outcomes": p.outcomes,
                    "status": p.status,
                    "is_featured": p.is_featured,
                    "is_visible": p.is_visible,
                    "order_index": p.order_index,
                }
                for p in portfolio.projects
            ],
        }

        ver = PortfolioVersion(
            portfolio_id=portfolio.id,
            version_number=version_count + 1,
            snapshot_json=snapshot,
            change_summary=summary or f"Version {version_count + 1} snapshot",
        )
        db.add(ver)
        db.commit()
        db.refresh(ver)
        return ver

    @classmethod
    def restore_version(cls, db: Session, user: User, version_id: uuid.UUID) -> Portfolio:
        """Restore portfolio to a previously captured snapshot state."""
        portfolio = cls.get_or_create_portfolio(db, user)
        ver = (
            db.execute(
                select(PortfolioVersion).where(
                    PortfolioVersion.id == version_id,
                    PortfolioVersion.portfolio_id == portfolio.id,
                )
            )
            .scalars()
            .first()
        )
        if not ver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio version not found.",
            )

        snap = ver.snapshot_json
        portfolio.title = snap.get("title", portfolio.title)
        portfolio.headline = snap.get("headline", portfolio.headline)
        portfolio.template_id = snap.get("template_id", portfolio.template_id)
        portfolio.theme_config = snap.get("theme_config", portfolio.theme_config)
        portfolio.profile_data = snap.get("profile_data", portfolio.profile_data)
        portfolio.custom_css = snap.get("custom_css", portfolio.custom_css)
        portfolio.updated_at = datetime.now(timezone.utc)

        cls.create_version_snapshot(
            db, user, portfolio, f"Restored from Version {ver.version_number}"
        )
        db.commit()
        db.refresh(portfolio)
        return portfolio

    @classmethod
    def get_public_portfolio(cls, db: Session, public_slug: str) -> Optional[Portfolio]:
        """Fetch portfolio by public slug. Returns None if unapproved or not published."""
        stmt = select(Portfolio).where(
            Portfolio.public_slug == public_slug,
            Portfolio.is_published.is_(True),
        )
        return db.execute(stmt).scalars().first()

    @classmethod
    def record_event(
        cls,
        db: Session,
        portfolio: Portfolio,
        event_type: str,
        project_id: Optional[uuid.UUID] = None,
        referrer: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Record a privacy-conscious visitor interaction event."""
        # Sanitize referrer category
        ref_cat = "direct"
        if referrer:
            ref_lower = referrer.lower()
            if "linkedin.com" in ref_lower:
                ref_cat = "linkedin"
            elif "github.com" in ref_lower:
                ref_cat = "github"
            elif any(s in ref_lower for s in ("google", "bing", "duckduckgo")):
                ref_cat = "search"
            elif any(s in ref_lower for s in ("twitter", "x.com", "threads")):
                ref_cat = "social"
            else:
                ref_cat = "other"

        # Sanitize user agent category
        ua_cat = "desktop"
        if user_agent:
            ua_lower = user_agent.lower()
            if any(b in ua_lower for b in ("bot", "crawler", "spider")):
                ua_cat = "bot"
            elif any(m in ua_lower for m in ("iphone", "android", "mobile")):
                ua_cat = "mobile"
            elif "ipad" in ua_lower or "tablet" in ua_lower:
                ua_cat = "tablet"

        evt = PortfolioViewEvent(
            portfolio_id=portfolio.id,
            event_type=event_type,
            project_id=project_id,
            referrer_category=ref_cat,
            user_agent_category=ua_cat,
        )
        db.add(evt)
        db.commit()

    @classmethod
    def get_analytics(cls, db: Session, user: User) -> PortfolioAnalyticsResponse:
        """Compute privacy-conscious analytics for candidate's portfolio."""
        portfolio = cls.get_or_create_portfolio(db, user)

        # 1. Total views
        total_views = (
            db.scalar(
                select(func.count(PortfolioViewEvent.id)).where(
                    PortfolioViewEvent.portfolio_id == portfolio.id,
                    PortfolioViewEvent.event_type == "page_view",
                )
            )
            or 0
        )

        # 2. Project views
        proj_views = (
            db.scalar(
                select(func.count(PortfolioViewEvent.id)).where(
                    PortfolioViewEvent.portfolio_id == portfolio.id,
                    PortfolioViewEvent.event_type == "project_view",
                )
            )
            or 0
        )

        # 3. Downloads count (PDF + HTML)
        downloads = (
            db.scalar(
                select(func.count(PortfolioViewEvent.id)).where(
                    PortfolioViewEvent.portfolio_id == portfolio.id,
                    PortfolioViewEvent.event_type.in_(["pdf_download", "html_download"]),
                )
            )
            or 0
        )

        # 4. Views by date (past 14 days)
        cutoff = datetime.now(timezone.utc) - timedelta(days=14)
        daily_stmt = (
            select(
                func.date(PortfolioViewEvent.created_at).label("day"),
                func.count(PortfolioViewEvent.id).label("cnt"),
            )
            .where(
                PortfolioViewEvent.portfolio_id == portfolio.id,
                PortfolioViewEvent.created_at >= cutoff,
            )
            .group_by(func.date(PortfolioViewEvent.created_at))
            .order_by(func.date(PortfolioViewEvent.created_at))
        )
        daily_rows = db.execute(daily_stmt).all()
        trend_points = [ViewTrendPoint(date=str(row.day), views=int(row.cnt)) for row in daily_rows]

        # 5. Top viewed projects
        top_projects: list[ProjectViewStat] = []
        proj_map = {p.id: p.title for p in portfolio.projects}
        top_p_stmt = (
            select(
                PortfolioViewEvent.project_id,
                func.count(PortfolioViewEvent.id).label("cnt"),
            )
            .where(
                PortfolioViewEvent.portfolio_id == portfolio.id,
                PortfolioViewEvent.project_id.is_not(None),
            )
            .group_by(PortfolioViewEvent.project_id)
            .order_by(func.count(PortfolioViewEvent.id).desc())
            .limit(5)
        )
        top_p_rows = db.execute(top_p_stmt).all()
        for row in top_p_rows:
            if row.project_id in proj_map:
                top_projects.append(
                    ProjectViewStat(
                        project_id=str(row.project_id),
                        title=proj_map[row.project_id],
                        views=int(row.cnt),
                    )
                )

        # 6. Referrers & Devices
        ref_rows = db.execute(
            select(
                PortfolioViewEvent.referrer_category,
                func.count(PortfolioViewEvent.id),
            )
            .where(PortfolioViewEvent.portfolio_id == portfolio.id)
            .group_by(PortfolioViewEvent.referrer_category)
        ).all()
        referrers = {str(r[0]): int(r[1]) for r in ref_rows}

        dev_rows = db.execute(
            select(
                PortfolioViewEvent.user_agent_category,
                func.count(PortfolioViewEvent.id),
            )
            .where(PortfolioViewEvent.portfolio_id == portfolio.id)
            .group_by(PortfolioViewEvent.user_agent_category)
        ).all()
        devices = {str(d[0]): int(d[1]) for d in dev_rows}

        return PortfolioAnalyticsResponse(
            total_views=total_views,
            project_views=proj_views,
            downloads_count=downloads,
            views_by_date=trend_points,
            top_viewed_projects=top_projects,
            referrers=referrers,
            devices=devices,
        )
