"""FastAPI router for Company Intelligence, Research, and Candidate Fit."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.company_intelligence import (
    CompanyFitAssessmentResponse,
    CompanyIntelligenceResponse,
    CompanyProductOrService,
    CompanyResearchGenerateRequest,
    CompanyResearchReportResponse,
    CompanyResearchSourceResponse,
    HiringSummarySchema,
    RecentDevelopmentItem,
    TechnologyItemSchema,
)
from app.services.company_intelligence_service import CompanyIntelligenceService

router = APIRouter(tags=["Company Intelligence & Research"])


@router.get(
    "/companies/{company_id}/intelligence",
    response_model=CompanyIntelligenceResponse,
    summary="Get or generate evidence-backed company intelligence profile",
)
def get_company_intelligence(
    company_id: uuid.UUID,
    refresh: bool = Query(False, description="Re-fetch web sources and refresh intelligence"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyIntelligenceResponse:
    service = CompanyIntelligenceService(db)
    intel = service.get_or_create_company_intelligence(company_id=company_id, refresh=refresh)
    company = service.get_company_or_404(company_id)

    return CompanyIntelligenceResponse(
        id=intel.id,
        company_id=intel.company_id,
        company_name=company.name,
        overview=intel.overview,
        industry_domain=intel.industry_domain,
        headquarters=intel.headquarters,
        operating_locations=intel.operating_locations,
        website_url=intel.website_url,
        careers_url=intel.careers_url,
        products_and_services=[
            CompanyProductOrService.model_validate(p) for p in (intel.products_and_services or [])
        ],
        technology_stack=[
            TechnologyItemSchema.model_validate(t) for t in (intel.technology_stack or [])
        ],
        size_band=intel.size_band,
        size_evidence=intel.size_evidence,
        funding_ownership_info=intel.funding_ownership_info,
        recent_developments=[
            RecentDevelopmentItem.model_validate(d) for d in (intel.recent_developments or [])
        ],
        hiring_summary=HiringSummarySchema.model_validate(intel.hiring_summary or {}),
        last_researched_at=intel.last_researched_at,
        is_stale=intel.is_stale,
        provenance_sources_count=intel.provenance_sources_count,
        metadata_json=intel.metadata_json,
        created_at=intel.created_at,
        updated_at=intel.updated_at,
    )


@router.get(
    "/companies/{company_id}/technology",
    response_model=list[TechnologyItemSchema],
    summary="Get technology intelligence with evidence classifications",
)
def get_company_technology(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[TechnologyItemSchema]:
    service = CompanyIntelligenceService(db)
    intel = service.get_or_create_company_intelligence(company_id=company_id)
    return [TechnologyItemSchema(**item) for item in (intel.technology_stack or [])]


@router.get(
    "/companies/{company_id}/hiring",
    response_model=HiringSummarySchema,
    summary="Get aggregated hiring metrics from verified jobs in Nexora DB",
)
def get_company_hiring_summary(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> HiringSummarySchema:
    service = CompanyIntelligenceService(db)
    summary, _ = service.compute_hiring_summary(company_id=company_id)
    return HiringSummarySchema(**summary)


@router.get(
    "/companies/{company_id}/fit",
    response_model=CompanyFitAssessmentResponse,
    summary="Assess candidate-to-company fit grounded in user's resume",
)
def get_company_fit(
    company_id: uuid.UUID,
    resume_version_id: Optional[uuid.UUID] = Query(
        None, description="Optional resume version to assess against"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyFitAssessmentResponse:
    service = CompanyIntelligenceService(db)
    fit_data = service.get_candidate_fit(
        user=current_user,
        company_id=company_id,
        resume_version_id=resume_version_id,
    )
    return CompanyFitAssessmentResponse(**fit_data)


@router.get(
    "/companies/{company_id}/sources",
    response_model=list[CompanyResearchSourceResponse],
    summary="List public research documents and sources for a company",
)
def list_company_sources(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[CompanyResearchSourceResponse]:
    service = CompanyIntelligenceService(db)
    sources = service.list_sources(company_id=company_id)
    return [CompanyResearchSourceResponse.model_validate(s) for s in sources]


@router.post(
    "/companies/{company_id}/research/generate",
    response_model=CompanyResearchReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate or retrieve cached structured 10-section research report",
)
def generate_company_research_report(
    company_id: uuid.UUID,
    req: CompanyResearchGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyResearchReportResponse:
    service = CompanyIntelligenceService(db)
    company = service.get_company_or_404(company_id)
    report = service.generate_research_report(
        user=current_user,
        company_id=company_id,
        req=req,
    )
    return CompanyResearchReportResponse(
        id=report.id,
        company_id=report.company_id,
        company_name=company.name,
        user_id=report.user_id,
        report_title=report.report_title,
        sections=report.sections,
        candidate_fit=report.candidate_fit,
        source_evidence=report.source_evidence,
        provider=report.provider,
        model=report.model,
        is_cached=report.is_cached,
        is_deterministic_fallback=report.is_deterministic_fallback,
        metadata_json=report.metadata_json,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get(
    "/companies/{company_id}/research/reports",
    response_model=list[CompanyResearchReportResponse],
    summary="List research reports generated by user for a specific company",
)
def list_company_reports_for_company(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[CompanyResearchReportResponse]:
    service = CompanyIntelligenceService(db)
    company = service.get_company_or_404(company_id)
    reports = service.list_user_reports(user=current_user, company_id=company_id)
    return [
        CompanyResearchReportResponse(
            id=r.id,
            company_id=r.company_id,
            company_name=company.name,
            user_id=r.user_id,
            report_title=r.report_title,
            sections=r.sections,
            candidate_fit=r.candidate_fit,
            source_evidence=r.source_evidence,
            provider=r.provider,
            model=r.model,
            is_cached=r.is_cached,
            is_deterministic_fallback=r.is_deterministic_fallback,
            metadata_json=r.metadata_json,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in reports
    ]


@router.get(
    "/company-intelligence/reports",
    response_model=list[CompanyResearchReportResponse],
    summary="List all company research reports generated by current user",
)
def list_all_user_company_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[CompanyResearchReportResponse]:
    service = CompanyIntelligenceService(db)
    reports = service.list_user_reports(user=current_user)
    results: list[CompanyResearchReportResponse] = []
    for r in reports:
        c_name = r.company.name if r.company else "Company"
        results.append(
            CompanyResearchReportResponse(
                id=r.id,
                company_id=r.company_id,
                company_name=c_name,
                user_id=r.user_id,
                report_title=r.report_title,
                sections=r.sections,
                candidate_fit=r.candidate_fit,
                source_evidence=r.source_evidence,
                provider=r.provider,
                model=r.model,
                is_cached=r.is_cached,
                is_deterministic_fallback=r.is_deterministic_fallback,
                metadata_json=r.metadata_json,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return results


@router.get(
    "/company-intelligence/reports/{report_id}",
    response_model=CompanyResearchReportResponse,
    summary="Get single company research report details",
)
def get_company_report_detail(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CompanyResearchReportResponse:
    service = CompanyIntelligenceService(db)
    report = service.get_report_or_404(user=current_user, report_id=report_id)
    c_name = report.company.name if report.company else "Company"
    return CompanyResearchReportResponse(
        id=report.id,
        company_id=report.company_id,
        company_name=c_name,
        user_id=report.user_id,
        report_title=report.report_title,
        sections=report.sections,
        candidate_fit=report.candidate_fit,
        source_evidence=report.source_evidence,
        provider=report.provider,
        model=report.model,
        is_cached=report.is_cached,
        is_deterministic_fallback=report.is_deterministic_fallback,
        metadata_json=report.metadata_json,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.delete(
    "/company-intelligence/reports/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company research report owned by current user",
)
def delete_company_report(
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    service = CompanyIntelligenceService(db)
    service.delete_report(user=current_user, report_id=report_id)
