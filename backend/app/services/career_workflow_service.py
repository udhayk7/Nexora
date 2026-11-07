import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.application import ApplicationActivity, JobApplication
from app.models.assistant import ApplicationEmail, ApplicationPreparation, CoverLetter
from app.models.company import Company
from app.models.company_intelligence import CompanyIntelligence
from app.models.job import Job
from app.models.match import JobMatch, UserMatchingPreference
from app.models.recommendation import AIJobMatch
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.models.workflow import CareerWorkflowRun, CareerWorkflowStep
from app.schemas.match import JobMatchRunRequest
from app.schemas.workflow import (
    OnboardingConfirmRequest,
    OnboardingResultResponse,
    PreparationDetailResponse,
    UnifiedDiscoveryResponse,
    UnifiedOpportunityItem,
    WorkflowDashboardResponse,
    WorkflowRecommendedAction,
)
from app.services.assistant_service import AssistantService
from app.services.job_intelligence_service import JobIntelligenceService
from app.services.matching_service import MatchingService
from app.services.portfolio_service import PortfolioService

logger = logging.getLogger("nexora.services.career_workflow")

# Entry level keywords for deterministic classification
ENTRY_LEVEL_KEYWORDS = (
    "junior",
    "entry",
    "fresher",
    "graduate",
    "associate",
    "intern",
    "trainee",
    "sde 1",
    "sde i",
    "engineer 1",
    "engineer i",
    "software engineer i",
    "early career",
    "campus",
)

# Priority employer tier classifications
PRIORITY_COMPANY_TIERS = ("tier_1", "tier_2", "big_4", "product", "mnc", "gcc")


