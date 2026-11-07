import hashlib
import math
import uuid
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.core.logging import logger
from app.models.analysis import ResumeAnalysis
from app.models.application import JobApplication
from app.models.job import Job
from app.models.match import JobMatch, UserMatchingPreference
from app.models.recommendation import AIJobMatch, JobIntelligence
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.analysis import ResumeAnalysisResult
from app.schemas.recommendation import (
    AIJobMatchResponse,
    JobRecommendationItem,
    RecommendationExplanation,
    RecommendationListResponse,
    RecommendationRefreshRequest,
    RecommendationRefreshResponse,
    RecommendationStateResponse,
)
from app.services.ai.ai_match_engine import AIJobMatchEngine
from app.services.job_intelligence_service import JobIntelligenceService
from app.services.job_service import compute_job_freshness
from app.services.matching_engine import MatchingEngine

PRIORITY_ROLE_KEYWORDS = {
    "ai",
    "ml",
    "genai",
    "generative ai",
    "machine learning",
    "deep learning",
    "python",
    "frontend",
    "front-end",
    "fullstack",
    "full-stack",
    "full stack",
    "sde",
    "software engineer",
    "software development",
    "data",
    "data engineer",
    "automation",
    "qa automation",
}


class RecommendationService:
    """Intelligent recommendation service blending deterministic matching, job intelligence,

    and personalized AI compatibility assessments.
    """

    @classmethod
    def _resolve_user_resume_and_analysis(
        cls,
        db: Session,
        user: User,
        resume_version_id: Optional[uuid.UUID] = None,
    ) -> tuple[Resume, ResumeVersion, ResumeAnalysis, ResumeAnalysisResult]:
        """Resolve the active resume, version, and completed AI analysis for the user."""
        resume: Optional[Resume] = None
        version: Optional[ResumeVersion] = None

        if resume_version_id:
            version = (
                db.query(ResumeVersion)
                .join(Resume, Resume.id == ResumeVersion.resume_id)
                .filter(
                    ResumeVersion.id == resume_version_id,
                    Resume.user_id == user.id,
                )
                .first()
            )
            if not version:
                raise NotFoundError("Requested resume version not found or does not belong to you")
            resume = db.query(Resume).filter(Resume.id == version.resume_id).first()
        else:
            resume = (
                db.query(Resume)
                .filter(Resume.user_id == user.id)
                .order_by(Resume.updated_at.desc())
                .first()
            )
            if not resume:
                raise BadRequestError(
                    "No resume found. Please upload a resume in Resume Studio first."
                )

            if resume.current_version_id:
                version = (
                    db.query(ResumeVersion)
                    .filter(ResumeVersion.id == resume.current_version_id)
                    .first()
                )

            if not version:
                version = (
                    db.query(ResumeVersion)
                    .filter(ResumeVersion.resume_id == resume.id)
                    .order_by(ResumeVersion.version_number.desc())
                    .first()
                )

        if not version or not resume:
            raise BadRequestError("Could not resolve a valid resume version.")

        analysis = (
            db.query(ResumeAnalysis)
            .filter(
                ResumeAnalysis.user_id == user.id,
                ResumeAnalysis.version_id == version.id,
                ResumeAnalysis.status == "completed",
            )
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )

        if not analysis or not analysis.result:
            raise BadRequestError(
                "Selected resume version has not been analyzed yet. "
                "Please run AI Resume Intelligence in Resume Studio first."
            )

        analysis_result = ResumeAnalysisResult.model_validate(analysis.result)
        return resume, version, analysis, analysis_result

    @classmethod
    def get_recommendations(
        cls,
        db: Session,
        user: User,
        resume_version_id: Optional[uuid.UUID] = None,
        role_family: Optional[str] = None,
        location: Optional[str] = None,
        work_arrangement: Optional[str] = None,
        seniority: Optional[str] = None,
        verification_status: Optional[str] = None,
        min_score: Optional[float] = None,
        salary_disclosed_only: bool = False,
        include_applied: bool = False,
        search_query: Optional[str] = None,
        sort_by: str = "recommendation_score",
        page: int = 1,
        page_size: int = 20,
    ) -> RecommendationListResponse:
        """Calculate and return personalized ranked job recommendations."""
        resume, version, analysis, analysis_result = cls._resolve_user_resume_and_analysis(
            db, user, resume_version_id
        )

        # User preferences
        preferences = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )

        # Exclusions: Applied jobs
        applied_job_ids = set()
        apps = (
            db.query(JobApplication.job_id)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.job_id.isnot(None),
                JobApplication.status != "withdrawn",
            )
            .all()
        )
        for (j_id,) in apps:
            if j_id:
                applied_job_ids.add(j_id)

        # Exclusions: Dismissed jobs & Saved jobs
        dismissed_job_ids = set()
        saved_job_ids = set()
        matches_state = (
            db.query(JobMatch.job_id, JobMatch.is_dismissed, JobMatch.is_saved)
            .filter(JobMatch.user_id == user.id)
            .all()
        )
        for j_id, is_dismissed, is_saved in matches_state:
            if is_dismissed:
                dismissed_job_ids.add(j_id)
            if is_saved:
                saved_job_ids.add(j_id)

        # Query candidate active jobs
        query = db.query(Job).filter(
            Job.job_status != "closed",
            Job.verification_status.notin_(["suspicious", "expired"]),
        )

        # Do not recommend dismissed jobs
        if dismissed_job_ids:
            query = query.filter(Job.id.notin_(list(dismissed_job_ids)))

        # Do not recommend applied jobs unless requested
        if not include_applied and applied_job_ids:
            query = query.filter(Job.id.notin_(list(applied_job_ids)))

        # Filters
        if role_family:
            query = query.filter(Job.role_family.ilike(f"%{role_family}%"))
        if work_arrangement and work_arrangement != "all":
            query = query.filter(Job.work_arrangement == work_arrangement)
        if seniority and seniority != "all":
            query = query.filter(Job.seniority_level.ilike(f"%{seniority}%"))
        if verification_status and verification_status != "all":
            query = query.filter(Job.verification_status == verification_status)
        if salary_disclosed_only:
            query = query.filter(or_(Job.salary_min.isnot(None), Job.salary_max.isnot(None)))
        if search_query and search_query.strip():
            sq = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Job.title.ilike(sq),
                    Job.location_text.ilike(sq),
                    Job.role_family.ilike(sq),
                )
            )

        candidate_jobs = query.order_by(Job.first_seen_at.desc()).limit(200).all()

        # Batch load AI evaluations for this user and version
        ai_evaluations_map: dict[uuid.UUID, AIJobMatch] = {}
        if candidate_jobs:
            c_job_ids = [j.id for j in candidate_jobs]
            ai_evals = (
                db.query(AIJobMatch)
                .filter(
                    AIJobMatch.user_id == user.id,
                    AIJobMatch.resume_version_id == version.id,
                    AIJobMatch.job_id.in_(c_job_ids),
                )
                .all()
            )
            for ev in ai_evals:
                ai_evaluations_map[ev.job_id] = ev

        items: list[JobRecommendationItem] = []
        top_score = 0.0
        ai_eval_count = 0
        verified_count = 0

        for job in candidate_jobs:
            freshness = compute_job_freshness(job.last_verified_at or job.first_seen_at)
            job.freshness = freshness  # type: ignore[attr-defined]

            # 1. Deterministic match evaluation
            det_score, breakdown, positives, gaps = MatchingEngine.evaluate_match(
                job=job,
                resume_analysis=analysis_result,
                preferences=preferences,
            )

            # 2. Retrieve or lazily create job intelligence
            intelligence = JobIntelligenceService.get_or_create(db, job)

            # 3. AI Evaluation check
            ai_match = ai_evaluations_map.get(job.id)
            if ai_match:
                ai_eval_count += 1

            if job.verification_status in ("verified", "corroborated"):
                verified_count += 1

            # 4. Compute Personalized Recommendation Score
            rec_score = cls._compute_recommendation_score(
                det_score=det_score,
                job=job,
                intelligence=intelligence,
                ai_match=ai_match,
                preferences=preferences,
            )

            if min_score and rec_score < min_score:
                continue

            top_score = max(top_score, rec_score)

            # 5. Build Grounded Recommendation Explanation
            explanation = cls._build_explanation(
                job=job,
                intelligence=intelligence,
                ai_match=ai_match,
                positives=positives,
                gaps=gaps,
                resume_version=version,
                preferences=preferences,
            )

            is_salary_disclosed = bool(job.salary_min or job.salary_max)

            item = JobRecommendationItem(
                job_id=job.id,
                title=job.title,
                company_name=job.company.name if job.company else "Unknown Company",
                company_logo_url=None,
                location_text=job.location_text or job.city or "Unspecified",
                work_arrangement=job.work_arrangement,
                role_family=job.role_family,
                seniority_level=job.seniority_level or intelligence.seniority_level,
                employment_type=job.employment_type,
                job_url=job.job_url,
                application_url=job.application_url or job.job_url,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_period=job.salary_period,
                salary_disclosed=is_salary_disclosed,
                verification_status=job.verification_status,
                freshness=freshness,
                deterministic_score=round(det_score, 1),
                recommendation_score=round(rec_score, 1),
                score_breakdown=breakdown.model_dump(),
                is_saved=job.id in saved_job_ids,
                is_dismissed=job.id in dismissed_job_ids,
                has_applied=job.id in applied_job_ids,
                ai_evaluated=ai_match is not None,
                ai_compatibility_rating=ai_match.compatibility_rating if ai_match else None,
                ai_fit_score=ai_match.fit_score if ai_match else None,
                explanation=explanation,
                first_seen_at=job.first_seen_at,
            )
            items.append(item)

        # 6. Sorting
        if sort_by == "deterministic_score":
            items.sort(key=lambda x: x.deterministic_score, reverse=True)
        elif sort_by == "newest":
            items.sort(key=lambda x: x.first_seen_at, reverse=True)
        elif sort_by == "salary":
            items.sort(key=lambda x: x.salary_min or 0.0, reverse=True)
        else:  # recommendation_score
            items.sort(key=lambda x: x.recommendation_score, reverse=True)

        total = len(items)
        page_size_safe = max(1, min(page_size, 100))
        page_safe = max(1, page)
        total_pages = math.ceil(total / page_size_safe) if total > 0 else 1
        start_idx = (page_safe - 1) * page_size_safe
        paged_items = items[start_idx : start_idx + page_size_safe]

        stats = {
            "top_score": round(top_score, 1),
            "total_count": total,
            "ai_evaluated_count": ai_eval_count,
            "verified_count": verified_count,
        }

        return RecommendationListResponse(
            items=paged_items,
            total=total,
            page=page_safe,
            page_size=page_size_safe,
            total_pages=total_pages,
            active_resume_version_id=version.id,
            active_resume_title=f"{resume.title} (v{version.version_number})",
            stats=stats,
        )

    @classmethod
    def _compute_recommendation_score(
        cls,
        det_score: float,
        job: Job,
        intelligence: JobIntelligence,
        ai_match: Optional[AIJobMatch],
        preferences: Optional[UserMatchingPreference],
    ) -> float:
        """Blend deterministic score with focus domains, freshness, trust, and AI assessments."""
        score = det_score

        # 1. Priority Role / Keyword Alignment Boost (+5 to +10)
        title_lower = job.title.lower()
        role_lower = (job.role_family or "").lower()
        job_skills = {s.lower() for s in (intelligence.required_skills + job.skills_tags)}

        matched_focus_kw = 0
        for kw in PRIORITY_ROLE_KEYWORDS:
            if kw in title_lower or kw in role_lower or kw in job_skills:
                matched_focus_kw += 1

        if matched_focus_kw >= 2:
            score += 8.0
        elif matched_focus_kw == 1:
            score += 5.0

        # 2. Fresher and early-career opportunity prioritization (+5)
        seniority = (job.seniority_level or intelligence.seniority_level).lower()
        if seniority in ("fresher", "internship", "entry_level", "junior"):
            score += 5.0

        # 3. Verification Trust Boost
        if job.verification_status == "verified":
            score += 5.0
        elif job.verification_status == "corroborated":
            score += 3.0

        # 4. Freshness Boost
        freshness = getattr(job, "freshness", "unknown")
        if freshness == "recent":
            score += 4.0
        elif freshness == "due_for_review":
            score += 1.0
        elif freshness == "stale":
            score -= 5.0

        # 5. Work Arrangement & Location preference match
        if preferences:
            pref_arrangements = [a.lower() for a in preferences.work_arrangement_preferences]
            if (
                job.work_arrangement.lower() in pref_arrangements
                or "remote" in pref_arrangements
                and job.work_arrangement == "remote"
            ):
                score += 3.0

            if preferences.preferred_locations:
                loc_text = (job.location_text or "").lower()
                for p_loc in preferences.preferred_locations:
                    if p_loc.lower() in loc_text or p_loc.lower() in (job.city or "").lower():
                        score += 3.0
                        break

            # Undisclosed salary is NEVER penalized!
            # Only if disclosed and meets or exceeds preference, award small bonus
            if (
                preferences.min_salary
                and job.salary_min
                and job.salary_min >= preferences.min_salary
            ):
                score += 2.0

        # 6. AI Match Evaluation modifier (if already evaluated)
        if ai_match:
            if ai_match.compatibility_rating == "strong":
                score += 5.0
            elif ai_match.compatibility_rating == "moderate":
                score += 2.0
            elif ai_match.compatibility_rating == "poor":
                score -= 8.0

        return max(0.0, min(100.0, score))

    @classmethod
    def _build_explanation(
        cls,
        job: Job,
        intelligence: JobIntelligence,
        ai_match: Optional[AIJobMatch],
        positives: list[Any],
        gaps: list[Any],
        resume_version: ResumeVersion,
        preferences: Optional[UserMatchingPreference],
    ) -> RecommendationExplanation:
        """Construct grounded explanation of why job matches and actionable next steps."""
        if ai_match:
            return RecommendationExplanation(
                why_matches={
                    "skills": [
                        str(s.get("title", ""))
                        for s in ai_match.strengths
                        if "Skills" in str(s.get("title", ""))
                    ],
                    "experience": ai_match.experience_alignment.get("reasoning", ""),
                    "projects": [
                        str(s.get("title", ""))
                        for s in ai_match.strengths
                        if "Project" in str(s.get("title", ""))
                    ],
                    "preference_alignment": ai_match.recommendation_rationale,
                },
                potential_gaps={
                    "missing_skills": [
                        str(g.get("skill", ""))
                        for g in ai_match.skill_gaps
                        if g.get("importance") == "high"
                    ],
                    "experience_gaps": ai_match.missing_requirements[:3],
                    "qualification_mismatches": [],
                },
                recommended_next_steps=[
                    str(s.get("action", "")) for s in ai_match.next_steps[:3] if s.get("action")
                ],
            )

        # Fallback dynamic grounded explanation from deterministic engine
        matching_skills = [p.description for p in positives if p.dimension == "skills"]
        missing_skills = [
            g.description for g in gaps if g.dimension == "skills" and g.type == "missing"
        ]
        mismatch_items = [g.description for g in gaps if g.type == "mismatch"]

        # Projects from resume version
        parsed = resume_version.parsed_content or {}
        proj_list = [
            p if isinstance(p, str) else p.get("title")
            for p in parsed.get("projects", [])
            if isinstance(p, str) or (isinstance(p, dict) and p.get("title"))
        ]

        why_matches = {
            "skills": matching_skills[:4] or ["Core technical alignment with job requirements"],
            "experience": f"Directly targets {intelligence.seniority_level} technologists",
            "projects": proj_list[:2]
            if proj_list
            else ["Demonstrated hands-on technical coursework"],
            "preference_alignment": (
                f"Matches role '{job.role_family}' and {job.work_arrangement} arrangement"
            ),
        }

        potential_gaps = {
            "missing_skills": missing_skills[:3],
            "experience_gaps": [],
            "qualification_mismatches": mismatch_items[:2],
        }

        top_skills = intelligence.required_skills[:2]
        skill_str = ", ".join(top_skills) if top_skills else "target technologies"

        next_steps = [
            f"Tailor your resume in Resume Studio to emphasize {skill_str}",
            "Review job responsibilities and verify alignment with your projects",
            "Track this application once submitted to keep your pipeline organized",
        ]

        return RecommendationExplanation(
            why_matches=why_matches,
            potential_gaps=potential_gaps,
            recommended_next_steps=next_steps,
        )

    @classmethod
    def evaluate_ai_match(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        resume_version_id: Optional[uuid.UUID] = None,
        force_refresh: bool = False,
    ) -> AIJobMatchResponse:
        """Run or retrieve AI match assessment between user's resume version and target job."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job opportunity not found")

        resume, version, analysis, analysis_result = cls._resolve_user_resume_and_analysis(
            db, user, resume_version_id
        )

        intelligence = JobIntelligenceService.get_or_create(db, job)

        # Assessment hash for resume-version-aware caching
        assessment_payload = f"{intelligence.content_hash}:{version.id}:{analysis.id}"
        assessment_hash = hashlib.sha256(assessment_payload.encode("utf-8")).hexdigest()

        existing = (
            db.query(AIJobMatch)
            .filter(
                AIJobMatch.user_id == user.id,
                AIJobMatch.resume_version_id == version.id,
                AIJobMatch.job_id == job.id,
            )
            .first()
        )

        # Cache hit
        if (
            existing
            and existing.assessment_hash == assessment_hash
            and existing.status == "completed"
            and not force_refresh
        ):
            logger.debug("Cache hit for AIJobMatch on job %s for user %s", job.id, user.id)
            return AIJobMatchResponse.model_validate(existing)

        # Execute AI evaluation or deterministic fallback
        data, provider, model, is_fallback = AIJobMatchEngine.evaluate(
            job=job,
            intelligence=intelligence,
            version=version,
            resume_analysis=analysis_result,
        )

        if existing:
            existing.job_intelligence_id = intelligence.id
            existing.assessment_hash = assessment_hash
            existing.compatibility_rating = data.get("compatibility_rating", "moderate")
            existing.fit_score = data.get("fit_score")
            existing.fit_summary = data.get("fit_summary", "")
            existing.strengths = data.get("strengths", [])
            existing.skill_gaps = data.get("skill_gaps", [])
            existing.experience_alignment = data.get("experience_alignment", {})
            existing.transferable_skills = data.get("transferable_skills", [])
            existing.missing_requirements = data.get("missing_requirements", [])
            existing.recommendation_rationale = data.get("recommendation_rationale", "")
            existing.next_steps = data.get("next_steps", [])
            existing.evidence_citations = data.get("evidence_citations", [])
            existing.provider = provider
            existing.model = model
            existing.status = "completed"
            existing.error_message = None
            existing.is_deterministic_fallback = is_fallback
            record = existing
        else:
            record = AIJobMatch(
                user_id=user.id,
                job_id=job.id,
                resume_id=resume.id,
                resume_version_id=version.id,
                job_intelligence_id=intelligence.id,
                assessment_hash=assessment_hash,
                compatibility_rating=data.get("compatibility_rating", "moderate"),
                fit_score=data.get("fit_score"),
                fit_summary=data.get("fit_summary", ""),
                strengths=data.get("strengths", []),
                skill_gaps=data.get("skill_gaps", []),
                experience_alignment=data.get("experience_alignment", {}) or {},
                transferable_skills=data.get("transferable_skills", []),
                missing_requirements=data.get("missing_requirements", []),
                recommendation_rationale=data.get("recommendation_rationale", ""),
                next_steps=data.get("next_steps", []),
                evidence_citations=data.get("evidence_citations", []),
                provider=provider,
                model=model,
                status="completed",
                error_message=None,
                is_deterministic_fallback=is_fallback,
                metadata_json={},
            )
            db.add(record)

        db.commit()
        db.refresh(record)

        audit_service.record_event(
            action="recommendation.ai_match_evaluated",
            resource_type="ai_job_match",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(record.id),
            metadata={
                "job_id": str(job.id),
                "resume_version_id": str(version.id),
                "rating": record.compatibility_rating,
                "fit_score": record.fit_score,
                "provider": provider,
                "is_fallback": is_fallback,
            },
        )

        return AIJobMatchResponse.model_validate(record)

    @classmethod
    def get_ai_match_evaluation(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        resume_version_id: Optional[uuid.UUID] = None,
    ) -> Optional[AIJobMatchResponse]:
        """Retrieve existing AI match evaluation for user and job."""
        _, version, _, _ = cls._resolve_user_resume_and_analysis(db, user, resume_version_id)

        record = (
            db.query(AIJobMatch)
            .filter(
                AIJobMatch.user_id == user.id,
                AIJobMatch.resume_version_id == version.id,
                AIJobMatch.job_id == job_id,
            )
            .first()
        )
        if not record:
            return None
        return AIJobMatchResponse.model_validate(record)

    @classmethod
    def refresh_recommendations(
        cls,
        db: Session,
        user: User,
        request: RecommendationRefreshRequest,
    ) -> RecommendationRefreshResponse:
        """Refresh recommendations cache and optionally evaluate top N with AI."""
        # 1. Fetch current recommendations
        recs = cls.get_recommendations(
            db=db,
            user=user,
            resume_version_id=request.resume_version_id,
            page_size=50,
        )

        ai_eval_count = 0
        if request.evaluate_top_ai:
            limit = min(request.max_ai_evaluations, 5)
            for item in recs.items[:limit]:
                try:
                    cls.evaluate_ai_match(
                        db=db,
                        user=user,
                        job_id=item.job_id,
                        resume_version_id=recs.active_resume_version_id,
                    )
                    ai_eval_count += 1
                except Exception as exc:
                    logger.warning("Failed top AI evaluation for job %s: %s", item.job_id, exc)

        audit_service.record_event(
            action="recommendation.refreshed",
            resource_type="user",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(user.id),
            metadata={
                "recommendations_count": recs.total,
                "ai_evaluations_run": ai_eval_count,
            },
        )

        return RecommendationRefreshResponse(
            message="Recommendations refreshed successfully",
            recommendations_count=recs.total,
            ai_evaluations_run=ai_eval_count,
        )

    @classmethod
    def update_opportunity_state(
        cls,
        db: Session,
        user: User,
        job_id: uuid.UUID,
        is_saved: Optional[bool] = None,
        is_dismissed: Optional[bool] = None,
    ) -> RecommendationStateResponse:
        """Save or dismiss a job opportunity for the current user."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise NotFoundError("Job opportunity not found")

        match = (
            db.query(JobMatch)
            .filter(JobMatch.user_id == user.id, JobMatch.job_id == job_id)
            .first()
        )
        if not match:
            resume, version, analysis, _ = cls._resolve_user_resume_and_analysis(db, user)
            match = JobMatch(
                user_id=user.id,
                job_id=job.id,
                resume_id=resume.id,
                version_id=version.id,
                analysis_id=analysis.id,
                engine_version="v1.0-deterministic",
                match_score=0.0,
                score_breakdown={},
                positive_signals=[],
                gap_signals=[],
                is_saved=False,
                is_dismissed=False,
            )
            db.add(match)

        if is_saved is not None:
            match.is_saved = is_saved
        if is_dismissed is not None:
            match.is_dismissed = is_dismissed

        db.commit()
        db.refresh(match)

        if is_saved:
            action = "match.saved"
        elif is_dismissed:
            action = "match.dismissed"
        else:
            action = "match.updated"
        audit_service.record_event(
            action=action,
            resource_type="job_match",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(match.id),
            metadata={
                "job_id": str(job.id),
                "is_saved": match.is_saved,
                "is_dismissed": match.is_dismissed,
            },
        )
        return RecommendationStateResponse(
            job_id=job.id,
            is_saved=match.is_saved,
            is_dismissed=match.is_dismissed,
        )
