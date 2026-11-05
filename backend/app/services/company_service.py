import math
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String as SAString
from sqlalchemy import cast, or_
from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.url_validator import extract_normalized_domain, normalize_company_name
from app.models.company import Company, CompanySource
from app.models.user import User
from app.schemas.company import (
    CompanyCreate,
    CompanyDetailResponse,
    CompanyDuplicateCheckResponse,
    CompanyDuplicateMatch,
    CompanyListResponse,
    CompanyResponse,
    CompanySourceCreate,
    CompanySourceResponse,
    CompanySourceUpdate,
    CompanyUpdate,
    CompanyVerifyRequest,
)


class CompanyService:
    """Business logic for company discovery, curation, provenance, and deduplication."""

    @staticmethod
    def _check_manage_permission(company: Company, user: User) -> None:
        """Verify user is authorized to modify or manage this company record."""
        if user.is_superuser:
            return
        if company.is_global and company.created_by_user_id != user.id:
            raise ForbiddenError("Global curated company records can only be managed by admins")
        if company.created_by_user_id is not None and company.created_by_user_id != user.id:
            raise ForbiddenError("You do not have permission to manage this company record")

    @staticmethod
    def _format_company_response(company: Company) -> CompanyResponse:
        """Map Company model to CompanyResponse with computed sources count."""
        sources_count = len(company.sources) if company.sources else 0
        return CompanyResponse(
            id=company.id,
            name=company.name,
            normalized_name=company.normalized_name,
            website_url=company.website_url,
            normalized_domain=company.normalized_domain,
            category=company.category,  # type: ignore[arg-type]
            headquarters_country=company.headquarters_country,
            headquarters_city=company.headquarters_city,
            operating_regions=company.operating_regions or [],
            industry_tags=company.industry_tags or [],
            technology_tags=company.technology_tags or [],
            size_band=company.size_band,
            careers_url=company.careers_url,
            description=company.description,
            primary_source=company.primary_source,
            primary_source_url=company.primary_source_url,
            verification_status=company.verification_status,  # type: ignore[arg-type]
            verification_notes=company.verification_notes,
            last_verified_at=company.last_verified_at,
            created_by_user_id=company.created_by_user_id,
            is_global=company.is_global,
            is_merged=company.is_merged,
            merged_into_company_id=company.merged_into_company_id,
            metadata_json=company.metadata_json or {},
            created_at=company.created_at,
            updated_at=company.updated_at,
            sources_count=sources_count,
        )

    @classmethod
    def list_companies(
        cls,
        db: Session,
        search: Optional[str] = None,
        category: Optional[str] = None,
        verification_status: Optional[str] = None,
        industry: Optional[str] = None,
        technology: Optional[str] = None,
        region: Optional[str] = None,
        user_only: bool = False,
        current_user: Optional[User] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> CompanyListResponse:
        """Retrieve paginated and filtered company records."""
        query = db.query(Company).filter(Company.is_merged.is_(False))

        if user_only and current_user:
            query = query.filter(Company.created_by_user_id == current_user.id)

        if category:
            query = query.filter(Company.category == category)

        if verification_status:
            query = query.filter(Company.verification_status == verification_status)

        if search and search.strip():
            term = f"%{search.strip()}%"
            norm_term = f"%{normalize_company_name(search.strip())}%"
            query = query.filter(
                or_(
                    Company.name.ilike(term),
                    Company.normalized_name.ilike(norm_term),
                    Company.normalized_domain.ilike(term),
                    Company.headquarters_city.ilike(term),
                    Company.headquarters_country.ilike(term),
                    Company.description.ilike(term),
                )
            )

        if region and region.strip():
            reg_term = f"%{region.strip()}%"
            query = query.filter(
                or_(
                    Company.headquarters_country.ilike(reg_term),
                    Company.headquarters_city.ilike(reg_term),
                    cast(Company.operating_regions, SAString).ilike(reg_term),
                )
            )

        if industry and industry.strip():
            ind_term = f"%{industry.strip()}%"
            query = query.filter(cast(Company.industry_tags, SAString).ilike(ind_term))

        if technology and technology.strip():
            tech_term = f"%{technology.strip()}%"
            query = query.filter(cast(Company.technology_tags, SAString).ilike(tech_term))

        total = query.count()
        safe_per_page = max(1, min(per_page, 100))
        total_pages = math.ceil(total / safe_per_page) if total > 0 else 1
        safe_page = max(1, min(page, max(1, total_pages)))

        records = (
            query.order_by(Company.name.asc())
            .offset((safe_page - 1) * safe_per_page)
            .limit(safe_per_page)
            .all()
        )

        items = [cls._format_company_response(c) for c in records]
        return CompanyListResponse(
            items=items,
            total=total,
            page=safe_page,
            per_page=safe_per_page,
            total_pages=total_pages,
        )

    @classmethod
    def check_duplicates(
        cls,
        db: Session,
        name: str,
        website_url: Optional[str] = None,
    ) -> CompanyDuplicateCheckResponse:
        """Scan active company records for potential duplicate matches by name or domain."""
        norm_name = normalize_company_name(name)
        norm_domain = extract_normalized_domain(website_url)

        matches: list[CompanyDuplicateMatch] = []
        seen_ids: set[uuid.UUID] = set()

        if norm_domain:
            domain_matches = (
                db.query(Company)
                .filter(
                    Company.is_merged.is_(False),
                    Company.normalized_domain == norm_domain,
                )
                .all()
            )
            for dm in domain_matches:
                seen_ids.add(dm.id)
                matches.append(
                    CompanyDuplicateMatch(
                        company=cls._format_company_response(dm),
                        confidence="high",
                        reason=f"Identical domain: {norm_domain}",
                    )
                )

        if norm_name:
            name_matches = (
                db.query(Company)
                .filter(
                    Company.is_merged.is_(False),
                    Company.normalized_name == norm_name,
                )
                .all()
            )
            for nm in name_matches:
                if nm.id not in seen_ids:
                    seen_ids.add(nm.id)
                    matches.append(
                        CompanyDuplicateMatch(
                            company=cls._format_company_response(nm),
                            confidence="medium",
                            reason=f"Matching normalized name: '{norm_name}'",
                        )
                    )

        return CompanyDuplicateCheckResponse(
            normalized_name=norm_name,
            normalized_domain=norm_domain,
            matches=matches,
        )

    @classmethod
    def create_company(
        cls,
        db: Session,
        user: User,
        data: CompanyCreate,
    ) -> CompanyDetailResponse:
        """Register a new company and optional initial discovery source."""
        norm_name = normalize_company_name(data.name)
        norm_domain = extract_normalized_domain(data.website_url)

        company = Company(
            name=data.name.strip(),
            normalized_name=norm_name,
            website_url=data.website_url,
            normalized_domain=norm_domain,
            category=data.category,
            headquarters_country=data.headquarters_country,
            headquarters_city=data.headquarters_city,
            operating_regions=data.operating_regions,
            industry_tags=data.industry_tags,
            technology_tags=data.technology_tags,
            size_band=data.size_band,
            careers_url=data.careers_url,
            description=data.description,
            primary_source=data.initial_source.source_name if data.initial_source else "User Entry",
            primary_source_url=(
                data.initial_source.source_url if data.initial_source else data.careers_url
            ),
            verification_status="unverified",
            created_by_user_id=user.id,
            is_global=user.is_superuser,
            is_merged=False,
        )

        db.add(company)
        db.flush()

        # Add initial discovery source provenance
        if data.initial_source:
            init_src = CompanySource(
                company_id=company.id,
                source_name=data.initial_source.source_name,
                source_type=data.initial_source.source_type,
                source_url=data.initial_source.source_url,
                evidence_summary=data.initial_source.evidence_summary,
                metadata_json=data.initial_source.metadata_json,
            )
            db.add(init_src)
        else:
            default_src = CompanySource(
                company_id=company.id,
                source_name=f"User Addition ({user.full_name})",
                source_type="user_added",
                source_url=data.careers_url or data.website_url,
                evidence_summary="Manual company creation submission.",
            )
            db.add(default_src)

        db.commit()
        db.refresh(company)

        # Audit emission
        audit_service.record_event(
            action="company.created",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company",
            resource_id=str(company.id),
            metadata={
                "company_name": company.name,
                "category": company.category,
                "domain": company.normalized_domain,
            },
        )

        return cls.get_company_detail(db, company.id)

    @classmethod
    def get_company_detail(
        cls,
        db: Session,
        company_id: uuid.UUID,
    ) -> CompanyDetailResponse:
        """Fetch detailed company profile and full discovery sources."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise NotFoundError("Company record not found")

        formatted_sources = [
            CompanySourceResponse.model_validate(s) for s in (company.sources or [])
        ]
        resp_base = cls._format_company_response(company)
        return CompanyDetailResponse(
            **resp_base.model_dump(),
            sources=formatted_sources,
        )

    @classmethod
    def update_company(
        cls,
        db: Session,
        user: User,
        company_id: uuid.UUID,
        data: CompanyUpdate,
    ) -> CompanyDetailResponse:
        """Update company metadata with authorization enforcement."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise NotFoundError("Company record not found")

        cls._check_manage_permission(company, user)

        update_dict = data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"]:
            company.name = update_dict["name"].strip()
            company.normalized_name = normalize_company_name(company.name)

        if "website_url" in update_dict:
            company.website_url = update_dict["website_url"]
            company.normalized_domain = extract_normalized_domain(company.website_url)

        for field in [
            "category",
            "careers_url",
            "headquarters_country",
            "headquarters_city",
            "operating_regions",
            "industry_tags",
            "technology_tags",
            "size_band",
            "description",
        ]:
            if field in update_dict:
                setattr(company, field, update_dict[field])

        db.commit()
        db.refresh(company)

        audit_service.record_event(
            action="company.updated",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company",
            resource_id=str(company.id),
            metadata={"updated_fields": list(update_dict.keys())},
        )

        return cls.get_company_detail(db, company.id)

    @classmethod
    def verify_company(
        cls,
        db: Session,
        user: User,
        company_id: uuid.UUID,
        data: CompanyVerifyRequest,
    ) -> CompanyDetailResponse:
        """Update company verification status; requires evidence notes for verified states."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise NotFoundError("Company record not found")

        cls._check_manage_permission(company, user)

        if data.verification_status in {"verified", "corroborated"} and (
            not data.verification_notes or len(data.verification_notes.strip()) < 5
        ):
            raise BadRequestError(
                "Verification notes with concrete evidence rationale are required"
            )

        company.verification_status = data.verification_status
        company.verification_notes = data.verification_notes.strip()
        company.last_verified_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(company)

        audit_service.record_event(
            action="company.verified",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company",
            resource_id=str(company.id),
            metadata={
                "status": data.verification_status,
                "evidence_length": len(data.verification_notes),
            },
        )

        return cls.get_company_detail(db, company.id)

    @classmethod
    def add_source(
        cls,
        db: Session,
        user: User,
        company_id: uuid.UUID,
        data: CompanySourceCreate,
    ) -> CompanySourceResponse:
        """Attach a new discovery provenance source to a company."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise NotFoundError("Company record not found")

        cls._check_manage_permission(company, user)

        source = CompanySource(
            company_id=company.id,
            source_name=data.source_name.strip(),
            source_type=data.source_type,
            source_url=data.source_url,
            evidence_summary=data.evidence_summary,
            metadata_json=data.metadata_json,
        )

        db.add(source)
        db.commit()
        db.refresh(source)

        audit_service.record_event(
            action="company.source_added",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company_source",
            resource_id=str(source.id),
            metadata={"company_id": str(company.id), "source_type": source.source_type},
        )

        return CompanySourceResponse.model_validate(source)

    @classmethod
    def update_source(
        cls,
        db: Session,
        user: User,
        company_id: uuid.UUID,
        source_id: uuid.UUID,
        data: CompanySourceUpdate,
    ) -> CompanySourceResponse:
        """Update an existing provenance source."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise NotFoundError("Company record not found")

        cls._check_manage_permission(company, user)

        source = (
            db.query(CompanySource)
            .filter(
                CompanySource.id == source_id,
                CompanySource.company_id == company_id,
            )
            .first()
        )
        if not source:
            raise NotFoundError("Company source record not found")

        update_dict = data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field == "source_name" and value:
                source.source_name = value.strip()
            elif field != "source_name":
                setattr(source, field, value)

        source.last_checked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(source)

        audit_service.record_event(
            action="company.source_updated",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company_source",
            resource_id=str(source.id),
            metadata={"company_id": str(company.id)},
        )

        return CompanySourceResponse.model_validate(source)

    @classmethod
    def delete_source(
        cls,
        db: Session,
        user: User,
        company_id: uuid.UUID,
        source_id: uuid.UUID,
    ) -> None:
        """Remove a discovery provenance source."""
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise NotFoundError("Company record not found")

        cls._check_manage_permission(company, user)

        source = (
            db.query(CompanySource)
            .filter(
                CompanySource.id == source_id,
                CompanySource.company_id == company_id,
            )
            .first()
        )
        if not source:
            raise NotFoundError("Company source record not found")

        db.delete(source)
        db.commit()

        audit_service.record_event(
            action="company.source_deleted",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company_source",
            resource_id=str(source_id),
            metadata={"company_id": str(company.id)},
        )

    @classmethod
    def merge_companies(
        cls,
        db: Session,
        user: User,
        target_company_id: uuid.UUID,
        secondary_company_id: uuid.UUID,
        merge_reason: str,
    ) -> CompanyDetailResponse:
        """Explicitly merge a duplicate secondary company into a target company."""
        if target_company_id == secondary_company_id:
            raise BadRequestError("Cannot merge a company into itself")

        target = db.query(Company).filter(Company.id == target_company_id).first()
        if not target:
            raise NotFoundError("Target company record not found")

        secondary = db.query(Company).filter(Company.id == secondary_company_id).first()
        if not secondary:
            raise NotFoundError("Secondary company record not found")

        if target.is_merged:
            raise ConflictError("Target company has already been merged into another record")
        if secondary.is_merged:
            raise ConflictError("Secondary company has already been merged")

        # User must have permission to manage both companies
        cls._check_manage_permission(target, user)
        cls._check_manage_permission(secondary, user)

        # 1. Transfer discovery sources from secondary to target
        sources_to_move = (
            db.query(CompanySource).filter(CompanySource.company_id == secondary.id).all()
        )
        for src in sources_to_move:
            src.company_id = target.id
            src.evidence_summary = (
                f"{src.evidence_summary or ''} [Transferred via merge from '{secondary.name}']"
            ).strip()

        # 2. Enrich target attributes if missing
        if not target.website_url and secondary.website_url:
            target.website_url = secondary.website_url
            target.normalized_domain = secondary.normalized_domain

        if not target.careers_url and secondary.careers_url:
            target.careers_url = secondary.careers_url

        if not target.description and secondary.description:
            target.description = secondary.description

        if not target.headquarters_city and secondary.headquarters_city:
            target.headquarters_city = secondary.headquarters_city

        if not target.headquarters_country and secondary.headquarters_country:
            target.headquarters_country = secondary.headquarters_country

        if not target.size_band and secondary.size_band:
            target.size_band = secondary.size_band

        # Merge tags without duplicates
        existing_ind = set(target.industry_tags or [])
        target.industry_tags = list(existing_ind.union(secondary.industry_tags or []))

        existing_tech = set(target.technology_tags or [])
        target.technology_tags = list(existing_tech.union(secondary.technology_tags or []))

        existing_reg = set(target.operating_regions or [])
        target.operating_regions = list(existing_reg.union(secondary.operating_regions or []))

        # 3. Mark secondary as merged
        secondary.is_merged = True
        secondary.merged_into_company_id = target.id
        secondary.verification_notes = (
            f"Merged into '{target.name}' ({target.id}). Reason: {merge_reason}"
        )

        db.commit()
        db.refresh(target)

        # 4. Emit auditable merge event
        audit_service.record_event(
            action="company.merged",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company",
            resource_id=str(target.id),
            metadata={
                "target_company_id": str(target.id),
                "target_company_name": target.name,
                "secondary_company_id": str(secondary.id),
                "secondary_company_name": secondary.name,
                "sources_transferred": len(sources_to_move),
                "merge_reason": merge_reason,
            },
        )

        return cls.get_company_detail(db, target.id)
