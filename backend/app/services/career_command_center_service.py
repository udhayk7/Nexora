import logging
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.analysis import ResumeAnalysis
from app.models.application import ApplicationStatusHistory, JobApplication
from app.models.assistant import ApplicationPreparation
from app.models.company import Company
from app.models.company_intelligence import CompanyResearchReport
from app.models.interview_prep import InterviewEvaluation, InterviewPreparationSession
from app.models.job import Job
from app.models.match import JobMatch, UserMatchingPreference
from app.models.recommendation import JobIntelligence
from app.models.resume import Resume, ResumeVersion
from app.models.tailoring import ResumeTailoringSession
from app.models.user import User
from app.schemas.career_command_center import (
    ActivityDataPoint,
    CareerFunnelResponse,
    CareerGoalsResponse,
    CareerGoalsUpdate,
    CareerOverviewKPIs,
    CareerReadinessResponse,
    CategoryCount,
    DemonstratedSkillItem,
    FunnelOutcomes,
    FunnelStageItem,
    InterviewPrepOverview,
    LocationCount,
    NextActionItem,
    PerformanceAnalyticsResponse,
    ProjectEvidenceItem,
    RecommendationsResponse,
    RequestedSkillItem,
    SavedVsAppliedComparison,
    SkillFrequencyItem,
    SkillGapItem,
    StatusCount,
    TargetRoleAlignment,
)

logger = logging.getLogger(__name__)


