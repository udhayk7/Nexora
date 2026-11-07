"""
Portfolio Studio & Professional Showcase API Router.
Provides authenticated endpoints for portfolio editing, project showcases, theme customization,
AI assistance, PDF/HTML exports, version history, and unauthenticated public portfolio viewing.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.portfolio import Portfolio
from app.models.user import User
from app.schemas.portfolio import (
    AIPortfolioAssistRequest,
    AIPortfolioAssistResponse,
    PortfolioAnalyticsResponse,
    PortfolioProfileUpdate,
    PortfolioProjectCreate,
    PortfolioProjectResponse,
    PortfolioProjectUpdate,
    PortfolioResponse,
    PortfolioSectionResponse,
    PortfolioSectionsReorderRequest,
    PortfolioSectionUpdate,
    PortfolioThemeUpdate,
    PortfolioVersionCreate,
    PortfolioVersionResponse,
    PublicPortfolioResponse,
    RecordEventRequest,
    SlugUpdateRequest,
)
from app.services.ai.portfolio_assistant_engine import AIPortfolioAssistantEngine
from app.services.portfolio_export_service import PortfolioExportService
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["Portfolio Studio"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _serialize_portfolio(portfolio: Portfolio) -> PortfolioResponse:
    """Helper to convert ORM Portfolio to response model."""
    sections_res = [PortfolioSectionResponse.model_validate(s) for s in portfolio.sections]
    projects_res = [PortfolioProjectResponse.model_validate(p) for p in portfolio.projects]
    return PortfolioResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        public_slug=portfolio.public_slug,
        title=portfolio.title,
        headline=portfolio.headline,
        is_published=portfolio.is_published,
        published_at=portfolio.published_at,
        template_id=portfolio.template_id,
        theme_config=portfolio.theme_config or {},
        profile_data=portfolio.profile_data or {},
        custom_css=portfolio.custom_css,
        sections=sections_res,
        projects=projects_res,
        versions_count=len(portfolio.versions),
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
    )


# ---------------------------------------------------------------------------
# 1. Authenticated Current User Portfolio
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=PortfolioResponse,
    summary="Get or initialize candidate's portfolio",
    description="Retrieve the current user's structured portfolio, or initialize default layout.",
)
def get_my_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.get_or_create_portfolio(db=db, user=current_user)
    return _serialize_portfolio(portfolio)


@router.put(
    "/profile",
    response_model=PortfolioResponse,
    summary="Update portfolio profile information",
    description="Update candidate headline, summary, skills, experience, and contact links.",
)
def update_profile(
    payload: PortfolioProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.update_profile(db=db, user=current_user, data=payload)
    return _serialize_portfolio(portfolio)


@router.put(
    "/theme",
    response_model=PortfolioResponse,
    summary="Update portfolio template and theme settings",
    description="Select between 'minimal', 'developer', and 'ai_tech' layouts and theme styles.",
)
def update_theme(
    payload: PortfolioThemeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.update_theme(db=db, user=current_user, data=payload)
    return _serialize_portfolio(portfolio)


@router.put(
    "/slug",
    response_model=PortfolioResponse,
    summary="Update public URL slug",
    description="Update the secure public shareable slug for the candidate's portfolio.",
)
def update_slug(
    payload: SlugUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.update_public_slug(
        db=db, user=current_user, new_slug=payload.public_slug
    )
    return _serialize_portfolio(portfolio)


# ---------------------------------------------------------------------------
# 2. Section Management & Reordering
# ---------------------------------------------------------------------------


@router.put(
    "/sections",
    response_model=list[PortfolioSectionResponse],
    summary="Reorder and configure sections",
    description="Reorder sections and toggle visibility flags.",
)
def reorder_sections(
    payload: PortfolioSectionsReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PortfolioSectionResponse]:
    sections = PortfolioService.reorder_sections(db=db, user=current_user, req=payload)
    return [PortfolioSectionResponse.model_validate(s) for s in sections]


@router.patch(
    "/sections/{section_id}",
    response_model=PortfolioSectionResponse,
    summary="Update a specific section",
    description="Modify section title, visibility, or custom JSON content.",
)
def update_section(
    section_id: uuid.UUID,
    payload: PortfolioSectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioSectionResponse:
    sec = PortfolioService.update_section(
        db=db, user=current_user, section_id=section_id, data=payload
    )
    return PortfolioSectionResponse.model_validate(sec)


# ---------------------------------------------------------------------------
# 3. Project Showcase Management
# ---------------------------------------------------------------------------


@router.post(
    "/projects",
    response_model=PortfolioProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a showcase project",
    description="Add a new project to the portfolio with architecture, tech stack, and URLs.",
)
def create_project(
    payload: PortfolioProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioProjectResponse:
    proj = PortfolioService.create_project(db=db, user=current_user, data=payload)
    return PortfolioProjectResponse.model_validate(proj)


@router.patch(
    "/projects/{project_id}",
    response_model=PortfolioProjectResponse,
    summary="Update showcase project",
    description="Update project details, links, architecture, or featured status.",
)
def update_project(
    project_id: uuid.UUID,
    payload: PortfolioProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioProjectResponse:
    proj = PortfolioService.update_project(
        db=db, user=current_user, project_id=project_id, data=payload
    )
    return PortfolioProjectResponse.model_validate(proj)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete showcase project",
    description="Remove a project from the portfolio.",
)
def delete_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    PortfolioService.delete_project(db=db, user=current_user, project_id=project_id)
    return {"status": "success", "message": "Project removed from portfolio."}


@router.post(
    "/projects/import-learning/{learning_project_id}",
    response_model=PortfolioProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import project from Learning Roadmap module",
    description="Import a practical project from learning roadmap into portfolio showcase.",
)
def import_learning_project(
    learning_project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioProjectResponse:
    proj = PortfolioService.import_from_learning_project(
        db=db, user=current_user, learning_project_id=learning_project_id
    )
    return PortfolioProjectResponse.model_validate(proj)


@router.post(
    "/import-resume",
    response_model=PortfolioResponse,
    summary="Pre-fill portfolio from latest verified resume",
    description="Imports verified skills and experience from candidate's latest resume analysis.",
)
def import_from_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.import_from_latest_resume(db=db, user=current_user)
    return _serialize_portfolio(portfolio)


# ---------------------------------------------------------------------------
# 4. Publishing Controls
# ---------------------------------------------------------------------------


@router.post(
    "/publish",
    response_model=PortfolioResponse,
    summary="Publish portfolio publicly",
    description="Make the portfolio viewable to recruiters via the public shareable slug.",
)
def publish_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.set_publication_status(db=db, user=current_user, is_published=True)
    return _serialize_portfolio(portfolio)


@router.post(
    "/unpublish",
    response_model=PortfolioResponse,
    summary="Unpublish and revoke public access",
    description="Revoke public access so the portfolio is private and returns 404.",
)
def unpublish_portfolio(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.set_publication_status(
        db=db, user=current_user, is_published=False
    )
    return _serialize_portfolio(portfolio)


# ---------------------------------------------------------------------------
# 5. Version History & Snapshots
# ---------------------------------------------------------------------------


@router.post(
    "/versions",
    response_model=PortfolioVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save portfolio version snapshot",
    description="Create an immutable backup snapshot of current portfolio state.",
)
def create_version(
    payload: PortfolioVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioVersionResponse:
    ver = PortfolioService.create_version_snapshot(
        db=db, user=current_user, summary=payload.change_summary
    )
    return PortfolioVersionResponse.model_validate(ver)


@router.get(
    "/versions",
    response_model=list[PortfolioVersionResponse],
    summary="List portfolio version history",
    description="Retrieve chronological version snapshots for the candidate's portfolio.",
)
def list_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PortfolioVersionResponse]:
    portfolio = PortfolioService.get_or_create_portfolio(db=db, user=current_user)
    return [PortfolioVersionResponse.model_validate(v) for v in portfolio.versions]


@router.post(
    "/versions/{version_id}/restore",
    response_model=PortfolioResponse,
    summary="Restore portfolio to a version snapshot",
    description="Restore profile, sections, and theme settings from a previously saved snapshot.",
)
def restore_version(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioResponse:
    portfolio = PortfolioService.restore_version(db=db, user=current_user, version_id=version_id)
    return _serialize_portfolio(portfolio)


# ---------------------------------------------------------------------------
# 6. AI Portfolio Assistant
# ---------------------------------------------------------------------------


@router.post(
    "/ai-assist",
    response_model=AIPortfolioAssistResponse,
    summary="AI Portfolio Assistant",
    description="Grounded AI suggestions for summaries, project descriptions, and role tailoring.",
)
def ai_assist(
    payload: AIPortfolioAssistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIPortfolioAssistResponse:
    portfolio = PortfolioService.get_or_create_portfolio(db=db, user=current_user)
    profile = portfolio.profile_data or {}
    skills = profile.get("technical_skills") or []
    experience = profile.get("work_experience") or []

    return AIPortfolioAssistantEngine.assist(
        request=payload,
        candidate_skills=skills,
        candidate_experience=experience,
    )


# ---------------------------------------------------------------------------
# 7. Exports (PDF & Static HTML)
# ---------------------------------------------------------------------------


@router.get(
    "/export/html",
    summary="Export standalone static HTML portfolio",
    description="Download a self-contained, responsive HTML file that works offline without CDNs.",
)
def export_html(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    portfolio = PortfolioService.get_or_create_portfolio(db=db, user=current_user)
    html_content = PortfolioExportService.generate_html_export(portfolio)
    PortfolioService.record_event(
        db=db,
        portfolio=portfolio,
        event_type="html_download",
    )
    filename = f"{portfolio.public_slug}_portfolio.html"
    return Response(
        content=html_content,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export/pdf",
    summary="Export recruiter-ready PDF portfolio",
    description="Download an A4 formatted, beautifully typeset PDF summary using ReportLab.",
)
def export_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    portfolio = PortfolioService.get_or_create_portfolio(db=db, user=current_user)
    pdf_bytes = PortfolioExportService.generate_pdf_export(portfolio)
    PortfolioService.record_event(
        db=db,
        portfolio=portfolio,
        event_type="pdf_download",
    )
    filename = f"{portfolio.public_slug}_portfolio.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# 8. Privacy-Conscious Analytics
# ---------------------------------------------------------------------------


@router.get(
    "/analytics",
    response_model=PortfolioAnalyticsResponse,
    summary="Get portfolio visitor analytics",
    description="Aggregated view counts, project interest stats, and referrer categories.",
)
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PortfolioAnalyticsResponse:
    return PortfolioService.get_analytics(db=db, user=current_user)


# ---------------------------------------------------------------------------
# 9. Public Portfolio Endpoints (Unauthenticated)
# ---------------------------------------------------------------------------


@router.get(
    "/public/{public_slug}",
    response_model=PublicPortfolioResponse,
    summary="View published portfolio",
    description="Public access for recruiters. Exposes only approved visible content.",
)
def get_public_portfolio(
    public_slug: str,
    db: Session = Depends(get_db),
    referer: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
) -> PublicPortfolioResponse:
    portfolio = PortfolioService.get_public_portfolio(db=db, public_slug=public_slug)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or is currently private.",
        )

    # Record page view event
    PortfolioService.record_event(
        db=db,
        portfolio=portfolio,
        event_type="page_view",
        referrer=referer,
        user_agent=user_agent,
    )

    # Filter strictly to visible sections and visible projects
    visible_secs = [
        PortfolioSectionResponse.model_validate(s) for s in portfolio.sections if s.is_visible
    ]
    visible_projs = [
        PortfolioProjectResponse.model_validate(p) for p in portfolio.projects if p.is_visible
    ]

    return PublicPortfolioResponse(
        public_slug=portfolio.public_slug,
        title=portfolio.title,
        headline=portfolio.headline,
        template_id=portfolio.template_id,
        theme_config=portfolio.theme_config or {},
        profile_data=portfolio.profile_data or {},
        sections=visible_secs,
        projects=visible_projs,
        published_at=portfolio.published_at,
    )


@router.post(
    "/public/{public_slug}/event",
    status_code=status.HTTP_200_OK,
    summary="Record visitor project interaction",
    description="Record project click or demo view event without collecting visitor personal data.",
)
def record_public_event(
    public_slug: str,
    payload: RecordEventRequest,
    db: Session = Depends(get_db),
    referer: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
) -> dict[str, str]:
    portfolio = PortfolioService.get_public_portfolio(db=db, public_slug=public_slug)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found.",
        )

    valid_types = ("page_view", "project_view", "pdf_download", "html_download")
    event_type = payload.event_type if payload.event_type in valid_types else "project_view"

    PortfolioService.record_event(
        db=db,
        portfolio=portfolio,
        event_type=event_type,
        project_id=payload.project_id,
        referrer=payload.referrer or referer,
        user_agent=user_agent,
    )
    return {"status": "recorded"}


@router.get(
    "/public/{public_slug}/export/pdf",
    summary="Download public portfolio PDF",
    description="Download recruiter-ready PDF resume/portfolio directly from the public page.",
)
def public_export_pdf(
    public_slug: str,
    db: Session = Depends(get_db),
    referer: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
) -> Response:
    portfolio = PortfolioService.get_public_portfolio(db=db, public_slug=public_slug)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or is currently private.",
        )
    pdf_bytes = PortfolioExportService.generate_pdf_export(portfolio)
    PortfolioService.record_event(
        db=db,
        portfolio=portfolio,
        event_type="pdf_download",
        referrer=referer,
        user_agent=user_agent,
    )
    filename = f"{portfolio.public_slug}_portfolio.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/public/{public_slug}/export/html",
    summary="Download public portfolio HTML",
    description="Download offline-capable static HTML portfolio directly from the public page.",
)
def public_export_html(
    public_slug: str,
    db: Session = Depends(get_db),
    referer: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None),
) -> Response:
    portfolio = PortfolioService.get_public_portfolio(db=db, public_slug=public_slug)
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found or is currently private.",
        )
    html_content = PortfolioExportService.generate_html_export(portfolio)
    PortfolioService.record_event(
        db=db,
        portfolio=portfolio,
        event_type="html_download",
        referrer=referer,
        user_agent=user_agent,
    )
    filename = f"{portfolio.public_slug}_portfolio.html"
    return Response(
        content=html_content,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