class CareerWorkflowService:
    """Unified Career Workflow Orchestrator.

    Connects candidate onboarding, job discovery, intelligent preparation,
    application execution with approval gates, and interview coaching.
    """

    # -------------------------------------------------------------------------
    # 1. Unified Candidate Onboarding Workflow
    # -------------------------------------------------------------------------

    @classmethod
    def start_onboarding_workflow(
        cls,
        db: Session,
        user: User,
        resume_id: Optional[uuid.UUID] = None,
        preferences_override: Optional[dict[str, Any]] = None,
    ) -> OnboardingResultResponse:
        """Execute end-to-end onboarding: extract candidate facts, infer preferences,

        update profiles, and initialize personalized job matching.
        """
        # Resolve target resume
        resume = None
        if resume_id:
            resume = (
                db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user.id).first()
            )
        if not resume:
            resume = (
                db.query(Resume)
                .filter(Resume.user_id == user.id)
                .order_by(Resume.created_at.desc())
                .first()
            )

        if not resume or not resume.current_version_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No resume found. Please upload a resume first to begin onboarding.",
            )

        version = (
            db.query(ResumeVersion).filter(ResumeVersion.id == resume.current_version_id).first()
        )
        if not version or not version.parsed_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Resume content has not been parsed yet. "
                    "Please try again after parsing completes."
                ),
            )

        # Create or update Workflow Run
        workflow_run = CareerWorkflowRun(
            user_id=user.id,
            workflow_type="onboarding",
            status="running",
            current_step="parsing_candidate",
            progress_pct=25,
            step_data={},
        )
        db.add(workflow_run)
        db.flush()

        parsed = version.parsed_content or {}
        contact = parsed.get("contact", {})
        skills = parsed.get("skills", [])
        experience = parsed.get("experience", [])
        education = parsed.get("education", [])
        summary = parsed.get("summary", "")

        # Infer suitable career roles from titles and skills
        extracted_roles = cls._infer_suitable_roles(experience, skills, summary)

        # Inferred preferences
        candidate_location = contact.get("location") or ""
        inferred_locations = [candidate_location] if candidate_location else ["Remote"]
        inferred_work_arrangements = ["remote", "hybrid", "on_site"]

        inferred_preferences = {
            "target_roles": extracted_roles,
            "preferred_locations": inferred_locations,
            "work_arrangement_preferences": inferred_work_arrangements,
            "min_salary": (preferences_override or {}).get("min_salary") or 400000.0,
            "salary_currency": (preferences_override or {}).get("salary_currency") or "INR",
            "seniority": "entry",
            "is_inferred": True,  # Clearly marks unverified AI inferences
        }

        # Step 1: Record step
        step1 = CareerWorkflowStep(
            workflow_run_id=workflow_run.id,
            step_name="extract_candidate_profile",
            step_order=1,
            status="completed",
            input_payload={"resume_id": str(resume.id), "version_id": str(version.id)},
            output_payload={
                "extracted_skills_count": len(skills),
                "extracted_roles": extracted_roles,
                "inferred_preferences": inferred_preferences,
            },
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(step1)

        # Step 2: Import into UserMatchingPreference
        workflow_run.current_step = "import_preferences"
        workflow_run.progress_pct = 50

        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if not pref:
            pref = UserMatchingPreference(
                user_id=user.id,
                target_role_families=extracted_roles,
                preferred_locations=inferred_locations,
                work_arrangement_preferences=inferred_work_arrangements,
                min_salary=inferred_preferences["min_salary"],
                salary_currency=inferred_preferences["salary_currency"],
                seniority_preferences=["entry", "junior"],
                preferred_skills=skills[:15],
                metadata_json={"onboarded_from_resume_id": str(resume.id)},
            )
            db.add(pref)
        else:
            if not pref.target_role_families:
                pref.target_role_families = extracted_roles
            if not pref.preferred_skills and skills:
                pref.preferred_skills = skills[:15]
            if not pref.preferred_locations and candidate_location:
                pref.preferred_locations = [candidate_location]
            pref.updated_at = datetime.now(timezone.utc)

        db.flush()

        # Bootstrap user portfolio profile if empty
        try:
            PortfolioService.get_or_create_portfolio(db, user)
        except Exception as e:
            logger.warning("Could not auto-initialize portfolio during onboarding: %s", e)

        # Step 3: Run matching & recommendations
        workflow_run.current_step = "initializing_job_matching"
        workflow_run.progress_pct = 75

        matching_jobs_count = 0
        top_matches_list: list[dict[str, Any]] = []

        try:
            req = JobMatchRunRequest(
                resume_id=resume.id,
                version_id=version.id,
                limit=50,
                min_score_threshold=30.0,
            )
            match_res = MatchingService.run_matching(
                db=db,
                user=user,
                request=req,
            )
            matching_jobs_count = match_res.matches_saved
            db_top_matches = (
                db.query(JobMatch)
                .filter(JobMatch.user_id == user.id, JobMatch.resume_id == resume.id)
                .order_by(JobMatch.match_score.desc())
                .limit(5)
                .all()
            )
            for m in db_top_matches:
                top_matches_list.append(
                    {
                        "job_id": str(m.job_id),
                        "job_title": m.job.title if m.job else "",
                        "company_name": m.job.company.name if (m.job and m.job.company) else "",
                        "match_score": m.match_score,
                    }
                )
        except Exception as exc:
            logger.warning("Matching calculation warning during onboarding: %s", exc)

        # Complete workflow run
        workflow_run.status = "completed"
        workflow_run.current_step = "onboarding_completed"
        workflow_run.progress_pct = 100
        workflow_run.step_data = {
            "extracted_roles": extracted_roles,
            "skills_count": len(skills),
            "matching_jobs_count": matching_jobs_count,
        }

        step2 = CareerWorkflowStep(
            workflow_run_id=workflow_run.id,
            step_name="initialize_job_matching",
            step_order=2,
            status="completed",
            input_payload={"resume_version_id": str(version.id)},
            output_payload={"matching_jobs_count": matching_jobs_count},
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(step2)
        db.commit()

        candidate_summary = {
            "name": contact.get("name") or user.full_name,
            "email": contact.get("email") or user.email,
            "phone": contact.get("phone"),
            "location": candidate_location,
            "skills_count": len(skills),
            "experience_items": len(experience),
            "education_items": len(education),
            "summary_preview": (summary[:150] + "...") if len(summary) > 150 else summary,
        }

        return OnboardingResultResponse(
            workflow_run_id=workflow_run.id,
            status="completed",
            candidate_summary=candidate_summary,
            extracted_roles=extracted_roles,
            extracted_skills=skills,
            inferred_preferences=inferred_preferences,
            matching_jobs_count=matching_jobs_count,
            top_matches=top_matches_list,
        )

    @classmethod
    def confirm_onboarding_review(
        cls,
        db: Session,
        user: User,
        data: OnboardingConfirmRequest,
    ) -> dict[str, Any]:
        """Update UserMatchingPreference with user's explicitly approved career preferences."""
        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if not pref:
            pref = UserMatchingPreference(
                user_id=user.id,
                target_role_families=data.target_roles,
                preferred_locations=data.preferred_locations,
                work_arrangement_preferences=data.work_arrangement_preferences,
                min_salary=data.min_salary,
                salary_currency=data.salary_currency or "INR",
                seniority_preferences=[data.seniority] if data.seniority else ["entry"],
                preferred_skills=data.technical_skills,
                metadata_json={"reviewed_by_candidate": True},
            )
            db.add(pref)
        else:
            if data.target_roles:
                pref.target_role_families = data.target_roles
            if data.preferred_locations:
                pref.preferred_locations = data.preferred_locations
            if data.work_arrangement_preferences:
                pref.work_arrangement_preferences = data.work_arrangement_preferences
            if data.min_salary is not None:
                pref.min_salary = data.min_salary
            if data.salary_currency:
                pref.salary_currency = data.salary_currency
            if data.seniority:
                pref.seniority_preferences = [data.seniority]
            if data.technical_skills:
                pref.preferred_skills = data.technical_skills
            pref.updated_at = datetime.now(timezone.utc)

        db.commit()
        return {
            "status": "success",
            "message": "Candidate career preferences confirmed and saved.",
            "target_roles": pref.target_role_families,
            "preferred_locations": pref.preferred_locations,
        }

    # -------------------------------------------------------------------------
    # 2. Unified Job Discovery & Prioritization
    # -------------------------------------------------------------------------

    @classmethod
    def get_unified_discovery(
        cls,
        db: Session,
        user: User,
        filter_entry_level: bool = True,
        prioritize_tiers: bool = True,
        limit: int = 50,
    ) -> UnifiedDiscoveryResponse:
        """Discover, rank, and explain relevant jobs from existing sources with

        entry-level detection, company tier prioritization, and verification audit.
        """
        # Fetch active jobs
        stmt = (
            select(Job)
            .outerjoin(Company, Job.company_id == Company.id)
            .where(Job.job_status == "active")
            .order_by(desc(Job.created_at))
            .limit(limit * 2)
        )
        jobs = db.execute(stmt).scalars().all()

        # Load existing match scores for this user
        matches_map: dict[uuid.UUID, JobMatch] = {}
        user_matches = db.query(JobMatch).filter(JobMatch.user_id == user.id).all()
        for m in user_matches:
            matches_map[m.job_id] = m

        # Load AI recommendations for this user
        ai_matches_map: dict[uuid.UUID, AIJobMatch] = {}
        ai_matches = db.query(AIJobMatch).filter(AIJobMatch.user_id == user.id).all()
        for am in ai_matches:
            ai_matches_map[am.job_id] = am

        # Load active resume skills
        user_skills: set[str] = set()
        latest_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user.id)
            .order_by(Resume.created_at.desc())
            .first()
        )
        if latest_resume and latest_resume.current_version_id:
            ver = (
                db.query(ResumeVersion)
                .filter(ResumeVersion.id == latest_resume.current_version_id)
                .first()
            )
            if ver and ver.parsed_content:
                user_skills = {s.lower().strip() for s in ver.parsed_content.get("skills", []) if s}

        opportunities: list[UnifiedOpportunityItem] = []
        entry_level_count = 0
        priority_companies_count = 0

        for j in jobs:
            title_lower = (j.title or "").lower()
            exp_level_lower = (j.seniority_level or "").lower()

            is_entry = exp_level_lower in ("entry", "fresher", "internship", "junior") or any(
                k in title_lower for k in ENTRY_LEVEL_KEYWORDS
            )
            if is_entry:
                entry_level_count += 1

            company = j.company
            raw_comp_name = (
                company.name
                if (company and company.name)
                else (j.metadata_json.get("company_name") if j.metadata_json else "Employer")
            )
            comp_name: str = str(raw_comp_name) if raw_comp_name else "Employer"
            comp_type = (company.category if company else None) or "general"
            comp_tier = (company.category if company else None) or "standard"

            is_priority = (
                comp_type.lower() in PRIORITY_COMPANY_TIERS
                or comp_tier.lower() in PRIORITY_COMPANY_TIERS
            )
            if is_priority:
                priority_companies_count += 1

            if filter_entry_level and not is_entry:
                continue

            # Verification status audit
            verif_status = j.verification_status or "unverified"
            is_verified = verif_status == "verified"

            # Match score & explanation
            match_obj = matches_map.get(j.id)
            ai_match_obj = ai_matches_map.get(j.id)
            match_score = None
            match_reasons: list[str] = []
            skill_gaps: list[str] = []
            eligibility_concerns: list[str] = []

            if match_obj:
                match_score = round(match_obj.match_score, 1)
                if match_score >= 70:
                    match_reasons.append("High overall alignment with your verified background.")
                if match_obj.score_breakdown:
                    skill_score = match_obj.score_breakdown.get("skills_score", 0)
                    if skill_score > 60:
                        match_reasons.append("Strong technical skill overlap with job criteria.")
            elif ai_match_obj:
                match_score = round(ai_match_obj.fit_score or 0.0, 1)
                if ai_match_obj.recommendation_rationale:
                    match_reasons.append(ai_match_obj.recommendation_rationale)
                elif ai_match_obj.fit_summary:
                    match_reasons.append(ai_match_obj.fit_summary)

            # Detect missing required skills
            job_skills = [s.lower().strip() for s in (j.skills_tags or [])]
            for s in job_skills:
                if user_skills and s not in user_skills:
                    skill_gaps.append(s.title())

            if is_entry:
                match_reasons.append("Identified as early-career or entry-level opportunity.")
            if is_priority:
                match_reasons.append(f"Premier employer category: {comp_type.upper()}.")

            if verif_status == "unverified":
                eligibility_concerns.append(
                    "Job listing is unverified. Apply via official company link only."
                )

            item = UnifiedOpportunityItem(
                job_id=j.id,
                title=j.title,
                company_name=comp_name,
                company_id=j.company_id,
                company_tier=comp_tier,
                company_type=comp_type,
                location=j.location_text or j.city,
                work_arrangement=j.work_arrangement,
                experience_level=j.seniority_level or "entry",
                is_entry_level=is_entry,
                is_verified=is_verified,
                verification_status=verif_status,
                match_score=match_score,
                match_reasons=match_reasons[:3],
                skill_gaps=skill_gaps[:5],
                eligibility_concerns=eligibility_concerns,
                application_url=j.application_url or j.job_url,
                source_name="Official Source" if is_verified else "Discovery Feed",
                published_at=j.created_at.isoformat() if j.created_at else None,
            )
            opportunities.append(item)

        # Sort: Highest match score first, then priority company tier, then verified status
        def _sort_key(opp: UnifiedOpportunityItem) -> tuple[float, int, int]:
            score = opp.match_score if opp.match_score is not None else 0.0
            tier_bonus = 1 if opp.company_type in PRIORITY_COMPANY_TIERS else 0
            verif_bonus = 1 if opp.is_verified else 0
            return (score, tier_bonus, verif_bonus)

        opportunities.sort(key=_sort_key, reverse=True)
        final_opps = opportunities[:limit]

        return UnifiedDiscoveryResponse(
            total_active_jobs=len(jobs),
            entry_level_count=entry_level_count,
            priority_companies_count=priority_companies_count,
            opportunities=final_opps,
            filters_applied={
                "filter_entry_level": filter_entry_level,
                "prioritize_tiers": prioritize_tiers,
            },
        )

    # -------------------------------------------------------------------------
    # 3. Intelligent Application Preparation Workspace
    # -------------------------------------------------------------------------

    @classmethod
    def get_or_create_preparation_workspace(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        resume_id: Optional[uuid.UUID] = None,
    ) -> PreparationDetailResponse:
        """Create or load unified application preparation workspace connecting

        job intelligence, resume tailoring, cover letter, email, screening Q&A,
        and company intelligence.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job opportunity not found.",
            )

        if job.job_status == "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This job opportunity is closed or no longer active.",
            )

        raw_comp_name = (
            job.company.name
            if (job.company and job.company.name)
            else (job.metadata_json.get("company_name") if job.metadata_json else "Employer")
        )
        comp_name: str = str(raw_comp_name) if raw_comp_name else "Employer"

        # Find or create JobApplication record if not present
        app_record = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.job_id == job_id,
            )
            .first()
        )
        if not app_record:
            app_record = JobApplication(
                user_id=user.id,
                job_id=job.id,
                company_id=job.company_id,
                title=job.title,
                company_name=comp_name,
                status="preparing",
                application_channel="official_portal",
                application_url=job.application_url or job.job_url,
            )
            db.add(app_record)
            db.flush()

        # Find or create ApplicationPreparation
        prep_rec = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.job_id == job_id,
            )
            .first()
        )
        if not prep_rec:
            # Create through AssistantService
            AssistantService.get_or_create_preparation(
                db=db,
                user=user,
                job_id=job_id,
                application_id=app_record.id,
            )
            prep_rec = (
                db.query(ApplicationPreparation)
                .filter(
                    ApplicationPreparation.user_id == user.id,
                    ApplicationPreparation.job_id == job_id,
                )
                .first()
            )

        assert prep_rec is not None

        # Link application record if needed
        if not prep_rec.application_id:
            prep_rec.application_id = app_record.id
            db.flush()

        # Connect 1: Job Intelligence
        job_intel_data = None
        try:
            intel = JobIntelligenceService.get_or_create(db, job)
            if intel:
                comp_label = job.company.name if job.company else "company"
                role_summary_str = f"{intel.seniority_level.capitalize()} role at {comp_label}"
                job_intel_data = {
                    "role_summary": role_summary_str,
                    "primary_responsibilities": getattr(intel, "responsibilities", []),
                    "must_have_skills": getattr(intel, "required_skills", []),
                    "nice_to_have_skills": getattr(intel, "preferred_skills", []),
                    "work_culture_signals": getattr(intel, "work_arrangement", ""),
                }
        except Exception as e:
            logger.warning("Could not fetch JobIntelligence for job %s: %s", job_id, e)

        # Connect 2: Candidate Compatibility Assessment
        compatibility_data = None
        match_record = (
            db.query(JobMatch)
            .filter(JobMatch.user_id == user.id, JobMatch.job_id == job_id)
            .first()
        )
        if match_record:
            strengths = [
                s.get("skill", "") for s in match_record.positive_signals if isinstance(s, dict)
            ]
            gaps = [s.get("skill", "") for s in match_record.gap_signals if isinstance(s, dict)]
            compatibility_data = {
                "overall_score": match_record.match_score,
                "breakdown": match_record.score_breakdown,
                "strengths": strengths,
                "gaps": gaps,
            }

        # Connect 3: Resume Tailoring
        tailored_resume_data = None
        if prep_rec.resume_version:
            tailored_resume_data = {
                "version_id": str(prep_rec.resume_version.id),
                "version_number": prep_rec.resume_version.version_number,
                "filename": prep_rec.resume_version.original_filename,
                "is_tailored": bool(
                    prep_rec.resume_version.is_tailored or prep_rec.resume_version.job_id
                ),
            }

        # Connect 4: Cover Letter
        cover_letter_data = None
        latest_cl = (
            db.query(CoverLetter)
            .filter(CoverLetter.user_id == user.id, CoverLetter.job_id == job_id)
            .order_by(CoverLetter.version_number.desc())
            .first()
        )
        if latest_cl:
            cover_letter_data = {
                "id": str(latest_cl.id),
                "version_number": latest_cl.version_number,
                "content": latest_cl.content,
                "is_approved": latest_cl.is_approved,
                "grounded_evidence": getattr(latest_cl, "experience_references", []),
            }

        # Connect 5: Recruiter Email
        recruiter_email_data = None
        latest_email = (
            db.query(ApplicationEmail)
            .filter(ApplicationEmail.user_id == user.id, ApplicationEmail.job_id == job_id)
            .order_by(ApplicationEmail.created_at.desc())
            .first()
        )
        if latest_email:
            is_email_appr = (
                latest_email.status in ("approved", "sent")
                or latest_email.approval_confirmed_at is not None
            )
            recruiter_email_data = {
                "id": str(latest_email.id),
                "subject": latest_email.subject,
                "body_text": latest_email.body,
                "status": latest_email.status,
                "is_approved": is_email_appr,
                "recipient_email": latest_email.recipient_email,
            }

        # Connect 6: Screening Q&A Prep
        qa_prep_list = prep_rec.qa_answers or []
        if not qa_prep_list:
            # Seed default starter Q&A based on job title and candidate background
            skill_sample = ", ".join((job.skills_tags or [])[:3])
            qa_prep_list = [
                {
                    "question": (
                        f"Why are you interested in the {job.title} position at {comp_name}?"
                    ),
                    "answer_outline": (
                        f"Excited about {comp_name}'s mission, technical stack "
                        f"({skill_sample}), and career alignment."
                    ),
                    "status": "prepared",
                },
                {
                    "question": (
                        "What relevant hands-on projects have you built using this tech stack?"
                    ),
                    "answer_outline": (
                        "Referencing completed portfolio projects and "
                        "verifiable GitHub repository evidence."
                    ),
                    "status": "prepared",
                },
            ]
            prep_rec.qa_answers = qa_prep_list
            db.flush()

        # Connect 7: Company Research
        company_research_data = None
        if job.company_id:
            try:
                intel_comp = (
                    db.query(CompanyIntelligence)
                    .filter(CompanyIntelligence.company_id == job.company_id)
                    .first()
                )
                if intel_comp:
                    confirmed_techs = [
                        t.get("name", "")
                        for t in (intel_comp.technology_stack or [])
                        if isinstance(t, dict) and t.get("name")
                    ]
                    company_research_data = {
                        "company_overview": intel_comp.overview or "",
                        "industry": intel_comp.industry_domain or "",
                        "hiring_summary": intel_comp.hiring_summary or {},
                        "technologies_confirmed": confirmed_techs,
                    }
            except Exception as e:
                logger.warning(
                    "Could not load CompanyIntelligence for company %s: %s", job.company_id, e
                )

        # Connect 8: Interview Preparation Starter
        interview_starter_data = {
            "suggested_topics": (job.skills_tags or [])[:5],
            "difficulty": "entry_level",
            "mock_ready": True,
        }

        # Progress check
        can_apply = bool(
            prep_rec.execution_status
            in ("ready_to_apply", "application_page_opened", "submission_pending_confirmation")
        )

        db.commit()

        return PreparationDetailResponse(
            preparation_id=prep_rec.id,
            job_id=job.id,
            job_title=job.title,
            company_name=comp_name,
            application_id=app_record.id,
            execution_status=prep_rec.execution_status,
            execution_channel=prep_rec.execution_channel,
            checklist_status=prep_rec.checklist_status,
            checklist_items=prep_rec.checklist_items or [],
            job_intelligence=job_intel_data,
            compatibility_assessment=compatibility_data,
            tailored_resume=tailored_resume_data,
            cover_letter=cover_letter_data,
            recruiter_email=recruiter_email_data,
            qa_prep=qa_prep_list,
            company_research=company_research_data,
            interview_prep_starter=interview_starter_data,
            can_apply=can_apply,
            portal_url=job.application_url or job.job_url,
        )

    # -------------------------------------------------------------------------
    # 4. Application Execution Workflow & Approval Gates
    # -------------------------------------------------------------------------

    @classmethod
    def approve_preparation(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        channel: str = "official_portal",
        notes: Optional[str] = None,
    ) -> PreparationDetailResponse:
        """Explicit candidate approval gate: transitions preparation state to 'ready_to_apply'."""
        prep_rec = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.job_id == job_id,
            )
            .first()
        )
        if not prep_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application preparation session not found.",
            )

        prep_rec.execution_status = "ready_to_apply"
        prep_rec.execution_channel = channel
        if notes:
            prep_rec.notes = (prep_rec.notes or "") + f"\n[Approved for {channel}]: {notes}"
        prep_rec.updated_at = datetime.now(timezone.utc)

        # Update application status
        if prep_rec.application:
            prep_rec.application.status = "preparing"
            prep_rec.application.application_channel = channel

        db.commit()
        return cls.get_or_create_preparation_workspace(db, user, job_id)

    @classmethod
    def open_application_portal(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Candidate opens official portal. Marks state as 'application_page_opened'.

        DOES NOT treat this as completed application submission.
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        if job.job_status == "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot open portal. This job opportunity is expired or closed.",
            )

        prep_rec = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.job_id == job_id,
            )
            .first()
        )
        if not prep_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Preparation session not found"
            )

        # Transition status
        prep_rec.execution_status = "application_page_opened"
        prep_rec.portal_opened_at = datetime.now(timezone.utc)
        prep_rec.updated_at = datetime.now(timezone.utc)

        # Provide assisted form data for candidate ease
        latest_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user.id)
            .order_by(Resume.created_at.desc())
            .first()
        )
        parsed = {}
        if latest_resume and latest_resume.current_version_id:
            ver = (
                db.query(ResumeVersion)
                .filter(ResumeVersion.id == latest_resume.current_version_id)
                .first()
            )
            parsed = (ver.parsed_content or {}) if ver else {}

        contact = parsed.get("contact", {})
        contact_links = contact.get("links", [])
        linkedin_link = next((lnk for lnk in contact_links if "linkedin" in lnk), "")
        github_link = next((lnk for lnk in contact_links if "github" in lnk), "")
        assisted_data = {
            "full_name": contact.get("name") or user.full_name,
            "email": contact.get("email") or user.email,
            "phone": contact.get("phone") or "",
            "location": contact.get("location") or "",
            "linkedin_url": linkedin_link,
            "github_url": github_link,
            "skills": ", ".join(parsed.get("skills", [])[:10]),
            "summary_snippet": parsed.get("summary", ""),
        }

        # Record activity
        if prep_rec.application_id:
            portal_link_str = job.application_url or job.job_url or ""
            act = ApplicationActivity(
                application_id=prep_rec.application_id,
                user_id=user.id,
                activity_type="portal_opened",
                title="Application Portal Opened",
                description=f"Opened verified application portal: {portal_link_str}",
            )
            db.add(act)

        db.commit()

        return {
            "portal_url": job.application_url or job.job_url,
            "execution_status": prep_rec.execution_status,
            "opened_at": prep_rec.portal_opened_at.isoformat(),
            "assisted_form_data": assisted_data,
        }

    @classmethod
    def confirm_portal_submission(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        confirmation_notes: Optional[str] = None,
    ) -> dict[str, Any]:
        """Explicit candidate confirmation of completed submission."""
        prep_rec = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.job_id == job_id,
            )
            .first()
        )
        if not prep_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Preparation session not found"
            )

        prep_rec.execution_status = "submitted_and_confirmed"
        prep_rec.submission_confirmed_at = datetime.now(timezone.utc)
        prep_rec.updated_at = datetime.now(timezone.utc)
        if confirmation_notes:
            prep_rec.notes = (
                prep_rec.notes or ""
            ) + f"\n[Confirmed Submission]: {confirmation_notes}"

        # Update JobApplication status to 'applied'
        if prep_rec.application_id:
            app = (
                db.query(JobApplication)
                .filter(JobApplication.id == prep_rec.application_id)
                .first()
            )
            if app:
                app.status = "applied"
                app.applied_at = datetime.now(timezone.utc)
                act = ApplicationActivity(
                    application_id=app.id,
                    user_id=user.id,
                    activity_type="application_submitted",
                    title="Application Submitted",
                    description="Candidate confirmed successful application submission.",
                )
                db.add(act)

        db.commit()
        return {
            "status": "success",
            "execution_status": "submitted_and_confirmed",
            "message": (
                "Application submission confirmed and application status moved to 'applied'."
            ),
            "confirmed_at": prep_rec.submission_confirmed_at.isoformat(),
        }

    @classmethod
    def execute_gmail_application(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        email_id: uuid.UUID,
        confirm_send: bool = True,
    ) -> dict[str, Any]:
        """Send approved recruiter email via Gmail after explicit confirmation."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.job_status == "closed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot send application email. Job is expired or inactive.",
            )

        if not confirm_send:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Explicit confirmation (confirm_send=True) is required to dispatch an email."
                ),
            )

        prep_rec = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.job_id == job_id,
            )
            .first()
        )
        if not prep_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Preparation session not found"
            )

        # Call AssistantService to send email
        try:
            AssistantService.send_email_message(
                db=db,
                user=user,
                email_id=email_id,
                confirm_send=True,
            )
        except Exception as e:
            prep_rec.execution_status = "failed"
            prep_rec.notes = (prep_rec.notes or "") + f"\n[Email Dispatch Failed]: {str(e)}"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to send email: {str(e)}",
            ) from e

        # On success
        prep_rec.execution_status = "submitted_and_confirmed"
        prep_rec.submission_confirmed_at = datetime.now(timezone.utc)
        prep_rec.updated_at = datetime.now(timezone.utc)

        if prep_rec.application_id:
            app = (
                db.query(JobApplication)
                .filter(JobApplication.id == prep_rec.application_id)
                .first()
            )
            if app:
                app.status = "applied"
                app.applied_at = datetime.now(timezone.utc)
                app.application_channel = "gmail"
                act = ApplicationActivity(
                    application_id=app.id,
                    user_id=user.id,
                    activity_type="email_sent",
                    title="Recruiter Email Sent",
                    description="Sent recruiter application email via Gmail.",
                )
                db.add(act)

        db.commit()
        return {
            "status": "success",
            "execution_status": "submitted_and_confirmed",
            "message": "Email sent successfully and application marked as applied.",
        }

    @classmethod
    def withdraw_application(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Withdraw application from consideration."""
        prep_rec = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.job_id == job_id,
            )
            .first()
        )
        if not prep_rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Preparation session not found"
            )

        prep_rec.execution_status = "withdrawn"
        prep_rec.updated_at = datetime.now(timezone.utc)

        if prep_rec.application_id:
            app = (
                db.query(JobApplication)
                .filter(JobApplication.id == prep_rec.application_id)
                .first()
            )
            if app:
                app.status = "withdrawn"

        db.commit()
        return {"status": "success", "execution_status": "withdrawn"}

    # -------------------------------------------------------------------------
    # 5. Unified Career Workflow Dashboard
    # -------------------------------------------------------------------------

    @classmethod
    def get_workflow_dashboard(cls, db: Session, user: User) -> WorkflowDashboardResponse:
        """Central dashboard metrics connecting all career operations and next actions."""
        # 1. Profile Completion Check
        missing_items: list[str] = []
        score = 0

        # Check resume
        resume_count = db.query(Resume).filter(Resume.user_id == user.id).count()
        if resume_count > 0:
            score += 40
        else:
            missing_items.append("Upload master resume")

        # Check preferences
        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if pref and pref.target_role_families and pref.preferred_locations:
            score += 30
        else:
            missing_items.append("Configure career target roles and locations")

        # Check portfolio
        try:
            portfolio = PortfolioService.get_or_create_portfolio(db, user)
            if portfolio and portfolio.projects:
                score += 30
            else:
                score += 15
                missing_items.append("Add verified projects to portfolio")
        except Exception:
            missing_items.append("Initialize portfolio showcase")

        profile_pct = min(100, score)

        # 2. Opportunities counts
        total_active_jobs = db.query(Job).filter(Job.job_status == "active").count()

        recommended_count = (
            db.query(JobMatch)
            .filter(JobMatch.user_id == user.id, JobMatch.match_score >= 60.0)
            .count()
        )

        jobs_requiring_review_count = (
            db.query(Job)
            .filter(
                Job.job_status == "active",
                Job.verification_status == "unverified",
            )
            .count()
        )

        # 3. Application Execution states
        preps = (
            db.query(ApplicationPreparation).filter(ApplicationPreparation.user_id == user.id).all()
        )

        awaiting_approval_count = sum(1 for p in preps if p.execution_status == "awaiting_approval")
        submitted_count = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status.in_(("applied", "interview", "offer")),
            )
            .count()
        )
        incomplete_prep_count = sum(
            1
            for p in preps
            if p.execution_status
            in (
                "not_started",
                "preparation_in_progress",
                "awaiting_approval",
                "ready_to_apply",
                "application_page_opened",
                "submission_pending_confirmation",
            )
        )

        # 4. Upcoming interviews
        upcoming_interviews = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status == "interview",
            )
            .count()
        )

        # 5. Prioritized Recommended Actions
        actions: list[WorkflowRecommendedAction] = []

        if awaiting_approval_count > 0:
            actions.append(
                WorkflowRecommendedAction(
                    action_type="approve_application",
                    title=f"Review & Approve {awaiting_approval_count} Application(s)",
                    description=(
                        "Tailored materials and cover letters are generated "
                        "and ready for your sign-off."
                    ),
                    priority="high",
                    target_route="/dashboard/career-workflow",
                    metadata={"count": awaiting_approval_count},
                )
            )

        if upcoming_interviews > 0:
            actions.append(
                WorkflowRecommendedAction(
                    action_type="interview_prep",
                    title="Prepare for Scheduled Interview",
                    description=(
                        "Run a mock interview session and review STAR project talking points."
                    ),
                    priority="high",
                    target_route="/dashboard/interview-prep",
                    metadata={"interviews": upcoming_interviews},
                )
            )

        if recommended_count > 0:
            actions.append(
                WorkflowRecommendedAction(
                    action_type="explore_recommendations",
                    title=f"Explore {recommended_count} Strong Job Matches",
                    description=(
                        "High-compatibility opportunities identified "
                        "for your target technical profile."
                    ),
                    priority="medium",
                    target_route="/dashboard/career-workflow",
                    metadata={"matches": recommended_count},
                )
            )

        if missing_items:
            actions.append(
                WorkflowRecommendedAction(
                    action_type="complete_profile",
                    title="Complete Candidate Onboarding",
                    description=f"Action needed: {missing_items[0]}.",
                    priority="low",
                    target_route="/dashboard/career-workflow",
                    metadata={"missing": missing_items},
                )
            )

        # 6. Recent Workflow Runs
        runs = (
            db.query(CareerWorkflowRun)
            .filter(CareerWorkflowRun.user_id == user.id)
            .order_by(CareerWorkflowRun.created_at.desc())
            .limit(5)
            .all()
        )

        return WorkflowDashboardResponse(
            profile_completion_pct=profile_pct,
            profile_missing_items=missing_items,
            new_opportunities_count=min(total_active_jobs, 25),
            recommended_opportunities_count=recommended_count,
            jobs_requiring_review_count=min(jobs_requiring_review_count, 10),
            applications_awaiting_approval_count=awaiting_approval_count,
            applications_submitted_count=submitted_count,
            incomplete_preparations_count=incomplete_prep_count,
            upcoming_interviews_count=upcoming_interviews,
            recommended_next_actions=actions,
            recent_workflow_runs=runs,  # type: ignore[arg-type]
        )

    # -------------------------------------------------------------------------
    # 6. Workflow Orchestration & Cancellation
    # -------------------------------------------------------------------------

    @classmethod
    def cancel_workflow_run(
        cls,
        db: Session,
        user: User,
        run_id: uuid.UUID,
    ) -> CareerWorkflowRun:
        """Cancel an eligible in-progress or pending workflow run."""
        run = (
            db.query(CareerWorkflowRun)
            .filter(
                CareerWorkflowRun.id == run_id,
                CareerWorkflowRun.user_id == user.id,
            )
            .first()
        )
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found"
            )

        if run.status in ("completed", "failed", "cancelled"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel workflow with status '{run.status}'.",
            )

        run.status = "cancelled"
        run.cancelled_at = datetime.now(timezone.utc)
        run.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run

    # -------------------------------------------------------------------------
    # Helper: Infer Suitable Roles from Resume Content
    # -------------------------------------------------------------------------

    @staticmethod
    def _infer_suitable_roles(
        experience: list[dict[str, Any]],
        skills: list[str],
        summary: str,
    ) -> list[str]:
        """Infer target role families based on past job titles and demonstrated technical skills."""
        roles: list[str] = []
        skills_lower = {s.lower() for s in skills}

        # Check experience titles
        for exp in experience:
            title = exp.get("title") or ""
            t_lower = title.lower()
            if any(k in t_lower for k in ("backend", "python", "fastapi", "django")):
                roles.append("Backend Developer")
            if any(k in t_lower for k in ("frontend", "react", "next", "ui", "web")):
                roles.append("Frontend Developer")
            if any(k in t_lower for k in ("full stack", "fullstack", "software engineer", "sde")):
                roles.append("Full Stack Engineer")
            if any(k in t_lower for k in ("ai", "machine learning", "ml", "data")):
                roles.append("AI / ML Engineer")

        # Fallback to skills heuristics
        if "python" in skills_lower or "fastapi" in skills_lower or "sql" in skills_lower:
            roles.append("Backend Developer")
        if "react" in skills_lower or "javascript" in skills_lower or "typescript" in skills_lower:
            roles.append("Frontend Developer")
        if "pytorch" in skills_lower or "tensorflow" in skills_lower or "pandas" in skills_lower:
            roles.append("AI / ML Engineer")

        if not roles:
            roles = ["Software Engineer", "Junior Developer"]

        # Deduplicate preserving order
        seen = set()
        deduped = []
        for r in roles:
            if r not in seen:
                seen.add(r)
                deduped.append(r)
        return deduped[:4]
