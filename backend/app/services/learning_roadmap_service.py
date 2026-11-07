"""
Learning Roadmap & Skill Development Service.
Orchestrates personalized skill gap analysis, roadmap lifecycle, curated educational resources,
milestone progression, project tracking, and activity analytics with strict multi-tenant isolation.
"""

import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.analysis import ResumeAnalysis
from app.models.interview_prep import InterviewEvaluation, InterviewPreparationSession
from app.models.job import Job
from app.models.learning_roadmap import (
    LearningActivity,
    LearningMilestone,
    LearningProject,
    LearningResource,
    LearningRoadmap,
)
from app.models.match import UserMatchingPreference
from app.models.recommendation import JobIntelligence
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.learning_roadmap import (
    LearningActivityCreate,
    LearningAnalyticsResponse,
    LearningMilestoneUpdate,
    LearningProjectCreate,
    LearningProjectUpdate,
    LearningResourceCreate,
    ProjectRecommendationResponse,
    RoadmapGenerateRequest,
    SkillGapAnalysisResponse,
    SkillItem,
    SuggestedMilestone,
)
from app.services.ai.roadmap_engine import RoadmapGenerationEngine
from app.services.learning_resources_catalog import CURATED_RESOURCES


class LearningRoadmapService:
    """Service handling all learning roadmap, skill gap, and project tracking logic."""

    # -----------------------------------------------------------------------
    # 1. Personalized Skill Gap Analysis
    # -----------------------------------------------------------------------

    @classmethod
    def get_skill_gaps(cls, db: Session, user: User) -> SkillGapAnalysisResponse:
        """
        Analyze skill gaps by synthesizing resume analysis, matching requirements,
        interview weaknesses, and user career goals.
        Never asserts a skill is demonstrated without concrete resume evidence.
        """
        # A. Gather Demonstrated Skills from candidate's latest Resume Analysis and Version
        demonstrated_map: dict[str, str] = {}
        latest_analysis = (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.user_id == user.id, ResumeAnalysis.status == "completed")
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )
        if latest_analysis and latest_analysis.result:
            skills_data = latest_analysis.result.get("skills_analysis", {})
            for s in skills_data.get("supported_skills", []):
                name = s.get("skill_name") or s.get("name") if isinstance(s, dict) else str(s)
                if name:
                    demonstrated_map[name.lower().strip()] = name.strip()
            for s in latest_analysis.result.get(
                "extracted_skills", []
            ) + latest_analysis.result.get("skills", []):
                name = s.get("name") if isinstance(s, dict) else str(s)
                if name:
                    demonstrated_map[name.lower().strip()] = name.strip()

        latest_version = (
            db.query(ResumeVersion)
            .join(Resume, ResumeVersion.resume_id == Resume.id)
            .filter(Resume.user_id == user.id)
            .order_by(ResumeVersion.created_at.desc())
            .first()
        )
        if latest_version and latest_version.parsed_content:
            for s in latest_version.parsed_content.get("skills", []):
                name = str(s).strip()
                if name:
                    demonstrated_map[name.lower()] = name

        # B. User Matching Preferences (target roles and priority goals)
        pref = (
            db.query(UserMatchingPreference)
            .filter(UserMatchingPreference.user_id == user.id)
            .first()
        )
        target_roles = (
            pref.target_role_families if pref and pref.target_role_families else ["backend_python"]
        )
        priority_skills_set = {
            s.lower().strip()
            for s in (
                (pref.preferred_skills if pref and pref.preferred_skills else [])
                + (
                    pref.metadata_json.get("priority_skills", [])
                    if pref and pref.metadata_json
                    else []
                )
            )
        }

        # C. Market Demand Skills from matched/active jobs
        job_skill_counter: Counter[str] = Counter()
        target_role_skills_set: set[str] = set()

        job_intelligences = (
            db.query(JobIntelligence)
            .join(Job, JobIntelligence.job_id == Job.id)
            .filter(Job.job_status == "active")
            .limit(50)
            .all()
        )
        for ji in job_intelligences:
            for r_skill in ji.required_skills or []:
                cleaned = str(r_skill).strip()
                if cleaned:
                    job_skill_counter[cleaned.lower()] += 2
                    target_role_skills_set.add(cleaned.lower())
            for p_skill in ji.preferred_skills or []:
                cleaned = str(p_skill).strip()
                if cleaned:
                    job_skill_counter[cleaned.lower()] += 1
                    target_role_skills_set.add(cleaned.lower())

        # D. Interview Weaknesses from completed evaluations
        interview_weakness_counter: Counter[str] = Counter()
        evaluations = (
            db.query(InterviewEvaluation)
            .join(
                InterviewPreparationSession,
                InterviewEvaluation.session_id == InterviewPreparationSession.id,
            )
            .filter(InterviewPreparationSession.user_id == user.id)
            .all()
        )
        for ev in evaluations:
            flagged_texts = (ev.missing_points or []) + (ev.suggested_improvements or [])
            if ev.evaluation_feedback:
                flagged_texts.append(ev.evaluation_feedback)
            for w in flagged_texts:
                cleaned = str(w).strip().lower()
                # Check if text mentions any known tech skill
                for known_s in list(job_skill_counter.keys()) + list(priority_skills_set):
                    if known_s in cleaned:
                        interview_weakness_counter[known_s] += 1

        # E. In-Progress Skills from active roadmaps/activities
        in_progress_skills: set[str] = set()
        active_roadmaps = (
            db.query(LearningRoadmap)
            .filter(
                LearningRoadmap.user_id == user.id,
                LearningRoadmap.status == "active",
            )
            .all()
        )
        for rm in active_roadmaps:
            for ts in rm.target_skills or []:
                in_progress_skills.add(str(ts).strip().lower())

        # Collect unique candidate skill pool to evaluate
        all_evaluated_skills: dict[str, str] = {}
        for k, v in demonstrated_map.items():
            all_evaluated_skills[k] = v
        for k in job_skill_counter:
            all_evaluated_skills[k] = k.title()
        for k in priority_skills_set:
            all_evaluated_skills[k] = k.title()
        for k in interview_weakness_counter:
            all_evaluated_skills[k] = k.title()
        for k in in_progress_skills:
            all_evaluated_skills[k] = k.title()

        demonstrated_items: list[SkillItem] = []
        partial_items: list[SkillItem] = []
        missing_items: list[SkillItem] = []
        interview_weakness_items: list[SkillItem] = []

        for skill_key, skill_display in all_evaluated_skills.items():
            is_demo = skill_key in demonstrated_map
            is_prog = skill_key in in_progress_skills
            job_freq = job_skill_counter.get(skill_key, 0)
            is_target_role = skill_key in target_role_skills_set
            is_priority = skill_key in priority_skills_set
            interview_weak_count = interview_weakness_counter.get(skill_key, 0)

            # Deterministic Priority Score Formula (0 to 100)
            score = 0.0
            score += min(job_freq * 8.0, 35.0)
            score += 25.0 if is_priority else 0.0
            score += 20.0 if is_target_role else 0.0
            score += min(interview_weak_count * 15.0, 20.0)
            score = round(min(score, 100.0), 1)

            if score >= 60.0 or interview_weak_count >= 2:
                priority = "critical"
            elif score >= 40.0:
                priority = "high"
            elif score >= 20.0:
                priority = "medium"
            else:
                priority = "low"

            sources: list[str] = []
            if is_demo:
                sources.append("resume_analysis")
            if job_freq > 0:
                sources.append(f"job_market_demand:{job_freq}")
            if is_priority:
                sources.append("user_career_goal")
            if interview_weak_count > 0:
                sources.append(f"interview_weakness:{interview_weak_count}")
            if is_prog:
                sources.append("in_progress_learning_plan")

            # Classification
            if interview_weak_count > 0:
                status = "interview_weakness"
            elif is_demo:
                status = "demonstrated"
            elif is_prog:
                status = "partially_demonstrated"
            else:
                status = "missing"

            evidence = (
                "Verified in candidate resume"
                if is_demo
                else (
                    "Currently practiced in learning roadmap"
                    if is_prog
                    else (
                        f"Identified as interview improvement area ({interview_weak_count}x)"
                        if interview_weak_count > 0
                        else None
                    )
                )
            )

            item = SkillItem(
                skill=skill_display,
                status=status,
                priority=priority,
                priority_score=score,
                job_frequency=job_freq,
                is_target_role_skill=is_target_role,
                is_priority_goal=is_priority,
                interview_weakness_count=interview_weak_count,
                evidence_summary=evidence,
                supporting_sources=sources,
            )

            if status == "demonstrated":
                demonstrated_items.append(item)
            elif status == "partially_demonstrated":
                partial_items.append(item)
            elif status == "interview_weakness":
                interview_weakness_items.append(item)
            else:
                missing_items.append(item)

        # Top recommended skills to learn (exclude already demonstrated)
        top_candidates = [
            it
            for it in (partial_items + missing_items + interview_weakness_items)
            if it.priority in ("critical", "high", "medium")
        ]
        top_candidates.sort(key=lambda x: x.priority_score, reverse=True)

        return SkillGapAnalysisResponse(
            demonstrated_skills=demonstrated_items,
            partially_demonstrated_skills=partial_items,
            missing_skills=missing_items,
            interview_weakness_skills=interview_weakness_items,
            top_recommended_skills=top_candidates[:8],
            target_roles=target_roles,
            total_identified_gaps=len(partial_items)
            + len(missing_items)
            + len(interview_weakness_items),
        )

    # -----------------------------------------------------------------------
    # 2. Roadmap Generation & Management
    # -----------------------------------------------------------------------

    @classmethod
    def generate_and_save_roadmap(
        cls,
        db: Session,
        user: User,
        request: RoadmapGenerateRequest,
    ) -> LearningRoadmap:
        """Generate and persist a structured learning roadmap adapted to user resume skills."""
        # Retrieve candidate demonstrated skills
        demonstrated: list[str] = []
        latest_analysis = (
            db.query(ResumeAnalysis)
            .filter(ResumeAnalysis.user_id == user.id, ResumeAnalysis.status == "completed")
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )
        if latest_analysis and latest_analysis.result:
            skills_data = latest_analysis.result.get("skills_analysis", {})
            for s in skills_data.get("supported_skills", []):
                name = s.get("skill_name") or s.get("name") if isinstance(s, dict) else str(s)
                if name and name not in demonstrated:
                    demonstrated.append(name.strip())
            for s in latest_analysis.result.get(
                "extracted_skills", []
            ) + latest_analysis.result.get("skills", []):
                name = s.get("name") if isinstance(s, dict) else str(s)
                if name and name not in demonstrated:
                    demonstrated.append(name.strip())

        latest_version = (
            db.query(ResumeVersion)
            .join(Resume, ResumeVersion.resume_id == Resume.id)
            .filter(Resume.user_id == user.id)
            .order_by(ResumeVersion.created_at.desc())
            .first()
        )
        if latest_version and latest_version.parsed_content:
            for s in latest_version.parsed_content.get("skills", []):
                name = str(s).strip()
                if name and name not in demonstrated:
                    demonstrated.append(name)

        roadmap_data, provider_name, model_name, is_fallback = (
            RoadmapGenerationEngine.generate_roadmap(
                target_role=request.target_role,
                demonstrated_skills=demonstrated,
                custom_skills=request.custom_skills,
                target_difficulty=request.target_difficulty or "intermediate",
                user_notes=request.user_notes,
            )
        )

        roadmap = LearningRoadmap(
            user_id=user.id,
            title=roadmap_data["title"],
            target_role=roadmap_data["target_role"],
            description=roadmap_data["description"],
            target_skills=roadmap_data["target_skills"],
            status="active",
            difficulty_level=roadmap_data.get("difficulty_level", "intermediate"),
            total_estimated_hours=roadmap_data.get("total_estimated_hours", 0.0),
            completed_hours=roadmap_data.get("completed_hours", 0.0),
            completion_percentage=roadmap_data.get("completion_percentage", 0.0),
            prerequisites=roadmap_data.get("prerequisites", []),
            already_mastered_skills=roadmap_data.get("already_mastered_skills", []),
            metadata_json=roadmap_data.get("metadata_json", {}),
        )
        db.add(roadmap)
        db.flush()

        # Add child milestones
        for m_data in roadmap_data.get("milestones", []):
            milestone = LearningMilestone(
                roadmap_id=roadmap.id,
                title=m_data["title"],
                stage=m_data["stage"],
                description=m_data["description"],
                learning_objectives=m_data.get("learning_objectives", []),
                practical_exercises=m_data.get("practical_exercises", []),
                status=m_data.get("status", "not_started"),
                estimated_hours=m_data.get("estimated_hours", 0.0),
                completed_hours=m_data.get("completed_hours", 0.0),
                order_index=m_data.get("order_index", 0),
                completion_notes=m_data.get("completion_notes"),
            )
            db.add(milestone)

        db.commit()
        db.refresh(roadmap)
        return roadmap

    @classmethod
    def get_user_roadmaps(
        cls,
        db: Session,
        user: User,
        status: Optional[str] = None,
    ) -> list[LearningRoadmap]:
        """List roadmaps owned by user, with optional status filter."""
        query = db.query(LearningRoadmap).filter(LearningRoadmap.user_id == user.id)
        if status:
            query = query.filter(LearningRoadmap.status == status)
        return query.order_by(LearningRoadmap.created_at.desc()).all()

    @classmethod
    def get_roadmap_detail(
        cls,
        db: Session,
        user: User,
        roadmap_id: uuid.UUID,
    ) -> LearningRoadmap:
        """Retrieve roadmap by ID, enforcing tenant ownership."""
        roadmap = (
            db.query(LearningRoadmap)
            .filter(
                LearningRoadmap.id == roadmap_id,
                LearningRoadmap.user_id == user.id,
            )
            .first()
        )
        if not roadmap:
            raise NotFoundError(f"Learning roadmap '{roadmap_id}' not found.")
        return roadmap

    @classmethod
    def update_roadmap_status(
        cls,
        db: Session,
        user: User,
        roadmap_id: uuid.UUID,
        status: str,
    ) -> LearningRoadmap:
        """Update roadmap status."""
        roadmap = cls.get_roadmap_detail(db, user, roadmap_id)
        roadmap.status = status
        if status == "completed" and not roadmap.completed_at:
            roadmap.completed_at = datetime.now(timezone.utc)
            roadmap.completion_percentage = 100.0
        db.commit()
        db.refresh(roadmap)
        return roadmap

    @classmethod
    def delete_roadmap(
        cls,
        db: Session,
        user: User,
        roadmap_id: uuid.UUID,
    ) -> bool:
        """Delete user roadmap."""
        roadmap = cls.get_roadmap_detail(db, user, roadmap_id)
        db.delete(roadmap)
        db.commit()
        return True

    @classmethod
    def update_milestone(
        cls,
        db: Session,
        user: User,
        milestone_id: uuid.UUID,
        update: LearningMilestoneUpdate,
    ) -> LearningMilestone:
        """Update milestone status, hours spent, exercises, and recalculate parent completion."""
        milestone = (
            db.query(LearningMilestone)
            .join(LearningRoadmap, LearningMilestone.roadmap_id == LearningRoadmap.id)
            .filter(
                LearningMilestone.id == milestone_id,
                LearningRoadmap.user_id == user.id,
            )
            .first()
        )
        if not milestone:
            raise NotFoundError(f"Milestone '{milestone_id}' not found.")

        if update.status is not None:
            milestone.status = update.status
            if update.status == "completed":
                milestone.completed_at = datetime.now(timezone.utc)
                if milestone.completed_hours <= 0.0:
                    milestone.completed_hours = milestone.estimated_hours

        if update.completed_hours is not None:
            milestone.completed_hours = update.completed_hours

        if update.completion_notes is not None:
            milestone.completion_notes = update.completion_notes

        if update.practical_exercises is not None:
            milestone.practical_exercises = update.practical_exercises

        # Recalculate roadmap progress
        roadmap = milestone.roadmap
        all_milestones = roadmap.milestones
        total_hours = sum(m.estimated_hours for m in all_milestones)
        completed_hours = sum(m.completed_hours for m in all_milestones)

        roadmap.total_estimated_hours = total_hours
        roadmap.completed_hours = completed_hours
        roadmap.completion_percentage = (
            round((completed_hours / total_hours * 100.0), 1) if total_hours > 0 else 0.0
        )
        if all(m.status in ("completed", "skipped") for m in all_milestones):
            roadmap.status = "completed"
            roadmap.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(milestone)
        return milestone

    # -----------------------------------------------------------------------
    # 3. Learning Resource Discovery & Management
    # -----------------------------------------------------------------------

    @classmethod
    def ensure_curated_resources_seeded(cls, db: Session) -> None:
        """Idempotently seed the curated public educational catalog into database."""
        curated_count = (
            db.query(func.count(LearningResource.id))
            .filter(LearningResource.is_curated.is_(True))
            .scalar()
            or 0
        )
        if curated_count >= len(CURATED_RESOURCES):
            return

        for r_data in CURATED_RESOURCES:
            exists = (
                db.query(LearningResource)
                .filter(
                    LearningResource.url == r_data["url"],
                    LearningResource.is_curated.is_(True),
                )
                .first()
            )
            if not exists:
                res = LearningResource(
                    skill=r_data["skill"],
                    title=r_data["title"],
                    provider=r_data["provider"],
                    url=r_data["url"],
                    cost_tier=r_data["cost_tier"],
                    resource_type=r_data["resource_type"],
                    difficulty=r_data["difficulty"],
                    estimated_hours=r_data["estimated_hours"],
                    description=r_data.get("description"),
                    is_curated=True,
                    user_id=None,
                )
                db.add(res)
        db.commit()

    @classmethod
    def list_resources(
        cls,
        db: Session,
        user: User,
        skill: Optional[str] = None,
        difficulty: Optional[str] = None,
        cost_tier: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 50,
    ) -> list[LearningResource]:
        """List resources accessible to user (curated catalog + user custom bookmarks)."""
        cls.ensure_curated_resources_seeded(db)

        query = db.query(LearningResource).filter(
            or_(
                LearningResource.is_curated.is_(True),
                LearningResource.user_id == user.id,
            )
        )
        if skill:
            query = query.filter(LearningResource.skill.ilike(f"%{skill}%"))
        if difficulty:
            query = query.filter(LearningResource.difficulty == difficulty)
        if cost_tier:
            query = query.filter(LearningResource.cost_tier == cost_tier)
        if search:
            query = query.filter(
                or_(
                    LearningResource.title.ilike(f"%{search}%"),
                    LearningResource.description.ilike(f"%{search}%"),
                    LearningResource.provider.ilike(f"%{search}%"),
                )
            )

        return (
            query.order_by(
                LearningResource.is_curated.desc(),
                LearningResource.created_at.desc(),
            )
            .limit(limit)
            .all()
        )

    @classmethod
    def create_custom_resource(
        cls,
        db: Session,
        user: User,
        data: LearningResourceCreate,
    ) -> LearningResource:
        """Allow candidate to add custom learning bookmarks."""
        resource = LearningResource(
            skill=data.skill,
            title=data.title,
            provider=data.provider,
            url=data.url,
            cost_tier=data.cost_tier,
            resource_type=data.resource_type,
            difficulty=data.difficulty,
            estimated_hours=data.estimated_hours,
            description=data.description,
            is_curated=False,
            user_id=user.id,
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        return resource

    @classmethod
    def delete_custom_resource(
        cls,
        db: Session,
        user: User,
        resource_id: uuid.UUID,
    ) -> bool:
        """Delete user-added custom bookmark."""
        res = (
            db.query(LearningResource)
            .filter(
                LearningResource.id == resource_id,
                LearningResource.user_id == user.id,
                LearningResource.is_curated.is_(False),
            )
            .first()
        )
        if not res:
            raise NotFoundError("Custom learning resource not found.")
        db.delete(res)
        db.commit()
        return True

    # -----------------------------------------------------------------------
    # 4. Practical Learning Activities & Time Tracking
    # -----------------------------------------------------------------------

    @classmethod
    def log_activity(
        cls,
        db: Session,
        user: User,
        data: LearningActivityCreate,
    ) -> LearningActivity:
        """Record study/practice activity hours and notes."""
        if data.roadmap_id:
            # Verify roadmap belongs to user
            cls.get_roadmap_detail(db, user, data.roadmap_id)

        activity = LearningActivity(
            user_id=user.id,
            roadmap_id=data.roadmap_id,
            milestone_id=data.milestone_id,
            project_id=data.project_id,
            skill=data.skill,
            activity_type=data.activity_type,
            hours_spent=data.hours_spent,
            notes=data.notes,
        )
        db.add(activity)

        # Update roadmap completed hours if linked
        if data.roadmap_id:
            roadmap = (
                db.query(LearningRoadmap).filter(LearningRoadmap.id == data.roadmap_id).first()
            )
            if roadmap:
                roadmap.completed_hours += data.hours_spent
                if roadmap.total_estimated_hours > 0:
                    roadmap.completion_percentage = min(
                        100.0,
                        round((roadmap.completed_hours / roadmap.total_estimated_hours * 100.0), 1),
                    )

        db.commit()
        db.refresh(activity)
        return activity

    @classmethod
    def get_activities(
        cls,
        db: Session,
        user: User,
        limit: int = 50,
    ) -> list[LearningActivity]:
        """List user's study activity logs."""
        return (
            db.query(LearningActivity)
            .filter(LearningActivity.user_id == user.id)
            .order_by(LearningActivity.created_at.desc())
            .limit(limit)
            .all()
        )

    # -----------------------------------------------------------------------
    # 5. Project Recommendations & Portfolio Tracking
    # -----------------------------------------------------------------------

    @classmethod
    def get_project_recommendations(
        cls,
        db: Session,
        user: User,
        target_role: Optional[str] = None,
        limit: int = 4,
    ) -> list[ProjectRecommendationResponse]:
        """Generate structured project recommendations tailored to missing skills."""
        gaps = cls.get_skill_gaps(db, user)
        missing_names = [it.skill for it in gaps.top_recommended_skills]
        role = target_role or (gaps.target_roles[0] if gaps.target_roles else "backend_python")

        raw_projects = RoadmapGenerationEngine.get_project_recommendations(
            target_role=role,
            missing_skills=missing_names,
            limit=limit,
        )
        responses: list[ProjectRecommendationResponse] = []
        for p in raw_projects:
            responses.append(
                ProjectRecommendationResponse(
                    title=p["title"],
                    objective=p["objective"],
                    tech_stack=p["tech_stack"],
                    target_skills=p["target_skills"],
                    functional_requirements=p["functional_requirements"],
                    suggested_milestones=[
                        SuggestedMilestone(**m) for m in p["suggested_milestones"]
                    ],
                    expected_portfolio_outcome=p["expected_portfolio_outcome"],
                    difficulty=p["difficulty"],
                    estimated_hours=p["estimated_hours"],
                )
            )
        return responses

    @classmethod
    def create_project(
        cls,
        db: Session,
        user: User,
        data: LearningProjectCreate,
    ) -> LearningProject:
        """Create a new practical project milestone to track."""
        if data.roadmap_id:
            cls.get_roadmap_detail(db, user, data.roadmap_id)

        milestones_dicts = [m.model_dump() for m in data.suggested_milestones]

        project = LearningProject(
            user_id=user.id,
            roadmap_id=data.roadmap_id,
            title=data.title,
            objective=data.objective,
            tech_stack=data.tech_stack,
            target_skills=data.target_skills,
            functional_requirements=data.functional_requirements,
            suggested_milestones=milestones_dicts,
            status=data.status,
            repository_url=data.repository_url,
            live_demo_url=data.live_demo_url,
            architecture_summary=data.architecture_summary,
            evidence_notes=data.evidence_notes,
            portfolio_ready=bool(data.repository_url and data.architecture_summary),
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    @classmethod
    def update_project(
        cls,
        db: Session,
        user: User,
        project_id: uuid.UUID,
        update: LearningProjectUpdate,
    ) -> LearningProject:
        """Update project implementation details, repository links, and portfolio readiness."""
        project = (
            db.query(LearningProject)
            .filter(
                LearningProject.id == project_id,
                LearningProject.user_id == user.id,
            )
            .first()
        )
        if not project:
            raise NotFoundError(f"Learning project '{project_id}' not found.")

        if update.status is not None:
            project.status = update.status
            if update.status == "completed" and not project.completed_at:
                project.completed_at = datetime.now(timezone.utc)

        if update.repository_url is not None:
            project.repository_url = update.repository_url

        if update.live_demo_url is not None:
            project.live_demo_url = update.live_demo_url

        if update.architecture_summary is not None:
            project.architecture_summary = update.architecture_summary

        if update.evidence_notes is not None:
            project.evidence_notes = update.evidence_notes

        if update.portfolio_ready is not None:
            project.portfolio_ready = update.portfolio_ready
        elif (
            project.repository_url
            and project.architecture_summary
            and project.status == "completed"
        ):
            project.portfolio_ready = True

        if update.suggested_milestones is not None:
            project.suggested_milestones = [m.model_dump() for m in update.suggested_milestones]

        db.commit()
        db.refresh(project)
        return project

    @classmethod
    def list_projects(
        cls,
        db: Session,
        user: User,
    ) -> list[LearningProject]:
        """List candidate's projects ordered by creation date."""
        return (
            db.query(LearningProject)
            .filter(LearningProject.user_id == user.id)
            .order_by(LearningProject.created_at.desc())
            .all()
        )

    # -----------------------------------------------------------------------
    # 6. Learning Analytics
    # -----------------------------------------------------------------------

    @classmethod
    def get_analytics(cls, db: Session, user: User) -> LearningAnalyticsResponse:
        """Synthesize learning time, milestone completion, and project readiness metrics."""
        # Total learning hours from activities
        total_hours = (
            db.query(func.coalesce(func.sum(LearningActivity.hours_spent), 0.0))
            .filter(LearningActivity.user_id == user.id)
            .scalar()
            or 0.0
        )

        # Weekly learning hours (past 7 days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        weekly_hours = (
            db.query(func.coalesce(func.sum(LearningActivity.hours_spent), 0.0))
            .filter(
                LearningActivity.user_id == user.id,
                LearningActivity.created_at >= seven_days_ago,
            )
            .scalar()
            or 0.0
        )

        # Roadmaps count
        active_roadmaps = (
            db.query(func.count(LearningRoadmap.id))
            .filter(
                LearningRoadmap.user_id == user.id,
                LearningRoadmap.status == "active",
            )
            .scalar()
            or 0
        )
        completed_roadmaps = (
            db.query(func.count(LearningRoadmap.id))
            .filter(
                LearningRoadmap.user_id == user.id,
                LearningRoadmap.status == "completed",
            )
            .scalar()
            or 0
        )

        # Milestones count
        completed_milestones = (
            db.query(func.count(LearningMilestone.id))
            .join(LearningRoadmap, LearningMilestone.roadmap_id == LearningRoadmap.id)
            .filter(
                LearningRoadmap.user_id == user.id,
                LearningMilestone.status == "completed",
            )
            .scalar()
            or 0
        )

        # Projects count
        completed_projects = (
            db.query(func.count(LearningProject.id))
            .filter(
                LearningProject.user_id == user.id,
                LearningProject.status == "completed",
            )
            .scalar()
            or 0
        )
        portfolio_ready_projects = (
            db.query(func.count(LearningProject.id))
            .filter(
                LearningProject.user_id == user.id,
                LearningProject.portfolio_ready.is_(True),
            )
            .scalar()
            or 0
        )

        # Hours by skill
        skill_hours_rows = (
            db.query(
                LearningActivity.skill,
                func.sum(LearningActivity.hours_spent).label("skill_hours"),
            )
            .filter(LearningActivity.user_id == user.id)
            .group_by(LearningActivity.skill)
            .all()
        )
        hours_by_skill = {row[0]: round(float(row[1]), 1) for row in skill_hours_rows}

        return LearningAnalyticsResponse(
            total_learning_hours=round(float(total_hours), 1),
            active_roadmaps_count=active_roadmaps,
            completed_roadmaps_count=completed_roadmaps,
            completed_milestones_count=completed_milestones,
            in_progress_skills_count=len(hours_by_skill),
            completed_projects_count=completed_projects,
            portfolio_ready_projects_count=portfolio_ready_projects,
            weekly_hours_spent=round(float(weekly_hours), 1),
            hours_by_skill=hours_by_skill,
        )