class CareerCommandCenterService:
    """Service providing unified career intelligence, funnel tracking, and analytics."""

    @classmethod
    def _parse_date_cutoff(cls, date_range: str) -> Optional[datetime]:
        """Convert date range string ('30d', '90d', 'all') into a UTC cutoff datetime."""
        now = datetime.now(timezone.utc)
        if date_range == "30d":
            return now - timedelta(days=30)
        elif date_range == "90d":
            return now - timedelta(days=90)
        return None

    @classmethod
    def get_overview(cls, db: Session, user: User, date_range: str = "all") -> CareerOverviewKPIs:
        """Consolidate high-level career KPIs across jobs, matches, and applications."""
        cutoff = cls._parse_date_cutoff(date_range)

        # 1. Platform-wide job discovery metrics
        total_discovered_q = db.query(func.count(Job.id))
        active_verified_q = db.query(func.count(Job.id)).filter(
            Job.job_status == "active",
            Job.verification_status == "verified",
        )
        if cutoff:
            total_discovered_q = total_discovered_q.filter(Job.first_seen_at >= cutoff)
            active_verified_q = active_verified_q.filter(Job.first_seen_at >= cutoff)

        total_discovered = total_discovered_q.scalar() or 0
        active_verified = active_verified_q.scalar() or 0

        # 2. User-specific job matches (strong matches >= 75.0)
        strong_matches_q = db.query(func.count(JobMatch.id)).filter(
            JobMatch.user_id == user.id,
            JobMatch.match_score >= 75.0,
        )
        if cutoff:
            strong_matches_q = strong_matches_q.filter(JobMatch.created_at >= cutoff)
        strong_matches = strong_matches_q.scalar() or 0

        # 3. Saved opportunities (either JobMatch.is_saved or JobApplication status = 'interested')
        saved_from_matches_q = (
            db.query(JobMatch.job_id)
            .distinct()
            .filter(
                JobMatch.user_id == user.id,
                JobMatch.is_saved.is_(True),
            )
        )
        saved_from_apps_q = (
            db.query(JobApplication.job_id)
            .distinct()
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status == "interested",
                JobApplication.job_id.isnot(None),
            )
        )
        if cutoff:
            saved_from_matches_q = saved_from_matches_q.filter(JobMatch.updated_at >= cutoff)
            saved_from_apps_q = saved_from_apps_q.filter(JobApplication.created_at >= cutoff)

        saved_job_ids = {r[0] for r in saved_from_matches_q.all() if r[0]} | {
            r[0] for r in saved_from_apps_q.all() if r[0]
        }
        saved_count = len(saved_job_ids)

        # 4. Applications in progress vs submitted
        apps_base_q = db.query(JobApplication).filter(JobApplication.user_id == user.id)
        if cutoff:
            apps_base_q = apps_base_q.filter(JobApplication.created_at >= cutoff)

        apps = apps_base_q.all()

        in_progress_statuses = {"preparing", "shortlisted", "assessment", "interview"}
        submitted_statuses = {
            "applied",
            "shortlisted",
            "assessment",
            "interview",
            "offer",
            "rejected",
        }

        apps_in_progress = sum(1 for a in apps if a.status in in_progress_statuses)
        apps_submitted = sum(
            1 for a in apps if (a.status in submitted_statuses or a.submission_confirmed)
        )
        interviews_scheduled = sum(1 for a in apps if a.status == "interview")
        offers_received = sum(1 for a in apps if a.status == "offer")

        # 5. User assets: resume versions & interview prep sessions
        resume_versions_q = (
            db.query(func.count(ResumeVersion.id))
            .join(Resume, ResumeVersion.resume_id == Resume.id)
            .filter(Resume.user_id == user.id)
        )
        interview_sessions_q = db.query(func.count(InterviewPreparationSession.id)).filter(
            InterviewPreparationSession.user_id == user.id
        )
        if cutoff:
            resume_versions_q = resume_versions_q.filter(ResumeVersion.created_at >= cutoff)
            interview_sessions_q = interview_sessions_q.filter(
                InterviewPreparationSession.created_at >= cutoff
            )

        resume_versions_count = resume_versions_q.scalar() or 0
        interview_prep_count = interview_sessions_q.scalar() or 0

        # 6. Weekly application target and progress
        prefs = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        metadata = prefs.metadata_json if (prefs and prefs.metadata_json) else {}
        weekly_target = int(metadata.get("weekly_application_target", 5))

        # Start of current calendar week (Monday 00:00:00 UTC)
        now_utc = datetime.now(timezone.utc)
        monday_this_week = (now_utc - timedelta(days=now_utc.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        apps_this_week = (
            db.query(func.count(JobApplication.id))
            .filter(
                JobApplication.user_id == user.id,
                or_(
                    JobApplication.applied_at >= monday_this_week,
                    JobApplication.created_at >= monday_this_week,
                ),
                or_(
                    JobApplication.status.in_(submitted_statuses),
                    JobApplication.submission_confirmed.is_(True),
                ),
            )
            .scalar()
            or 0
        )

        target_progress = min(100.0, round((apps_this_week / max(1, weekly_target)) * 100.0, 1))

        return CareerOverviewKPIs(
            total_discovered_jobs=total_discovered,
            active_verified_jobs=active_verified,
            strong_job_matches=strong_matches,
            saved_opportunities=saved_count,
            applications_in_progress=apps_in_progress,
            applications_submitted=apps_submitted,
            interviews_scheduled=interviews_scheduled,
            offers_received=offers_received,
            resume_versions_created=resume_versions_count,
            interview_prep_sessions_completed=interview_prep_count,
            weekly_application_target=weekly_target,
            applications_this_week=apps_this_week,
            target_progress_percentage=target_progress,
            date_range=date_range,
        )

    @classmethod
    def get_funnel(cls, db: Session, user: User) -> CareerFunnelResponse:
        """Calculate the 7-stage application conversion funnel using application status history."""
        # 1. Discovered: Total active verified opportunities on Nexora
        discovered_count = (
            db.query(func.count(Job.id))
            .filter(
                Job.job_status == "active",
                Job.verification_status.notin_(["suspicious", "expired"]),
            )
            .scalar()
            or 0
        )

        # 2. Matched: Total matched opportunities for user
        matched_count = (
            db.query(func.count(JobMatch.id)).filter(JobMatch.user_id == user.id).scalar() or 0
        )

        # 3. Saved: Saved in matches or marked interested
        saved_matches_q = (
            db.query(JobMatch.job_id)
            .distinct()
            .filter(
                JobMatch.user_id == user.id,
                JobMatch.is_saved.is_(True),
            )
        )
        interested_apps_q = (
            db.query(JobApplication.job_id)
            .distinct()
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status == "interested",
                JobApplication.job_id.isnot(None),
            )
        )
        saved_job_ids = {r[0] for r in saved_matches_q.all() if r[0]} | {
            r[0] for r in interested_apps_q.all() if r[0]
        }
        saved_count = len(saved_job_ids)

        # 4. Preparing: Applications in preparing or with an active preparation workspace
        preparations_job_ids = {
            r[0]
            for r in db.query(ApplicationPreparation.job_id)
            .distinct()
            .filter(ApplicationPreparation.user_id == user.id)
            .all()
            if r[0]
        }
        preparing_apps_count = (
            db.query(func.count(JobApplication.id))
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status == "preparing",
            )
            .scalar()
            or 0
        )
        preparing_count = max(preparing_apps_count, len(preparations_job_ids))

        # 5. Applied: Source of truth is confirmed submission or status history reaching applied
        applied_status_app_ids = {
            r[0]
            for r in db.query(ApplicationStatusHistory.application_id)
            .distinct()
            .join(JobApplication, ApplicationStatusHistory.application_id == JobApplication.id)
            .filter(
                JobApplication.user_id == user.id,
                ApplicationStatusHistory.to_status == "applied",
            )
            .all()
        }
        confirmed_apps = (
            db.query(JobApplication.id)
            .filter(
                JobApplication.user_id == user.id,
                or_(
                    JobApplication.status.in_(
                        [
                            "applied",
                            "shortlisted",
                            "assessment",
                            "interview",
                            "offer",
                            "rejected",
                        ]
                    ),
                    JobApplication.submission_confirmed.is_(True),
                ),
            )
            .all()
        )
        all_applied_ids = applied_status_app_ids | {r[0] for r in confirmed_apps}
        applied_count = len(all_applied_ids)

        # 6. Interview: Reached interview status
        interview_history_ids = {
            r[0]
            for r in db.query(ApplicationStatusHistory.application_id)
            .distinct()
            .join(JobApplication, ApplicationStatusHistory.application_id == JobApplication.id)
            .filter(
                JobApplication.user_id == user.id,
                ApplicationStatusHistory.to_status.in_(["interview", "offer"]),
            )
            .all()
        }
        current_interview_ids = {
            r[0]
            for r in db.query(JobApplication.id)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status.in_(["interview", "offer"]),
            )
            .all()
        }
        interview_count = len(interview_history_ids | current_interview_ids)

        # 7. Offer: Reached offer status
        offer_history_ids = {
            r[0]
            for r in db.query(ApplicationStatusHistory.application_id)
            .distinct()
            .join(JobApplication, ApplicationStatusHistory.application_id == JobApplication.id)
            .filter(
                JobApplication.user_id == user.id,
                ApplicationStatusHistory.to_status == "offer",
            )
            .all()
        }
        current_offer_ids = {
            r[0]
            for r in db.query(JobApplication.id)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status == "offer",
            )
            .all()
        }
        offer_count = len(offer_history_ids | current_offer_ids)

        # Build Stage Items
        raw_stages = [
            ("discovered", "Discovered Opportunities", discovered_count),
            ("matched", "Matched Opportunities", matched_count),
            ("saved", "Saved Opportunities", saved_count),
            ("preparing", "Preparing Application", preparing_count),
            ("applied", "Applied (Confirmed)", applied_count),
            ("interview", "Interviews Conducted", interview_count),
            ("offer", "Job Offers", offer_count),
        ]

        stage_items: list[FunnelStageItem] = []
        prev_count: Optional[int] = None

        for s_id, label, count in raw_stages:
            conversion_pct: Optional[float] = None
            drop_off_count = 0
            drop_off_pct = 0.0

            if prev_count is not None:
                if prev_count > 0:
                    conversion_pct = round((count / prev_count) * 100.0, 1)
                    drop_off_count = max(0, prev_count - count)
                    drop_off_pct = round((drop_off_count / prev_count) * 100.0, 1)
                else:
                    conversion_pct = 0.0
                    drop_off_count = 0
                    drop_off_pct = 0.0

            stage_items.append(
                FunnelStageItem(
                    stage_id=s_id,
                    label=label,
                    count=count,
                    conversion_from_previous_percentage=conversion_pct,
                    drop_off_count=drop_off_count,
                    drop_off_percentage=drop_off_pct,
                )
            )
            prev_count = count

        # Funnel outcomes from actual active user applications
        all_user_apps = (
            db.query(JobApplication.status).filter(JobApplication.user_id == user.id).all()
        )
        statuses = [r[0] for r in all_user_apps]
        outcomes = FunnelOutcomes(
            active=sum(
                1
                for s in statuses
                if s
                in {"interested", "preparing", "applied", "shortlisted", "assessment", "interview"}
            ),
            offered=sum(1 for s in statuses if s == "offer"),
            rejected=sum(1 for s in statuses if s == "rejected"),
            withdrawn=sum(1 for s in statuses if s == "withdrawn"),
        )

        return CareerFunnelResponse(
            stages=stage_items,
            outcomes=outcomes,
        )

    @classmethod
    def get_readiness(cls, db: Session, user: User) -> CareerReadinessResponse:
        """Compute candidate career readiness deterministically from verified evidence."""
        # 1. Fetch user's latest completed Resume Analysis
        analysis = (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.user_id == user.id, ResumeAnalysis.status == "completed")
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )

        demonstrated_skills_dict: dict[str, DemonstratedSkillItem] = {}
        project_evidence_items: list[ProjectEvidenceItem] = []
        demonstrated_skill_names_lower: set[str] = set()

        if analysis and analysis.result:
            skills_data = analysis.result.get("skills_analysis", {})
            supported_skills = skills_data.get("supported_skills", [])
            categorized_skills = skills_data.get("categorized_skills", {})
            evidence_entries = skills_data.get("evidence", [])

            # Invert categorized skills for quick lookup
            skill_to_cat: dict[str, str] = {}
            for cat, skl_list in categorized_skills.items():
                for skl in skl_list:
                    skill_to_cat[skl.lower()] = cat

            for skl in supported_skills:
                skl_clean = str(skl).strip()
                skl_lower = skl_clean.lower()
                demonstrated_skill_names_lower.add(skl_lower)

                source_secs = [
                    e.get("section", "Experience")
                    for e in evidence_entries
                    if skl_lower in e.get("excerpt", "").lower()
                ] or ["Resume"]

                demonstrated_skills_dict[skl_clean] = DemonstratedSkillItem(
                    skill=skl_clean,
                    evidence_count=len(source_secs),
                    source_sections=list(set(source_secs))[:3],
                    category=skill_to_cat.get(skl_lower, "Technical"),
                )

            # Extract project and internship evidence
            exp_data = analysis.result.get("experience_evidence", {})
            measurable = exp_data.get("measurable_outcomes", [])
            profile_data = analysis.result.get("candidate_profile", {})
            profile_summary = profile_data.get("summary", "Candidate Experience")

            if measurable:
                project_evidence_items.append(
                    ProjectEvidenceItem(
                        title="Demonstrated Technical Impact",
                        role_or_context=profile_summary[:120],
                        measurable_outcomes=measurable[:4],
                        demonstrated_technologies=list(demonstrated_skills_dict.keys())[:6],
                    )
                )

        # 2. Query target role preferences & Job Intelligence requirements
        prefs = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        target_roles = prefs.target_role_families if prefs else []

        # Find active jobs aligned with target roles or latest verified jobs
        job_int_q = (
            db.query(JobIntelligence)
            .join(Job, JobIntelligence.job_id == Job.id)
            .filter(
                Job.job_status == "active",
                Job.verification_status.notin_(["suspicious", "expired"]),
            )
        )
        if target_roles:
            job_int_q = job_int_q.filter(Job.role_family.in_(target_roles))

        job_intelligences = job_int_q.limit(100).all()

        # Aggregate requested skills across relevant job market postings
        requested_skill_counter: Counter[str] = Counter()
        for ji in job_intelligences:
            for s in ji.required_skills or []:
                if s:
                    requested_skill_counter[s.strip()] += 2
            for s in ji.preferred_skills or []:
                if s:
                    requested_skill_counter[s.strip()] += 1

        top_requested_skills: list[RequestedSkillItem] = []
        missing_skills: list[SkillGapItem] = []

        for skl_name, freq in requested_skill_counter.most_common(20):
            is_demonstrated = skl_name.lower() in demonstrated_skill_names_lower
            top_requested_skills.append(
                RequestedSkillItem(
                    skill=skl_name,
                    frequency=freq,
                    is_demonstrated_by_user=is_demonstrated,
                )
            )
            if not is_demonstrated:
                missing_skills.append(
                    SkillGapItem(
                        skill=skl_name,
                        market_demand_frequency=freq,
                        status="missing_entirely",
                        recommendation=(
                            f"Build a demonstrative project applying {skl_name} "
                            "to satisfy frequent target job requirements."
                        ),
                    )
                )

        # 3. Aggregated mock interview performance
        evals = (
            db.query(InterviewEvaluation)
            .join(
                InterviewPreparationSession,
                InterviewEvaluation.session_id == InterviewPreparationSession.id,
            )
            .filter(InterviewPreparationSession.user_id == user.id)
            .all()
        )

        completed_sessions_count = (
            db.query(func.count(InterviewPreparationSession.id))
            .filter(InterviewPreparationSession.user_id == user.id)
            .scalar()
            or 0
        )

        interview_overview = InterviewPrepOverview(
            completed_sessions_count=completed_sessions_count,
            evaluated_answers_count=len(evals),
        )

        if evals:
            interview_overview.average_overall_score = round(
                sum(e.overall_score for e in evals) / len(evals), 1
            )
            rubrics = {
                "technical_correctness": round(
                    sum(e.technical_correctness_score for e in evals) / len(evals), 1
                ),
                "relevance": round(sum(e.relevance_score for e in evals) / len(evals), 1),
                "completeness": round(sum(e.completeness_score for e in evals) / len(evals), 1),
                "clarity": round(sum(e.clarity_score for e in evals) / len(evals), 1),
                "approach": round(sum(e.approach_score for e in evals) / len(evals), 1),
                "communication": round(sum(e.communication_score for e in evals) / len(evals), 1),
            }
            interview_overview.rubric_averages = rubrics

            # Top strengths vs areas for improvement
            sorted_rubrics = sorted(rubrics.items(), key=lambda x: x[1], reverse=True)
            interview_overview.top_strengths = [
                f"{k.replace('_', ' ').title()} ({v}%)" for k, v in sorted_rubrics[:2] if v >= 65.0
            ]
            interview_overview.areas_for_improvement = [
                f"{k.replace('_', ' ').title()} ({v}%)" for k, v in sorted_rubrics[-2:] if v < 75.0
            ]

        # 4. Target role alignment
        match_scores = db.query(JobMatch.match_score).filter(JobMatch.user_id == user.id).all()
        avg_match_score = (
            round(sum(m[0] for m in match_scores) / len(match_scores), 1) if match_scores else 0.0
        )
        alignment_tier = (
            "High"
            if avg_match_score >= 75.0
            else ("Moderate" if avg_match_score >= 50.0 else "Developing")
        )
        role_alignment = TargetRoleAlignment(
            target_role_families=target_roles,
            average_match_score=avg_match_score,
            alignment_tier=alignment_tier,
        )

        # 5. Deterministic Career Readiness Score Calculation
        # Weights: Skills 40%, Job Match 30%, Interview 20%, Resume Evidence Depth 10%
        # S_skills: proportion of top 15 requested market skills demonstrated by candidate
        top_15_market = top_requested_skills[:15]
        skills_matched_count = sum(1 for s in top_15_market if s.is_demonstrated_by_user)
        s_skills = (
            min(100.0, round((skills_matched_count / max(1, len(top_15_market))) * 100.0, 1))
            if top_15_market
            else (80.0 if demonstrated_skills_dict else 20.0)
        )

        # S_match: average match score (clamped 0-100)
        s_match = min(100.0, max(0.0, avg_match_score))

        # S_interview: average evaluation score, or 50.0 neutral baseline if no practice yet
        s_interview = (
            interview_overview.average_overall_score
            if interview_overview.average_overall_score is not None
            else 50.0
        )

        # S_evidence: depth of quantified outcomes (up to 5 outcomes = 100%)
        outcomes_count = (
            len(project_evidence_items[0].measurable_outcomes) if project_evidence_items else 0
        )
        s_evidence = (
            min(100.0, round((outcomes_count / 4.0) * 100.0, 1)) if outcomes_count > 0 else 30.0
        )

        readiness_score = round(
            (0.40 * s_skills) + (0.30 * s_match) + (0.20 * s_interview) + (0.10 * s_evidence), 1
        )

        formula_desc = (
            "Readiness Score = (40% x Skills Alignment) + (30% x Match Alignment) + "
            "(20% x Interview Readiness) + (10% x Resume Evidence Depth)"
        )
        limitations_desc = (
            "This readiness score is calculated strictly from deterministic heuristics based on "
            "uploaded resume evidence, active market skill frequencies, and completed mock "
            "evaluations. It does not replace human judgment or guarantee employment."
        )

        return CareerReadinessResponse(
            readiness_score=readiness_score,
            readiness_score_formula=formula_desc,
            score_limitations=limitations_desc,
            score_breakdown={
                "skills_alignment": s_skills,
                "matching_alignment": s_match,
                "interview_readiness": s_interview,
                "resume_evidence_depth": s_evidence,
            },
            demonstrated_skills=list(demonstrated_skills_dict.values())[:25],
            frequently_requested_skills=top_requested_skills[:15],
            missing_or_underrepresented_skills=missing_skills[:10],
            project_and_internship_evidence=project_evidence_items,
            interview_performance=interview_overview,
            target_role_alignment=role_alignment,
        )

    @classmethod
    def get_recommendations(cls, db: Session, user: User) -> RecommendationsResponse:
        """Identify prioritized, actionable next steps for the user's active job search."""
        actions: list[NextActionItem] = []
        now = datetime.now(timezone.utc)

        # Rule 1: Scheduled interview without an Interview Preparation Session (HIGH)
        interview_apps = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status == "interview",
            )
            .all()
        )
        for app in interview_apps:
            existing_session = (
                db.query(InterviewPreparationSession)
                .filter(
                    InterviewPreparationSession.user_id == user.id,
                    InterviewPreparationSession.application_id == app.id,
                )
                .first()
            )
            if not existing_session:
                actions.append(
                    NextActionItem(
                        id=f"interview-prep-{app.id}",
                        priority="high",
                        action_type="prepare_interview",
                        title=f"Prepare for interview at {app.company_name}",
                        reason=(
                            f"Application for '{app.title}' is currently in interview stage, "
                            "but no structured mock interview coaching session has been launched."
                        ),
                        related_entity_type="application",
                        related_entity_id=str(app.id),
                        navigation_url=f"/dashboard/interview-prep?application_id={app.id}",
                        metadata={"company_name": app.company_name, "title": app.title},
                    )
                )

        # Rule 2: Scheduled interview or application without a Company Intelligence Report (HIGH)
        for app in interview_apps:
            if app.company_id:
                has_report = (
                    db.query(CompanyResearchReport)
                    .filter(
                        CompanyResearchReport.company_id == app.company_id,
                        CompanyResearchReport.user_id == user.id,
                    )
                    .first()
                )
                if not has_report:
                    actions.append(
                        NextActionItem(
                            id=f"company-research-{app.company_id}",
                            priority="high",
                            action_type="research_company",
                            title=f"Research {app.company_name} engineering and tech stack",
                            reason=(
                                f"You have an upcoming interview with {app.company_name}. "
                                "Generate an evidence report to explore their tech stack."
                            ),
                            related_entity_type="company",
                            related_entity_id=str(app.company_id),
                            navigation_url=f"/dashboard/company-intelligence?company_id={app.company_id}",
                            metadata={"company_name": app.company_name},
                        )
                    )

        # Rule 3: Application preparation workspace incomplete (HIGH)
        in_progress_preps = (
            db.query(ApplicationPreparation)
            .filter(
                ApplicationPreparation.user_id == user.id,
                ApplicationPreparation.checklist_status != "completed",
            )
            .limit(2)
            .all()
        )
        for prep in in_progress_preps:
            job = db.query(Job).filter(Job.id == prep.job_id).first()
            job_title = job.title if job else "Target Opportunity"
            actions.append(
                NextActionItem(
                    id=f"complete-prep-{prep.id}",
                    priority="high",
                    action_type="complete_prep",
                    title=f"Complete preparation for {job_title}",
                    reason=(
                        "Application checklist is incomplete. Review tailored cover letter "
                        "and resume evidence before portal submission."
                    ),
                    related_entity_type="preparation",
                    related_entity_id=str(prep.id),
                    navigation_url=f"/dashboard/application-assistant?job_id={prep.job_id}",
                    metadata={"job_id": str(prep.job_id)},
                )
            )

        # Rule 4: Applied applications needing follow-up (MEDIUM)
        seven_days_ago = now - timedelta(days=7)
        follow_up_apps = (
            db.query(JobApplication)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.status == "applied",
                or_(
                    JobApplication.next_follow_up_at <= now,
                    JobApplication.applied_at <= seven_days_ago,
                ),
            )
            .limit(2)
            .all()
        )
        for app in follow_up_apps:
            actions.append(
                NextActionItem(
                    id=f"follow-up-{app.id}",
                    priority="medium",
                    action_type="follow_up",
                    title=f"Follow up on application to {app.company_name}",
                    reason=(
                        f"Application for '{app.title}' was submitted with no status updates. "
                        "Consider generating a professional recruiter follow-up email."
                    ),
                    related_entity_type="application",
                    related_entity_id=str(app.id),
                    navigation_url="/dashboard/applications",
                    metadata={"application_id": str(app.id)},
                )
            )

        # Rule 5: High-scoring verified job match not yet saved or applied (MEDIUM)
        applied_job_ids = {
            r[0]
            for r in db.query(JobApplication.job_id)
            .filter(
                JobApplication.user_id == user.id,
                JobApplication.job_id.isnot(None),
            )
            .all()
        }
        strong_matches = (
            db.query(JobMatch)
            .join(Job, JobMatch.job_id == Job.id)
            .filter(
                JobMatch.user_id == user.id,
                JobMatch.match_score >= 80.0,
                JobMatch.is_saved.is_(False),
                JobMatch.is_dismissed.is_(False),
                Job.job_status == "active",
                Job.verification_status == "verified",
            )
            .order_by(JobMatch.match_score.desc())
            .limit(2)
            .all()
        )
        for sm in strong_matches:
            if sm.job_id not in applied_job_ids:
                job = sm.job
                actions.append(
                    NextActionItem(
                        id=f"strong-match-{sm.id}",
                        priority="medium",
                        action_type="review_match",
                        title=f"Review {sm.match_score:.0f}% match: {job.title}",
                        reason=(
                            f"Verified role aligned with your skills ({sm.match_score:.0f}% fit). "
                            "Review alignment signals and consider applying."
                        ),
                        related_entity_type="job",
                        related_entity_id=str(sm.job_id),
                        navigation_url="/dashboard/matches",
                        metadata={"job_id": str(sm.job_id), "score": sm.match_score},
                    )
                )

        # Rule 6: Saved opportunity without a tailored resume (MEDIUM)
        saved_matches = (
            db.query(JobMatch)
            .filter(
                JobMatch.user_id == user.id,
                JobMatch.is_saved.is_(True),
                JobMatch.job_id.notin_(list(applied_job_ids) or [uuid.uuid4()]),
            )
            .limit(2)
            .all()
        )
        for sm in saved_matches:
            # Check if tailored resume session exists for this job
            has_tailored = (
                db.query(ResumeTailoringSession)
                .filter(
                    ResumeTailoringSession.user_id == user.id,
                    ResumeTailoringSession.job_id == sm.job_id,
                    ResumeTailoringSession.status == "completed",
                )
                .first()
            )
            if not has_tailored:
                actions.append(
                    NextActionItem(
                        id=f"tailor-resume-{sm.job_id}",
                        priority="medium",
                        action_type="tailor_resume",
                        title=f"Tailor resume for {sm.job.title}",
                        reason=(
                            f"Opportunity '{sm.job.title}' is saved. Generate a tailored resume "
                            "highlighting job-specific keywords without fabrication."
                        ),
                        related_entity_type="job",
                        related_entity_id=str(sm.job_id),
                        navigation_url=f"/dashboard/resumes/tailor?jobId={sm.job_id}",
                        metadata={"job_id": str(sm.job_id)},
                    )
                )

        # Limit to top 6 prioritized recommendations
        actions.sort(
            key=lambda a: 0 if a.priority == "high" else (1 if a.priority == "medium" else 2)
        )
        selected_actions = actions[:6]

        return RecommendationsResponse(
            actions=selected_actions,
            total_actions=len(selected_actions),
        )

    @classmethod
    def get_analytics(
        cls, db: Session, user: User, date_range: str = "all"
    ) -> PerformanceAnalyticsResponse:
        """Generate comprehensive job search performance analytics with statistical safeguards."""
        cutoff = cls._parse_date_cutoff(date_range)

        # Query all applications for this user
        apps_q = db.query(JobApplication).filter(JobApplication.user_id == user.id)
        if cutoff:
            apps_q = apps_q.filter(JobApplication.created_at >= cutoff)
        apps = apps_q.all()

        # 1. Weekly & Monthly activity buckets
        weekly_counter: dict[str, dict[str, int]] = {}
        monthly_counter: dict[str, dict[str, int]] = {}

        # Initialize last 8 weeks and last 6 months for clean charts
        now = datetime.now(timezone.utc)
        for i in range(7, -1, -1):
            w_start = (now - timedelta(weeks=i)).strftime("%Y-W%W")
            weekly_counter[w_start] = {
                "applications_created": 0,
                "applications_submitted": 0,
                "interviews_scheduled": 0,
            }

        for i in range(5, -1, -1):
            m_start = (now - timedelta(days=i * 30)).strftime("%Y-%m")
            monthly_counter[m_start] = {
                "applications_created": 0,
                "applications_submitted": 0,
                "interviews_scheduled": 0,
            }

        for app in apps:
            if app.created_at:
                w_key = app.created_at.strftime("%Y-W%W")
                m_key = app.created_at.strftime("%Y-%m")
                if w_key in weekly_counter:
                    weekly_counter[w_key]["applications_created"] += 1
                if m_key in monthly_counter:
                    monthly_counter[m_key]["applications_created"] += 1

            if app.applied_at or app.status in {
                "applied",
                "shortlisted",
                "assessment",
                "interview",
                "offer",
                "rejected",
            }:
                ref_time = app.applied_at or app.created_at
                if ref_time:
                    w_key = ref_time.strftime("%Y-W%W")
                    m_key = ref_time.strftime("%Y-%m")
                    if w_key in weekly_counter:
                        weekly_counter[w_key]["applications_submitted"] += 1
                    if m_key in monthly_counter:
                        monthly_counter[m_key]["applications_submitted"] += 1

            if app.status == "interview":
                ref_time = app.updated_at or app.created_at
                if ref_time:
                    w_key = ref_time.strftime("%Y-W%W")
                    m_key = ref_time.strftime("%Y-%m")
                    if w_key in weekly_counter:
                        weekly_counter[w_key]["interviews_scheduled"] += 1
                    if m_key in monthly_counter:
                        monthly_counter[m_key]["interviews_scheduled"] += 1

        weekly_activity = [
            ActivityDataPoint(
                period=k,
                applications_created=v["applications_created"],
                applications_submitted=v["applications_submitted"],
                interviews_scheduled=v["interviews_scheduled"],
            )
            for k, v in sorted(weekly_counter.items())
        ]

        monthly_activity = [
            ActivityDataPoint(
                period=k,
                applications_created=v["applications_created"],
                applications_submitted=v["applications_submitted"],
                interviews_scheduled=v["interviews_scheduled"],
            )
            for k, v in sorted(monthly_counter.items())
        ]

        # 2. Applications by Role Family
        role_family_counts = (
            db.query(Job.role_family, func.count(JobApplication.id))
            .join(JobApplication, JobApplication.job_id == Job.id)
            .filter(JobApplication.user_id == user.id)
            .group_by(Job.role_family)
            .all()
        )
        total_role_apps = sum(c[1] for c in role_family_counts) or 1
        apps_by_role = [
            CategoryCount(
                category=(r[0] or "General Software").replace("_", " ").title(),
                count=r[1],
                percentage=round((r[1] / total_role_apps) * 100.0, 1),
            )
            for r in role_family_counts
        ]

        # 3. Applications by Company Category
        category_counts = (
            db.query(Company.category, func.count(JobApplication.id))
            .join(JobApplication, JobApplication.company_id == Company.id)
            .filter(JobApplication.user_id == user.id)
            .group_by(Company.category)
            .all()
        )
        total_cat_apps = sum(c[1] for c in category_counts) or 1
        apps_by_company_category = [
            CategoryCount(
                category=(c[0] or "Other").replace("_", " ").title(),
                count=c[1],
                percentage=round((c[1] / total_cat_apps) * 100.0, 1),
            )
            for c in category_counts
        ]

        # 4. Conversion Rates with Statistical Significance Safeguards
        submitted_count = sum(
            1
            for a in apps
            if a.status
            in {"applied", "shortlisted", "assessment", "interview", "offer", "rejected"}
            or a.submission_confirmed
        )
        interview_count = sum(1 for a in apps if a.status in {"interview", "offer"})
        offer_count = sum(1 for a in apps if a.status == "offer")

        # Safeguard: Do not display misleading high percentages for sample size < 5
        is_interview_meaningful = submitted_count >= 5
        interview_rate = (
            round((interview_count / submitted_count) * 100.0, 1) if submitted_count > 0 else None
        )

        is_offer_meaningful = submitted_count >= 5
        offer_rate = (
            round((offer_count / submitted_count) * 100.0, 1) if submitted_count > 0 else None
        )

        # 5. Application Status Distribution
        status_counter: Counter[str] = Counter([a.status for a in apps])
        total_apps = len(apps) or 1
        status_dist = [
            StatusCount(
                status=st.replace("_", " ").title(),
                count=cnt,
                percentage=round((cnt / total_apps) * 100.0, 1),
            )
            for st, cnt in status_counter.most_common()
        ]

        # 6. Frequently Matched Skills
        matches = db.query(JobMatch).filter(JobMatch.user_id == user.id).limit(100).all()
        skill_counter: Counter[str] = Counter()
        for m in matches:
            for sig in m.positive_signals or []:
                if isinstance(sig, dict) and "signal" in sig:
                    skill_counter[str(sig["signal"]).strip()] += 1
                elif isinstance(sig, str):
                    skill_counter[sig.strip()] += 1

        top_matched_skills = [
            SkillFrequencyItem(skill=s, count=c) for s, c in skill_counter.most_common(10)
        ]

        # 7. Common Job Locations
        locations = (
            db.query(Job.location_text, func.count(Job.id))
            .join(JobApplication, JobApplication.job_id == Job.id)
            .filter(JobApplication.user_id == user.id)
            .group_by(Job.location_text)
            .all()
        )
        location_counts = [
            LocationCount(location=loc[0] or "Remote", count=loc[1])
            for loc in sorted(locations, key=lambda x: x[1], reverse=True)[:6]
        ]

        # 8. Saved vs Applied Comparison
        saved_from_matches = (
            db.query(func.count(JobMatch.id))
            .filter(JobMatch.user_id == user.id, JobMatch.is_saved.is_(True))
            .scalar()
            or 0
        )
        saved_from_apps = (
            db.query(func.count(JobApplication.id))
            .filter(JobApplication.user_id == user.id, JobApplication.status == "interested")
            .scalar()
            or 0
        )
        saved_total = saved_from_matches + saved_from_apps
        ratio = round((submitted_count / max(1, saved_total)), 2)

        if saved_total == 0 and submitted_count == 0:
            insight = (
                "Begin exploring discovered opportunities and save jobs matching your career goals."
            )
        elif ratio < 0.2:
            insight = (
                "High volume of saved jobs relative to submissions. "
                "Consider taking action to prepare and submit applications."
            )
        elif ratio > 0.8:
            insight = "Strong follow-through rate from saved jobs to submitted applications."
        else:
            insight = (
                "Balanced pipeline between opportunity curation and active application submissions."
            )

        return PerformanceAnalyticsResponse(
            date_range=date_range,
            weekly_activity=weekly_activity,
            monthly_activity=monthly_activity,
            applications_by_role_family=apps_by_role,
            applications_by_company_category=apps_by_company_category,
            interview_conversion_rate=interview_rate,
            interview_sample_size=submitted_count,
            is_interview_sample_meaningful=is_interview_meaningful,
            offer_conversion_rate=offer_rate,
            offer_sample_size=submitted_count,
            is_offer_sample_meaningful=is_offer_meaningful,
            application_status_distribution=status_dist,
            most_frequently_matched_skills=top_matched_skills,
            most_common_job_locations=location_counts,
            saved_vs_applied=SavedVsAppliedComparison(
                saved_count=saved_total,
                applied_count=submitted_count,
                ratio=ratio,
                insight=insight,
            ),
        )

    @classmethod
    def get_goals(cls, db: Session, user: User) -> CareerGoalsResponse:
        """Retrieve user's career goals and matching preferences."""
        prefs = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if not prefs:
            return CareerGoalsResponse()

        metadata = prefs.metadata_json or {}
        return CareerGoalsResponse(
            target_role_families=prefs.target_role_families or [],
            preferred_locations=prefs.preferred_locations or [],
            work_arrangement_preferences=prefs.work_arrangement_preferences or [],
            min_salary=prefs.min_salary,
            salary_currency=prefs.salary_currency or "INR",
            salary_period=prefs.salary_period or "annual",
            preferred_company_categories=metadata.get(
                "preferred_company_categories", prefs.preferred_industries or []
            ),
            priority_technical_skills=prefs.preferred_skills or [],
            weekly_application_target=int(metadata.get("weekly_application_target", 5)),
        )

    @classmethod
    def update_goals(cls, db: Session, user: User, data: CareerGoalsUpdate) -> CareerGoalsResponse:
        """Update user's career goals and preferences, synchronizing with UserMatchingPreference."""
        prefs = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        if not prefs:
            prefs = UserMatchingPreference(user_id=user.id)
            db.add(prefs)

        if data.target_role_families is not None:
            prefs.target_role_families = data.target_role_families
        if data.preferred_locations is not None:
            prefs.preferred_locations = data.preferred_locations
        if data.work_arrangement_preferences is not None:
            prefs.work_arrangement_preferences = data.work_arrangement_preferences
        if data.min_salary is not None:
            prefs.min_salary = data.min_salary
        if data.salary_currency is not None:
            prefs.salary_currency = data.salary_currency
        if data.salary_period is not None:
            prefs.salary_period = data.salary_period
        if data.priority_technical_skills is not None:
            prefs.preferred_skills = data.priority_technical_skills

        # Metadata updates (weekly target, company categories)
        meta = dict(prefs.metadata_json or {})
        if data.weekly_application_target is not None:
            meta["weekly_application_target"] = data.weekly_application_target
        if data.preferred_company_categories is not None:
            meta["preferred_company_categories"] = data.preferred_company_categories
            prefs.preferred_industries = data.preferred_company_categories
        prefs.metadata_json = meta

        db.commit()
        db.refresh(prefs)

        return cls.get_goals(db, user)
