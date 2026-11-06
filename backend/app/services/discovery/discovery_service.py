import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.core.job_utils import compute_canonical_url_hash, normalize_job_title
from app.core.url_validator import validate_safe_url
from app.models.company import Company, CompanySource, DiscoveryScanLog
from app.models.job import Job, JobSource, JobVerification
from app.models.user import User
from app.schemas.discovery import (
    DiscoveryBatchScanResult,
    DiscoveryOverviewResponse,
    DiscoveryScanLogResponse,
    DiscoveryScanResult,
    DiscoverySourceCreate,
    DiscoverySourceResponse,
    DiscoverySourceTestRequest,
    DiscoverySourceTestResponse,
    DiscoverySourceUpdate,
)
from app.services.discovery.adapters.registry import (
    ADAPTER_CLASSES,
    get_adapter,
    list_supported_adapters,
)


class JobDiscoveryService:
    """Core domain service for configuring, testing, and executing automated job discovery."""

    @classmethod
    def get_overview(cls, db: Session) -> DiscoveryOverviewResponse:
        """Calculate high-level KPI overview for the discovery workspace."""
        total_sources = (
            db.query(func.count(CompanySource.id))
            .filter(CompanySource.adapter_name.isnot(None))
            .scalar()
            or 0
        )
        total_active_sources = (
            db.query(func.count(CompanySource.id))
            .filter(
                CompanySource.adapter_name.isnot(None),
                CompanySource.is_enabled.is_(True),
            )
            .scalar()
            or 0
        )
        sources_scanned = (
            db.query(func.count(CompanySource.id))
            .filter(
                CompanySource.adapter_name.isnot(None),
                CompanySource.last_successful_scan_at.isnot(None),
            )
            .scalar()
            or 0
        )

        scan_sums = db.query(
            func.sum(DiscoveryScanLog.jobs_imported),
            func.sum(DiscoveryScanLog.jobs_updated),
        ).first()
        new_jobs = int(scan_sums[0] or 0) if scan_sums else 0
        updated_jobs = int(scan_sums[1] or 0) if scan_sums else 0

        failed_scans = (
            db.query(func.count(DiscoveryScanLog.id))
            .filter(DiscoveryScanLog.status == "failed")
            .scalar()
            or 0
        )

        last_run = db.query(func.max(DiscoveryScanLog.started_at)).scalar()

        return DiscoveryOverviewResponse(
            total_sources=total_sources,
            total_active_sources=total_active_sources,
            sources_scanned=sources_scanned,
            new_jobs_discovered=new_jobs,
            updated_jobs=updated_jobs,
            failed_source_scans=failed_scans,
            last_discovery_run=last_run,
            supported_adapters=list_supported_adapters(),
        )

    @classmethod
    def list_sources(
        cls,
        db: Session,
        company_id: Optional[uuid.UUID] = None,
        adapter_name: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[DiscoverySourceResponse], int]:
        """Fetch paginated company sources configured for automated discovery."""
        query = db.query(CompanySource).join(Company, CompanySource.company_id == Company.id)

        if company_id:
            query = query.filter(CompanySource.company_id == company_id)
        if adapter_name:
            query = query.filter(CompanySource.adapter_name == adapter_name.lower())
        if is_enabled is not None:
            query = query.filter(CompanySource.is_enabled == is_enabled)

        total = query.count()
        sources = query.order_by(CompanySource.updated_at.desc()).offset(skip).limit(limit).all()

        results: list[DiscoverySourceResponse] = []
        for src in sources:
            resp = DiscoverySourceResponse.model_validate(src)
            resp.company_name = src.company.name if src.company else None
            results.append(resp)

        return results, total

    @classmethod
    def get_source_detail(
        cls,
        db: Session,
        source_id: uuid.UUID,
    ) -> DiscoverySourceResponse:
        """Retrieve a discovery source by ID."""
        src = db.query(CompanySource).filter(CompanySource.id == source_id).first()
        if not src:
            raise NotFoundError("Discovery source not found")
        resp = DiscoverySourceResponse.model_validate(src)
        resp.company_name = src.company.name if src.company else None
        return resp

    @classmethod
    def create_source(
        cls,
        db: Session,
        user: User,
        data: DiscoverySourceCreate,
    ) -> DiscoverySourceResponse:
        """Register a new discovery source for a company."""
        # 1. Verify company
        comp = (
            db.query(Company)
            .filter(Company.id == data.company_id, Company.is_merged.is_(False))
            .first()
        )
        if not comp:
            raise BadRequestError("Target company does not exist or has been merged")

        # 2. Verify adapter name
        adapter_key = data.adapter_name.strip().lower()
        if adapter_key not in ADAPTER_CLASSES:
            valid_adapters = ", ".join(ADAPTER_CLASSES.keys())
            raise BadRequestError(
                f"Unsupported adapter '{data.adapter_name}'. Choose from: {valid_adapters}"
            )

        # 3. Validate URL if present
        source_url = None
        if data.source_url and data.source_url.strip():
            source_url = validate_safe_url(data.source_url.strip(), field_name="Source URL")

        now = datetime.now(timezone.utc)
        source = CompanySource(
            company_id=comp.id,
            source_name=data.source_name.strip(),
            source_type=data.source_type,
            adapter_name=adapter_key,
            source_url=source_url,
            board_token=data.board_token.strip().lower() if data.board_token else None,
            scan_frequency_hours=data.scan_frequency_hours,
            is_enabled=data.is_enabled,
            first_seen_at=now,
            last_checked_at=now,
            metadata_json=data.metadata_json or {},
        )

        db.add(source)
        db.commit()
        db.refresh(source)

        audit_service.record_event(
            action="discovery.source_created",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company_source",
            resource_id=str(source.id),
            metadata={
                "company_id": str(comp.id),
                "adapter_name": adapter_key,
                "source_name": source.source_name,
            },
        )

        resp = DiscoverySourceResponse.model_validate(source)
        resp.company_name = comp.name
        return resp

    @classmethod
    def update_source(
        cls,
        db: Session,
        user: User,
        source_id: uuid.UUID,
        data: DiscoverySourceUpdate,
    ) -> DiscoverySourceResponse:
        """Update an existing discovery source."""
        source = db.query(CompanySource).filter(CompanySource.id == source_id).first()
        if not source:
            raise NotFoundError("Discovery source not found")

        update_dict = data.model_dump(exclude_unset=True)

        if "adapter_name" in update_dict and update_dict["adapter_name"]:
            adapter_key = update_dict["adapter_name"].strip().lower()
            if adapter_key not in ADAPTER_CLASSES:
                raise BadRequestError(f"Unsupported adapter '{adapter_key}'")
            source.adapter_name = adapter_key

        if "source_name" in update_dict and update_dict["source_name"]:
            source.source_name = update_dict["source_name"].strip()

        if "source_url" in update_dict:
            raw_url = update_dict["source_url"]
            source.source_url = (
                validate_safe_url(raw_url.strip(), field_name="Source URL")
                if raw_url and raw_url.strip()
                else None
            )

        if "board_token" in update_dict:
            token = update_dict["board_token"]
            source.board_token = token.strip().lower() if token and token.strip() else None

        if "scan_frequency_hours" in update_dict and update_dict["scan_frequency_hours"]:
            source.scan_frequency_hours = update_dict["scan_frequency_hours"]

        if "is_enabled" in update_dict:
            source.is_enabled = bool(update_dict["is_enabled"])

        if "metadata_json" in update_dict and update_dict["metadata_json"]:
            source.metadata_json = update_dict["metadata_json"]

        source.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(source)

        audit_service.record_event(
            action="discovery.source_updated",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company_source",
            resource_id=str(source.id),
            metadata={"updated_fields": list(update_dict.keys())},
        )

        resp = DiscoverySourceResponse.model_validate(source)
        resp.company_name = source.company.name if source.company else None
        return resp

    @classmethod
    def delete_source(
        cls,
        db: Session,
        user: User,
        source_id: uuid.UUID,
    ) -> None:
        """Remove a discovery source record."""
        source = db.query(CompanySource).filter(CompanySource.id == source_id).first()
        if not source:
            raise NotFoundError("Discovery source not found")

        db.delete(source)
        db.commit()

        audit_service.record_event(
            action="discovery.source_deleted",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="company_source",
            resource_id=str(source_id),
            metadata={"source_name": source.source_name},
        )

    @classmethod
    def test_source(cls, data: DiscoverySourceTestRequest) -> DiscoverySourceTestResponse:
        """Test source connectivity and preview detected opportunities before saving."""
        adapter = get_adapter(data.adapter_name)
        is_success, msg, count = adapter.test_connection(
            source_url=data.source_url,
            board_token=data.board_token,
        )

        samples: list[dict[str, Any]] = []
        if is_success:
            try:
                jobs = adapter.fetch_jobs(
                    source_url=data.source_url,
                    board_token=data.board_token,
                )
                for j in jobs[:3]:
                    samples.append(
                        {
                            "title": j.title,
                            "location": j.location_text,
                            "role_family": j.role_family,
                            "seniority": j.seniority_level,
                            "skills": j.skills_tags[:5],
                            "url": j.job_url,
                        }
                    )
            except Exception:
                pass

        return DiscoverySourceTestResponse(
            is_success=is_success,
            message=msg,
            jobs_detected=count,
            sample_jobs=samples,
        )

    @classmethod
    def scan_source(
        cls,
        db: Session,
        source_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        scan_type: str = "manual",
    ) -> DiscoveryScanResult:
        """Execute discovery scan for a source, normalizing and ingesting opportunities."""
        source = db.query(CompanySource).filter(CompanySource.id == source_id).first()
        if not source:
            raise NotFoundError("Discovery source not found")

        company = source.company
        company_name = company.name if company else source.source_name
        adapter_name = source.adapter_name or "unknown"

        started_at = datetime.now(timezone.utc)
        start_mono = time.monotonic()

        jobs_found = 0
        jobs_imported = 0
        jobs_updated = 0
        scan_status = "success"
        error_msg: Optional[str] = None

        try:
            adapter = get_adapter(adapter_name)
            discovered_jobs = adapter.fetch_jobs(
                source_url=source.source_url,
                board_token=source.board_token,
            )
            jobs_found = len(discovered_jobs)
            now = datetime.now(timezone.utc)

            for dj in discovered_jobs:
                canon_hash = compute_canonical_url_hash(dj.job_url)

                # Deduplication checks
                existing_job: Optional[Job] = None
                if canon_hash:
                    existing_job = (
                        db.query(Job).filter(Job.canonical_url_hash == canon_hash).first()
                    )

                if not existing_job and dj.external_source_id:
                    existing_job = (
                        db.query(Job)
                        .filter(
                            Job.company_id == source.company_id,
                            Job.external_source_id == dj.external_source_id,
                        )
                        .first()
                    )

                if not existing_job and source.company_id:
                    norm_title = normalize_job_title(dj.title)
                    existing_job = (
                        db.query(Job)
                        .filter(
                            Job.company_id == source.company_id,
                            Job.normalized_title == norm_title,
                            Job.job_status != "closed",
                        )
                        .first()
                    )

                if existing_job:
                    # Idempotent update: refresh timestamps and re-activate if necessary
                    existing_job.last_seen_at = now
                    existing_job.last_checked_at = now
                    if existing_job.job_status == "closed":
                        existing_job.job_status = "active"

                    # Update missing fields without overwriting user data
                    if not existing_job.location_text and dj.location_text:
                        existing_job.location_text = dj.location_text
                    if not existing_job.skills_tags and dj.skills_tags:
                        existing_job.skills_tags = dj.skills_tags
                    if not existing_job.role_family and dj.role_family:
                        existing_job.role_family = dj.role_family

                    # Ensure JobSource citation is recorded
                    src_exists = (
                        db.query(JobSource)
                        .filter(
                            JobSource.job_id == existing_job.id,
                            JobSource.source_name == source.source_name,
                        )
                        .first()
                    )
                    if not src_exists:
                        db.add(
                            JobSource(
                                job_id=existing_job.id,
                                source_name=source.source_name,
                                source_type=source.source_type,
                                source_url=source.source_url or dj.job_url,
                                external_id=dj.external_source_id,
                                evidence_summary=f"Re-observed via automated {adapter_name} scan.",
                                first_seen_at=now,
                                last_seen_at=now,
                            )
                        )
                    jobs_updated += 1
                else:
                    # Ingest new job opportunity
                    norm_title = normalize_job_title(dj.title)
                    new_job = Job(
                        company_id=source.company_id,
                        title=dj.title.strip(),
                        normalized_title=norm_title,
                        description=dj.description.strip(),
                        employment_type=dj.employment_type,
                        seniority_level=dj.seniority_level,
                        work_arrangement=dj.work_arrangement,
                        location_text=dj.location_text,
                        city=dj.city,
                        state_province=dj.state_province,
                        country=dj.country,
                        remote_eligibility_regions=dj.remote_eligibility_regions,
                        skills_tags=dj.skills_tags,
                        role_family=dj.role_family,
                        salary_min=dj.salary_min,
                        salary_max=dj.salary_max,
                        salary_currency=dj.salary_currency,
                        salary_period=dj.salary_period,
                        job_url=dj.job_url,
                        application_url=dj.application_url or dj.job_url,
                        external_source_id=dj.external_source_id,
                        canonical_url_hash=canon_hash,
                        source_published_at=dj.source_published_at or now,
                        first_seen_at=now,
                        last_seen_at=now,
                        last_checked_at=now,
                        job_status="active",
                        verification_status="corroborated",
                        verification_notes=f"Ingested from {adapter_name} career board.",
                        last_verified_at=now,
                        is_global=True,
                        created_by_user_id=user_id,
                        metadata_json={
                            "discovery_source_id": str(source.id),
                            "adapter_name": adapter_name,
                            "raw_metadata": dj.raw_metadata,
                        },
                    )
                    db.add(new_job)
                    db.flush()  # Obtain new_job.id

                    # Attach JobSource provenance
                    db.add(
                        JobSource(
                            job_id=new_job.id,
                            source_name=source.source_name,
                            source_type=source.source_type,
                            source_url=source.source_url or dj.job_url,
                            external_id=dj.external_source_id,
                            evidence_summary=f"Discovered via automated {adapter_name} scan.",
                            first_seen_at=now,
                            last_seen_at=now,
                        )
                    )

                    # Add verification audit entry
                    db.add(
                        JobVerification(
                            job_id=new_job.id,
                            verifier_type="system",
                            evidence_type="careers_page",
                            evidence_url=dj.job_url,
                            evidence_summary=f"Automated {adapter_name} scan confirmed listing.",
                            observed_status="active",
                            verification_outcome="corroborated",
                            reason=f"Retrieved from verified {company_name} career source.",
                            checked_at=now,
                        )
                    )

                    jobs_imported += 1

            # Update source record
            source.last_successful_scan_at = now
            source.last_scan_status = "success"
            msg_str = (
                f"Discovered {jobs_imported} new, {jobs_updated} updated "
                f"({jobs_found} total in feed)."
            )
            source.last_scan_message = msg_str
            source.jobs_discovered_count += jobs_imported
            source.last_checked_at = now

        except Exception as exc:
            scan_status = "failed"
            error_msg = str(exc)
            source.last_scan_status = "failed"
            source.last_scan_message = f"Scan failed: {error_msg}"
            source.error_count += 1
            source.last_checked_at = datetime.now(timezone.utc)

        duration = time.monotonic() - start_mono
        completed_at = datetime.now(timezone.utc)

        # Record scan audit log
        log_entry = DiscoveryScanLog(
            company_source_id=source.id,
            company_id=source.company_id,
            adapter_name=adapter_name,
            scan_type=scan_type,
            status=scan_status,
            jobs_found=jobs_found,
            jobs_imported=jobs_imported,
            jobs_updated=jobs_updated,
            error_message=error_msg,
            started_at=started_at,
            completed_at=completed_at,
            metadata_json={"duration_seconds": round(duration, 2)},
        )
        db.add(log_entry)
        db.commit()

        if user_id:
            audit_service.record_event(
                action="discovery.source_scanned",
                actor_type="user",
                actor_id=str(user_id),
                resource_type="company_source",
                resource_id=str(source.id),
                metadata={
                    "status": scan_status,
                    "jobs_found": jobs_found,
                    "jobs_imported": jobs_imported,
                    "jobs_updated": jobs_updated,
                },
            )

        msg = (
            f"Successfully scanned '{source.source_name}': {jobs_imported} new, "
            f"{jobs_updated} updated ({jobs_found} found in feed)."
            if scan_status == "success"
            else f"Scan failed for '{source.source_name}': {error_msg}"
        )

        return DiscoveryScanResult(
            source_id=source.id,
            company_name=company_name,
            adapter_name=adapter_name,
            status=scan_status,
            jobs_found=jobs_found,
            jobs_imported=jobs_imported,
            jobs_updated=jobs_updated,
            message=msg,
            duration_seconds=round(duration, 2),
        )

    @classmethod
    def scan_all_sources(
        cls,
        db: Session,
        only_due: bool = False,
        user_id: Optional[uuid.UUID] = None,
    ) -> DiscoveryBatchScanResult:
        """Scan all enabled discovery sources with failure isolation between sources."""
        now = datetime.now(timezone.utc)
        query = db.query(CompanySource).filter(
            CompanySource.adapter_name.isnot(None),
            CompanySource.is_enabled.is_(True),
        )

        sources = query.all()
        due_sources: list[CompanySource] = []

        for s in sources:
            if not only_due:
                due_sources.append(s)
                continue
            if not s.last_successful_scan_at:
                due_sources.append(s)
                continue
            # Check elapsed hours against scan_frequency_hours
            freq = s.scan_frequency_hours or 24
            last_dt = s.last_successful_scan_at
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            if last_dt + timedelta(hours=freq) <= now:
                due_sources.append(s)

        results: list[DiscoveryScanResult] = []
        total_found = 0
        total_imported = 0
        total_updated = 0
        failed_count = 0

        for src in due_sources:
            try:
                res = cls.scan_source(
                    db=db,
                    source_id=src.id,
                    user_id=user_id,
                    scan_type="batch" if not only_due else "scheduled",
                )
                results.append(res)
                total_found += res.jobs_found
                total_imported += res.jobs_imported
                total_updated += res.jobs_updated
                if res.status != "success":
                    failed_count += 1
            except Exception as exc:
                failed_count += 1
                results.append(
                    DiscoveryScanResult(
                        source_id=src.id,
                        company_name=src.company.name if src.company else src.source_name,
                        adapter_name=src.adapter_name or "unknown",
                        status="failed",
                        jobs_found=0,
                        jobs_imported=0,
                        jobs_updated=0,
                        message=f"Unhandled error during scan: {exc}",
                        duration_seconds=0.0,
                    )
                )

        if user_id:
            audit_service.record_event(
                action="discovery.batch_scanned",
                actor_type="user",
                actor_id=str(user_id),
                resource_type="system",
                resource_id="batch_scan",
                metadata={
                    "sources_scanned": len(due_sources),
                    "total_imported": total_imported,
                    "total_updated": total_updated,
                    "failed_count": failed_count,
                },
            )

        return DiscoveryBatchScanResult(
            sources_scanned=len(due_sources),
            total_jobs_found=total_found,
            total_jobs_imported=total_imported,
            total_jobs_updated=total_updated,
            failed_sources=failed_count,
            results=results,
        )

    @classmethod
    def get_scan_logs(
        cls,
        db: Session,
        source_id: Optional[uuid.UUID] = None,
        company_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> tuple[list[DiscoveryScanLogResponse], int]:
        """Retrieve audit history logs of discovery scans."""
        query = db.query(DiscoveryScanLog).outerjoin(
            Company, DiscoveryScanLog.company_id == Company.id
        )

        if source_id:
            query = query.filter(DiscoveryScanLog.company_source_id == source_id)
        if company_id:
            query = query.filter(DiscoveryScanLog.company_id == company_id)

        total = query.count()
        logs = query.order_by(DiscoveryScanLog.started_at.desc()).offset(skip).limit(limit).all()

        results: list[DiscoveryScanLogResponse] = []
        for log_entry in logs:
            resp = DiscoveryScanLogResponse.model_validate(log_entry)
            resp.company_name = log_entry.company.name if log_entry.company else None
            if log_entry.completed_at and log_entry.started_at:
                st = (
                    log_entry.started_at
                    if log_entry.started_at.tzinfo
                    else log_entry.started_at.replace(tzinfo=timezone.utc)
                )
                ct = (
                    log_entry.completed_at
                    if log_entry.completed_at.tzinfo
                    else log_entry.completed_at.replace(tzinfo=timezone.utc)
                )
                resp.duration_seconds = round((ct - st).total_seconds(), 2)
            results.append(resp)

        return results, total
