"""Company Intelligence & Research Service.

Coordinates public research ingestion, hiring analytics from real DB jobs,
technology stack evidence classification, candidate fit assessment, and AI reports.
"""

import hashlib
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.logging import logger
from app.models.analysis import ResumeAnalysis
from app.models.company import Company
from app.models.company_intelligence import (
    CompanyIntelligence,
    CompanyResearchReport,
    CompanyResearchSource,
)
from app.models.job import Job
from app.models.match import UserMatchingPreference
from app.models.user import User
from app.schemas.company_intelligence import CompanyResearchGenerateRequest
from app.services.ai.company_research_report_engine import (
    AICompanyResearchReportEngine,
    compute_research_cache_hash,
)
from app.services.company_intelligence.adapters import OfficialWebsiteAdapter
from app.services.company_intelligence.fit_evaluator import evaluate_company_fit
from app.services.company_intelligence.technology_extractor import (
    extract_technologies_with_evidence,
)


class CompanyIntelligenceService:
    """Core domain service for company research and intelligence."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.adapter = OfficialWebsiteAdapter()

    def get_company_or_404(self, company_id: uuid.UUID) -> Company:
        company = self.db.execute(
            select(Company).where(Company.id == company_id)
        ).scalar_one_or_none()
        if not company:
            raise NotFoundError(f"Company {company_id} not found")
        return company

    def compute_hiring_summary(
        self, company_id: uuid.UUID
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Aggregate actual discovered job records from Nexora DB."""
        jobs = (
            self.db.execute(
                select(Job).where(Job.company_id == company_id).order_by(desc(Job.first_seen_at))
            )
            .scalars()
            .all()
        )

        active_jobs: list[dict[str, Any]] = []
        stale_count = 0
        entry_level_count = 0
        internship_count = 0
        categories_map: dict[str, int] = {}
        locations_set: set[str] = set()
        active_tech_set: set[str] = set()
        last_posted: Optional[str] = None

        for j in jobs:
            is_active = j.job_status == "active"
            if is_active:
                job_dict = {
                    "id": str(j.id),
                    "title": j.title,
                    "seniority_level": j.seniority_level,
                    "location_text": j.location_text
                    or (f"{j.city}, {j.country}" if j.city else None),
                    "role_family": j.role_family,
                    "job_status": j.job_status,
                    "description": j.description or "",
                    "skills_tags": list(j.skills_tags or []),
                }
                active_jobs.append(job_dict)

                # Seniority breakdowns
                s_level = (j.seniority_level or "").lower()
                title_lower = (j.title or "").lower()
                if "intern" in s_level or "intern" in title_lower:
                    internship_count += 1
                    entry_level_count += 1
                elif (
                    "entry" in s_level
                    or "junior" in title_lower
                    or "graduate" in title_lower
                    or "associate" in s_level
                ):
                    entry_level_count += 1

                # Role categories
                rf = j.role_family or "Engineering / Tech"
                categories_map[rf] = categories_map.get(rf, 0) + 1

                # Locations
                if j.location_text:
                    locations_set.add(j.location_text)
                elif j.city:
                    loc = f"{j.city}, {j.country}" if j.country else j.city
                    locations_set.add(loc)

                # Technologies from job skills
                for s in j.skills_tags or []:
                    active_tech_set.add(s)

                if not last_posted:
                    dt = j.source_published_at or j.first_seen_at
                    if dt:
                        last_posted = dt.isoformat()
            else:
                stale_count += 1

        top_categories = [
            {"category": k, "count": v}
            for k, v in sorted(categories_map.items(), key=lambda x: x[1], reverse=True)
        ]

        summary = {
            "total_active_jobs": len(active_jobs),
            "entry_level_jobs": entry_level_count,
            "internship_jobs": internship_count,
            "experienced_jobs": max(0, len(active_jobs) - entry_level_count),
            "top_categories": top_categories,
            "top_locations": sorted(locations_set)[:8],
            "active_technologies": sorted(active_tech_set)[:25],
            "stale_or_expired_jobs": stale_count,
            "last_job_posted_at": last_posted,
        }

        return summary, active_jobs

    def get_or_create_company_intelligence(
        self,
        company_id: uuid.UUID,
        refresh: bool = False,
    ) -> CompanyIntelligence:
        """Retrieve existing intelligence or synthesize a fresh evidence-backed profile."""
        company = self.get_company_or_404(company_id)

        intel = self.db.execute(
            select(CompanyIntelligence).where(CompanyIntelligence.company_id == company_id)
        ).scalar_one_or_none()

        if intel and not refresh and not intel.is_stale:
            return intel

        # 1. Collect / Ingest Research Sources
        existing_sources = (
            self.db.execute(
                select(CompanyResearchSource)
                .where(CompanyResearchSource.company_id == company_id)
                .order_by(desc(CompanyResearchSource.retrieved_at))
            )
            .scalars()
            .all()
        )

        if not existing_sources or refresh:
            fetched_payloads = self.adapter.fetch_company_sources(
                website_url=company.website_url,
                careers_url=company.careers_url,
            )
            for p in fetched_payloads:
                # Deduplicate by content hash
                existing = self.db.execute(
                    select(CompanyResearchSource).where(
                        CompanyResearchSource.company_id == company_id,
                        CompanyResearchSource.content_hash == p.content_hash,
                    )
                ).scalar_one_or_none()

                if not existing:
                    new_src = CompanyResearchSource(
                        company_id=company_id,
                        source_type=p.source_type,
                        source_url=p.source_url,
                        title=p.title,
                        content_snippet=p.content_snippet,
                        raw_content=p.raw_content,
                        content_hash=p.content_hash,
                        retrieved_at=p.retrieved_at,
                        is_verified=True,
                    )
                    self.db.add(new_src)
            self.db.commit()

            # Reload sources
            existing_sources = (
                self.db.execute(
                    select(CompanyResearchSource)
                    .where(CompanyResearchSource.company_id == company_id)
                    .order_by(desc(CompanyResearchSource.retrieved_at))
                )
                .scalars()
                .all()
            )

        # Combine text for analysis
        combined_source_text = "\n\n".join(
            [f"{s.title}\n{s.raw_content or s.content_snippet or ''}" for s in existing_sources]
        )

        source_hash = (
            hashlib.sha256(combined_source_text.encode("utf-8")).hexdigest()
            if combined_source_text
            else None
        )

        # 2. Hiring intelligence from DB jobs
        hiring_summary, active_jobs = self.compute_hiring_summary(company_id)
        job_descriptions = [j.get("description", "") for j in active_jobs]

        # 3. Technology intelligence extraction
        tech_items = extract_technologies_with_evidence(
            official_sources_text=combined_source_text,
            job_descriptions=job_descriptions,
            company_tags=list(company.technology_tags or []),
        )

        # 4. Products, Services & Recent Developments
        industry_val = company.industry_tags[0] if company.industry_tags else company.category
        hq_val = (
            f"{company.headquarters_city}, {company.headquarters_country}"
            if company.headquarters_city and company.headquarters_country
            else (company.headquarters_city or company.headquarters_country or None)
        )

        products: list[dict[str, Any]] = []
        if company.description:
            products.append(
                {
                    "name": f"{company.name} Core Platform",
                    "description": company.description[:250],
                    "category": industry_val or "Technology",
                    "evidence_source": "Official company profile description",
                }
            )

        for src in existing_sources[:3]:
            if "about" in src.source_url.lower() or "product" in src.source_url.lower():
                products.append(
                    {
                        "name": src.title,
                        "description": (src.content_snippet or "")[:200],
                        "category": "Services & Offerings",
                        "evidence_source": src.source_url,
                    }
                )

        recent_developments: list[dict[str, Any]] = []
        for src in existing_sources:
            if src.source_type in ("news_release", "engineering_blog"):
                recent_developments.append(
                    {
                        "headline": src.title,
                        "summary": (src.content_snippet or "")[:200],
                        "source_url": src.source_url,
                        "date": src.retrieved_at.strftime("%Y-%m-%d"),
                    }
                )

        # 5. Locations
        locations: list[str] = []
        if hq_val:
            locations.append(hq_val)
        for loc in hiring_summary.get("top_locations", []):
            if loc not in locations:
                locations.append(loc)

        # 6. Size Evidence (Zero fabrication rule)
        size_band = company.size_band
        size_evidence = None
        if size_band:
            size_evidence = f"Reported in company profile as {size_band}"
        else:
            size_band = "Undisclosed"
            size_evidence = "No verified employee count publicly verified in indexed sources"

        overview = company.description or (
            f"{company.name} is a verified organization in "
            f"{industry_val or 'the technology industry'}. "
            f"Currently has {hiring_summary.get('total_active_jobs', 0)} "
            f"active engineering requisitions recorded."
        )

        if not intel:
            intel = CompanyIntelligence(
                company_id=company_id,
                overview=overview,
                industry_domain=industry_val,
                headquarters=hq_val,
                operating_locations=locations,
                website_url=company.website_url,
                careers_url=company.careers_url,
                products_and_services=products,
                technology_stack=tech_items,
                size_band=size_band,
                size_evidence=size_evidence,
                funding_ownership_info="Privately held / undisclosed funding"
                if not company.is_global
                else "Established global enterprise",
                recent_developments=recent_developments,
                hiring_summary=hiring_summary,
                source_content_hash=source_hash,
                last_researched_at=datetime.utcnow(),
                is_stale=False,
                provenance_sources_count=len(existing_sources),
            )
            self.db.add(intel)
        else:
            intel.overview = overview
            intel.industry_domain = industry_val
            intel.headquarters = hq_val
            intel.operating_locations = locations
            intel.website_url = company.website_url
            intel.careers_url = company.careers_url
            intel.products_and_services = products
            intel.technology_stack = tech_items
            intel.size_band = size_band
            intel.size_evidence = size_evidence
            intel.recent_developments = recent_developments
            intel.hiring_summary = hiring_summary
            intel.source_content_hash = source_hash
            intel.last_researched_at = datetime.utcnow()
            intel.is_stale = False
            intel.provenance_sources_count = len(existing_sources)

        self.db.commit()
        self.db.refresh(intel)
        return intel

    def get_candidate_fit(
        self,
        user: User,
        company_id: uuid.UUID,
        resume_version_id: Optional[uuid.UUID] = None,
    ) -> dict[str, Any]:
        """Assess candidate fit using verified resume skills and target preferences."""
        company = self.get_company_or_404(company_id)
        intel = self.get_or_create_company_intelligence(company_id)

        # Retrieve candidate skills from resume analysis
        candidate_skills: list[str] = []
        query = select(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id)
        if resume_version_id:
            query = query.where(ResumeAnalysis.version_id == resume_version_id)
        analysis = (
            self.db.execute(query.order_by(desc(ResumeAnalysis.created_at))).scalars().first()
        )

        if analysis and analysis.result:
            skills_dict = analysis.result.get("skills", {})
            supported = skills_dict.get("supported_skills", [])
            for s in supported:
                candidate_skills.append(s if isinstance(s, str) else s.get("name", ""))

        # Retrieve target role preferences
        pref = self.db.execute(
            select(UserMatchingPreference).where(UserMatchingPreference.user_id == user.id)
        ).scalar_one_or_none()

        target_roles: list[str] = []
        if pref and pref.target_role_families:
            target_roles = list(pref.target_role_families)

        # Get active jobs
        _, active_jobs = self.compute_hiring_summary(company_id)

        return evaluate_company_fit(
            company_id=company_id,
            company_name=company.name,
            company_technologies=intel.technology_stack,
            candidate_skills=candidate_skills,
            candidate_target_roles=target_roles,
            company_jobs=active_jobs,
        )

    def generate_research_report(
        self,
        user: User,
        company_id: uuid.UUID,
        req: CompanyResearchGenerateRequest,
    ) -> CompanyResearchReport:
        """Generate or retrieve cached structured company research report."""
        company = self.get_company_or_404(company_id)
        intel = self.get_or_create_company_intelligence(company_id, refresh=req.force_refresh)

        # Fit assessment
        candidate_fit = self.get_candidate_fit(
            user=user,
            company_id=company_id,
            resume_version_id=req.resume_version_id,
        )

        # Active jobs
        _, active_jobs = self.compute_hiring_summary(company_id)
        job_ids = [str(j["id"]) for j in active_jobs]

        # Sources
        sources = (
            self.db.execute(
                select(CompanyResearchSource)
                .where(CompanyResearchSource.company_id == company_id)
                .order_by(desc(CompanyResearchSource.retrieved_at))
            )
            .scalars()
            .all()
        )

        sources_list = [
            {
                "title": s.title,
                "source_url": s.source_url,
                "source_type": s.source_type,
                "content_snippet": s.content_snippet,
                "is_verified": s.is_verified,
            }
            for s in sources
        ]

        # Compute cache key
        candidate_skills = candidate_fit.get("matching_skills", []) + candidate_fit.get(
            "missing_or_gap_skills", []
        )
        cache_hash = compute_research_cache_hash(
            company_id=str(company_id),
            source_content_hash=intel.source_content_hash,
            candidate_skills=candidate_skills,
            job_ids=job_ids,
        )

        # Check existing cached report for this user
        if not req.force_refresh:
            cached_report = (
                self.db.execute(
                    select(CompanyResearchReport).where(
                        CompanyResearchReport.user_id == user.id,
                        CompanyResearchReport.company_id == company_id,
                        CompanyResearchReport.content_hash == cache_hash,
                    )
                )
                .scalars()
                .first()
            )

            if cached_report:
                logger.info("Returning cached company research report %s", cached_report.id)
                cached_report.is_cached = True
                return cached_report

        # Generate report
        sections, provider, model, is_fallback = AICompanyResearchReportEngine.generate_report(
            company_name=company.name,
            industry=intel.industry_domain,
            headquarters=intel.headquarters,
            locations=intel.operating_locations,
            website_url=intel.website_url,
            careers_url=intel.careers_url,
            technologies=intel.technology_stack,
            products=intel.products_and_services,
            recent_developments=intel.recent_developments,
            hiring_summary=intel.hiring_summary,
            active_jobs=active_jobs,
            candidate_fit=candidate_fit,
            sources=sources_list,
            size_band=intel.size_band,
            size_evidence=intel.size_evidence,
            funding_info=intel.funding_ownership_info,
            focus_areas=req.focus_areas,
        )

        report = CompanyResearchReport(
            company_id=company_id,
            user_id=user.id,
            report_title=f"Company Intelligence & Fit Report: {company.name}",
            sections=sections,
            candidate_fit=candidate_fit,
            source_evidence=sources_list,
            content_hash=cache_hash,
            provider=provider,
            model=model,
            is_cached=False,
            is_deterministic_fallback=is_fallback,
            metadata_json={"focus_areas": req.focus_areas or []},
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def list_user_reports(
        self,
        user: User,
        company_id: Optional[uuid.UUID] = None,
    ) -> list[CompanyResearchReport]:
        """List research reports generated by the user."""
        query = select(CompanyResearchReport).where(CompanyResearchReport.user_id == user.id)
        if company_id:
            query = query.where(CompanyResearchReport.company_id == company_id)
        return list(
            self.db.execute(query.order_by(desc(CompanyResearchReport.created_at))).scalars().all()
        )

    def get_report_or_404(
        self,
        user: User,
        report_id: uuid.UUID,
    ) -> CompanyResearchReport:
        """Get specific report scoped to user."""
        report = self.db.execute(
            select(CompanyResearchReport).where(
                CompanyResearchReport.id == report_id,
                CompanyResearchReport.user_id == user.id,
            )
        ).scalar_one_or_none()
        if not report:
            raise NotFoundError(f"Research report {report_id} not found")
        return report

    def list_sources(self, company_id: uuid.UUID) -> list[CompanyResearchSource]:
        """List public research documents/sources for a company."""
        return list(
            self.db.execute(
                select(CompanyResearchSource)
                .where(CompanyResearchSource.company_id == company_id)
                .order_by(desc(CompanyResearchSource.retrieved_at))
            )
            .scalars()
            .all()
        )
