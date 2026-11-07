import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import BadRequestError, NotFoundError
from app.models.analysis import ResumeAnalysis
from app.models.application import ApplicationActivity, JobApplication
from app.models.company import Company
from app.models.interview_prep import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewPreparationNote,
    InterviewPreparationSession,
    InterviewQuestion,
)
from app.models.job import Job
from app.models.resume import Resume, ResumeVersion
from app.models.user import User
from app.schemas.analysis import ResumeAnalysisResult
from app.schemas.interview_prep import (
    InterviewAnalyticsResponse,
    InterviewAnswerDetail,
    InterviewAnswerSubmitRequest,
    InterviewEvaluationDetail,
    InterviewNoteCreateRequest,
    InterviewNoteResponse,
    InterviewNoteUpdateRequest,
    InterviewQuestionDetail,
    InterviewReminderCreateRequest,
    InterviewSessionCreateRequest,
    InterviewSessionDetail,
    InterviewSessionSummary,
    ProjectPreparationGenerateRequest,
    ScoreTrendPoint,
    StructuredProjectBreakdown,
)
from app.schemas.notification import NotificationResponse
from app.services.ai.interview_evaluation_engine import InterviewEvaluationEngine
from app.services.ai.interview_prep_engine import InterviewPrepEngine
from app.services.ai.interview_question_engine import InterviewQuestionEngine
from app.services.ai.project_prep_engine import ProjectPrepEngine
from app.services.notification_service import NotificationService


class InterviewPrepService:
    """
    Central orchestration service for AI Interview Preparation, Question Generation,
    Mock Interview Coaching, Project Breakdown, Notes, and Performance Analytics.
    """

    # =========================================================================
    # 1. Session Lifecycle & Plan Generation
    # =========================================================================

    @classmethod
    def create_session(
        cls,
        db: Session,
        user: User,
        data: InterviewSessionCreateRequest,
    ) -> InterviewSessionDetail:
        """Create a new interview preparation session, plan, and question set."""
        job: Optional[Job] = None
        company: Optional[Company] = None
        application: Optional[JobApplication] = None
        resume_version: Optional[ResumeVersion] = None
        analysis_result: Optional[ResumeAnalysisResult] = None

        # Resolve Application if provided
        if data.application_id:
            application = (
                db.query(JobApplication)
                .filter(
                    JobApplication.id == data.application_id,
                    JobApplication.user_id == user.id,
                )
                .first()
            )
            if not application:
                raise NotFoundError("Referenced job application not found")
            if not data.job_id and application.job_id:
                data.job_id = application.job_id
            if not data.company_id and application.company_id:
                data.company_id = application.company_id

        # Resolve Job if provided
        if data.job_id:
            job = db.query(Job).filter(Job.id == data.job_id).first()
            if not job:
                raise NotFoundError("Referenced job opportunity not found")
            if not company and job.company:
                company = job.company

        # Resolve Company if provided
        if data.company_id and not company:
            company = db.query(Company).filter(Company.id == data.company_id).first()

        # Resolve Resume Version & Analysis
        resume_version, analysis_result = cls._resolve_resume_and_analysis(
            db, user, data.resume_version_id
        )

        # Fallback dummy job representation if practicing without a specific job
        if not job:
            job = Job(
                id=uuid.uuid4(),
                title=f"General Software Engineer ({data.category.replace('_', ' ').title()})",
                normalized_title="general software engineer",
                description="Software engineering role focusing on practical problem solving.",
                skills_tags=(
                    analysis_result.skills.supported_skills[:6]
                    if analysis_result and analysis_result.skills
                    else ["Python", "Algorithms", "System Design"]
                ),
                job_url="https://nexora.local/mock-interview",
                job_status="active",
                verification_status="verified",
            )

        # Generate Grounded Preparation Plan
        plan_dict, prep_provider, prep_model, is_fallback = InterviewPrepEngine.generate_plan(
            job=job,
            resume_analysis=analysis_result,
            interview_round=data.interview_round,
            interview_type=data.interview_type,
            user_instructions=data.user_instructions,
        )

        company_name = (
            company.name
            if company
            else (job.company.name if job and job.company else "Target Company")
        )
        round_title = data.interview_round.replace("_", " ").title()
        session_title = f"{job.title} — {round_title} ({data.difficulty.capitalize()})"

        session = InterviewPreparationSession(
            user_id=user.id,
            job_id=job.id
            if job and hasattr(job, "created_at") and job.created_at
            else (job.id if db.query(Job).filter(Job.id == job.id).first() else None),
            company_id=company.id if company else None,
            application_id=application.id if application else None,
            resume_version_id=resume_version.id if resume_version else None,
            title=session_title,
            interview_type=data.interview_type,
            interview_round=data.interview_round,
            difficulty=data.difficulty,
            category=data.category,
            status="in_progress",
            preparation_plan=plan_dict,
            user_instructions=data.user_instructions,
            total_questions=data.question_count,
            completed_questions=0,
            average_score=None,
            provider=prep_provider,
            model=prep_model,
            is_deterministic_fallback=is_fallback,
        )
        db.add(session)
        db.flush()

        # Generate Questions Set
        questions_raw, q_provider, q_model, _ = InterviewQuestionEngine.generate_questions(
            job=job,
            resume_analysis=analysis_result,
            category=data.category,
            difficulty=data.difficulty,
            question_count=data.question_count,
            user_instructions=data.user_instructions,
            project_name=data.selected_project_name,
        )

        session_questions: list[InterviewQuestion] = []
        for q_data in questions_raw:
            question = InterviewQuestion(
                session_id=session.id,
                question_order=q_data.get("question_order", len(session_questions) + 1),
                category=q_data.get("category", data.category),
                difficulty=q_data.get("difficulty", data.difficulty),
                question_text=q_data["question_text"],
                context_hint=q_data.get("context_hint"),
                expected_points=q_data.get("expected_points", []),
                evaluation_criteria=q_data.get("evaluation_criteria", {}),
                ideal_answer_outline=q_data.get("ideal_answer_outline"),
                project_name=data.selected_project_name,
            )
            db.add(question)
            session_questions.append(question)

        session.total_questions = len(session_questions)
        db.commit()
        db.refresh(session)

        # Audit & Application Timeline
        audit_service.record_event(
            action="interview_prep.session_created",
            resource_type="interview_preparation_session",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(session.id),
            metadata={
                "job_title": job.title,
                "company": company_name,
                "round": data.interview_round,
                "category": data.category,
                "question_count": len(session_questions),
            },
        )

        if application:
            cls._record_application_activity(
                db=db,
                user=user,
                application_id=application.id,
                activity_type="interview_prep_started",
                title=f"Started Interview Prep: {session.title}",
                description=(
                    f"Generated {len(session_questions)} {data.difficulty} "
                    f"{data.category} questions."
                ),
            )

        return cls._build_session_detail(db, session)

    @classmethod
    def list_sessions(
        cls,
        db: Session,
        user: User,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InterviewSessionSummary]:
        """Retrieve paginated list of user's interview preparation sessions."""
        query = db.query(InterviewPreparationSession).filter(
            InterviewPreparationSession.user_id == user.id
        )
        if status:
            query = query.filter(InterviewPreparationSession.status == status)

        sessions = (
            query.order_by(InterviewPreparationSession.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        summaries = []
        for s in sessions:
            job_title = s.job.title if s.job else None
            company_name = (
                s.company.name
                if s.company
                else (s.job.company.name if s.job and s.job.company else None)
            )
            summaries.append(
                InterviewSessionSummary(
                    id=s.id,
                    user_id=s.user_id,
                    job_id=s.job_id,
                    company_id=s.company_id,
                    application_id=s.application_id,
                    resume_version_id=s.resume_version_id,
                    title=s.title,
                    interview_type=s.interview_type,
                    interview_round=s.interview_round,
                    difficulty=s.difficulty,
                    category=s.category,
                    status=s.status,
                    total_questions=s.total_questions,
                    completed_questions=s.completed_questions,
                    average_score=s.average_score,
                    created_at=s.created_at,
                    completed_at=s.completed_at,
                    job_title=job_title,
                    company_name=company_name,
                )
            )
        return summaries

    @classmethod
    def get_session_detail(
        cls,
        db: Session,
        user: User,
        session_id: uuid.UUID,
    ) -> InterviewSessionDetail:
        """Retrieve complete session detail with questions, answers, and evaluations."""
        session = (
            db.query(InterviewPreparationSession)
            .filter(
                InterviewPreparationSession.id == session_id,
                InterviewPreparationSession.user_id == user.id,
            )
            .first()
        )
        if not session:
            raise NotFoundError("Interview preparation session not found")

        return cls._build_session_detail(db, session)

    @classmethod
    def complete_or_abandon_session(
        cls,
        db: Session,
        user: User,
        session_id: uuid.UUID,
        status: str,
    ) -> InterviewSessionDetail:
        """Mark a session as completed or abandoned."""
        if status not in {"completed", "abandoned", "in_progress"}:
            raise BadRequestError("Status must be completed, abandoned, or in_progress")

        session = (
            db.query(InterviewPreparationSession)
            .filter(
                InterviewPreparationSession.id == session_id,
                InterviewPreparationSession.user_id == user.id,
            )
            .first()
        )
        if not session:
            raise NotFoundError("Interview preparation session not found")

        session.status = status
        if status == "completed":
            session.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
        return cls._build_session_detail(db, session)

    # =========================================================================
    # 2. Interactive Mock Interview: Answer Submission & Evaluation
    # =========================================================================

    @classmethod
    def submit_answer(
        cls,
        db: Session,
        user: User,
        session_id: uuid.UUID,
        question_id: uuid.UUID,
        data: InterviewAnswerSubmitRequest,
    ) -> InterviewAnswerDetail:
        """Submit candidate answer, run AI evaluation, update progress and average score."""
        session = (
            db.query(InterviewPreparationSession)
            .filter(
                InterviewPreparationSession.id == session_id,
                InterviewPreparationSession.user_id == user.id,
            )
            .first()
        )
        if not session:
            raise NotFoundError("Interview preparation session not found")

        question = (
            db.query(InterviewQuestion)
            .filter(
                InterviewQuestion.id == question_id,
                InterviewQuestion.session_id == session.id,
            )
            .first()
        )
        if not question:
            raise NotFoundError("Interview question not found in this session")

        # Find or create answer
        answer = (
            db.query(InterviewAnswer)
            .filter(
                InterviewAnswer.question_id == question.id,
                InterviewAnswer.user_id == user.id,
            )
            .first()
        )
        if not answer:
            answer = InterviewAnswer(
                session_id=session.id,
                question_id=question.id,
                user_id=user.id,
                answer_text=data.answer_text,
                submitted_code=data.submitted_code,
                submitted_language=data.submitted_language,
                time_spent_seconds=data.time_spent_seconds,
            )
            db.add(answer)
            db.flush()
        else:
            answer.answer_text = data.answer_text
            answer.submitted_code = data.submitted_code
            answer.submitted_language = data.submitted_language
            answer.time_spent_seconds = data.time_spent_seconds

        # Evaluate Answer using Evaluation Engine
        eval_dict, eval_provider, eval_model, eval_fallback = (
            InterviewEvaluationEngine.evaluate_answer(
                question=question,
                answer_text=data.answer_text,
                submitted_code=data.submitted_code,
                submitted_language=data.submitted_language,
            )
        )

        evaluation = (
            db.query(InterviewEvaluation).filter(InterviewEvaluation.answer_id == answer.id).first()
        )
        if not evaluation:
            evaluation = InterviewEvaluation(
                answer_id=answer.id,
                session_id=session.id,
                overall_score=eval_dict["overall_score"],
                technical_correctness_score=eval_dict["technical_correctness_score"],
                relevance_score=eval_dict["relevance_score"],
                completeness_score=eval_dict["completeness_score"],
                clarity_score=eval_dict["clarity_score"],
                approach_score=eval_dict["approach_score"],
                communication_score=eval_dict["communication_score"],
                strengths=eval_dict.get("strengths", []),
                missing_points=eval_dict.get("missing_points", []),
                suggested_improvements=eval_dict.get("suggested_improvements", []),
                stronger_answer_example=eval_dict["stronger_answer_example"],
                evaluation_feedback=eval_dict["evaluation_feedback"],
                provider=eval_provider,
                model=eval_model,
                is_deterministic_fallback=eval_fallback,
            )
            db.add(evaluation)
        else:
            evaluation.overall_score = eval_dict["overall_score"]
            evaluation.technical_correctness_score = eval_dict["technical_correctness_score"]
            evaluation.relevance_score = eval_dict["relevance_score"]
            evaluation.completeness_score = eval_dict["completeness_score"]
            evaluation.clarity_score = eval_dict["clarity_score"]
            evaluation.approach_score = eval_dict["approach_score"]
            evaluation.communication_score = eval_dict["communication_score"]
            evaluation.strengths = eval_dict.get("strengths", [])
            evaluation.missing_points = eval_dict.get("missing_points", [])
            evaluation.suggested_improvements = eval_dict.get("suggested_improvements", [])
            evaluation.stronger_answer_example = eval_dict["stronger_answer_example"]
            evaluation.evaluation_feedback = eval_dict["evaluation_feedback"]
            evaluation.provider = eval_provider
            evaluation.model = eval_model
            evaluation.is_deterministic_fallback = eval_fallback

        db.flush()

        # Recalculate Session Progress & Average Score
        all_evals = (
            db.query(InterviewEvaluation).filter(InterviewEvaluation.session_id == session.id).all()
        )
        session.completed_questions = len(all_evals)
        if all_evals:
            session.average_score = round(
                sum(e.overall_score for e in all_evals) / len(all_evals), 1
            )

        if session.completed_questions >= session.total_questions:
            session.status = "completed"
            session.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(answer)
        db.refresh(evaluation)

        # Audit
        audit_service.record_event(
            action="interview_prep.answer_evaluated",
            resource_type="interview_answer",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=str(answer.id),
            metadata={
                "session_id": str(session.id),
                "question_id": str(question.id),
                "score": evaluation.overall_score,
                "category": question.category,
            },
        )

        eval_detail = InterviewEvaluationDetail.model_validate(evaluation)
        return InterviewAnswerDetail(
            id=answer.id,
            session_id=answer.session_id,
            question_id=answer.question_id,
            user_id=answer.user_id,
            answer_text=answer.answer_text,
            submitted_code=answer.submitted_code,
            submitted_language=answer.submitted_language,
            time_spent_seconds=answer.time_spent_seconds,
            created_at=answer.created_at,
            evaluation=eval_detail,
        )

    # =========================================================================
    # 3. Project Deep-Dive Coaching
    # =========================================================================

    @classmethod
    def generate_project_breakdown(
        cls,
        db: Session,
        user: User,
        data: ProjectPreparationGenerateRequest,
    ) -> StructuredProjectBreakdown:
        """Generate structured STAR breakdown for an evidenced project."""
        _, analysis = cls._resolve_resume_and_analysis(db, user, data.resume_version_id)
        job = db.query(Job).filter(Job.id == data.job_id).first() if data.job_id else None

        breakdown_dict, _, _, _ = ProjectPrepEngine.generate_breakdown(
            project_name=data.project_name,
            resume_analysis=analysis,
            job=job,
            user_instructions=data.user_instructions,
        )

        audit_service.record_event(
            action="interview_prep.project_breakdown_generated",
            resource_type="project_preparation",
            actor_type="user",
            actor_id=str(user.id),
            resource_id=data.project_name,
            metadata={"project": data.project_name},
        )

        return StructuredProjectBreakdown.model_validate(breakdown_dict)

    # =========================================================================
    # 4. Preparation Notes & Checklists
    # =========================================================================

    @classmethod
    def create_note(
        cls,
        db: Session,
        user: User,
        data: InterviewNoteCreateRequest,
    ) -> InterviewNoteResponse:
        """Create a new interview preparation note, revision topic, or checklist."""
        note = InterviewPreparationNote(
            user_id=user.id,
            session_id=data.session_id,
            application_id=data.application_id,
            job_id=data.job_id,
            note_type=data.note_type,
            title=data.title,
            content=data.content,
            items=data.items,
            is_pinned=data.is_pinned,
        )
        db.add(note)
        db.commit()
        db.refresh(note)
        return InterviewNoteResponse.model_validate(note)

    @classmethod
    def list_notes(
        cls,
        db: Session,
        user: User,
        note_type: Optional[str] = None,
        session_id: Optional[uuid.UUID] = None,
        application_id: Optional[uuid.UUID] = None,
    ) -> list[InterviewNoteResponse]:
        """List user's preparation notes with optional filtering."""
        query = db.query(InterviewPreparationNote).filter(
            InterviewPreparationNote.user_id == user.id
        )
        if note_type:
            query = query.filter(InterviewPreparationNote.note_type == note_type)
        if session_id:
            query = query.filter(InterviewPreparationNote.session_id == session_id)
        if application_id:
            query = query.filter(InterviewPreparationNote.application_id == application_id)

        notes = query.order_by(
            InterviewPreparationNote.is_pinned.desc(),
            InterviewPreparationNote.updated_at.desc(),
        ).all()
        return [InterviewNoteResponse.model_validate(n) for n in notes]

    @classmethod
    def update_note(
        cls,
        db: Session,
        user: User,
        note_id: uuid.UUID,
        data: InterviewNoteUpdateRequest,
    ) -> InterviewNoteResponse:
        """Update an existing interview preparation note."""
        note = (
            db.query(InterviewPreparationNote)
            .filter(
                InterviewPreparationNote.id == note_id,
                InterviewPreparationNote.user_id == user.id,
            )
            .first()
        )
        if not note:
            raise NotFoundError("Interview preparation note not found")

        if data.title is not None:
            note.title = data.title
        if data.content is not None:
            note.content = data.content
        if data.note_type is not None:
            note.note_type = data.note_type
        if data.items is not None:
            note.items = data.items
        if data.is_pinned is not None:
            note.is_pinned = data.is_pinned

        db.commit()
        db.refresh(note)
        return InterviewNoteResponse.model_validate(note)

    @classmethod
    def delete_note(
        cls,
        db: Session,
        user: User,
        note_id: uuid.UUID,
    ) -> None:
        """Delete an interview note."""
        note = (
            db.query(InterviewPreparationNote)
            .filter(
                InterviewPreparationNote.id == note_id,
                InterviewPreparationNote.user_id == user.id,
            )
            .first()
        )
        if not note:
            raise NotFoundError("Interview preparation note not found")

        db.delete(note)
        db.commit()

    # =========================================================================
    # 5. Performance Analytics
    # =========================================================================

    @classmethod
    def get_analytics(cls, db: Session, user: User) -> InterviewAnalyticsResponse:
        """Calculate performance analytics across all user's completed sessions and answers."""
        sessions = (
            db.query(InterviewPreparationSession)
            .filter(InterviewPreparationSession.user_id == user.id)
            .all()
        )
        total_started = len(sessions)
        completed_sessions = [s for s in sessions if s.status == "completed"]
        total_completed = len(completed_sessions)

        evaluations = (
            db.query(InterviewEvaluation)
            .join(
                InterviewPreparationSession,
                InterviewEvaluation.session_id == InterviewPreparationSession.id,
            )
            .filter(InterviewPreparationSession.user_id == user.id)
            .all()
        )
        total_attempted = len(evaluations)

        if not evaluations:
            return InterviewAnalyticsResponse(
                total_sessions_started=total_started,
                total_sessions_completed=total_completed,
                total_questions_attempted=0,
                overall_average_score=0.0,
                technical_average_score=0.0,
                behavioral_average_score=0.0,
                category_performance={},
                difficulty_performance={},
                strong_areas=[],
                weak_areas=[],
                recommended_revision_topics=[],
                score_trend=[],
            )

        overall_avg = round(sum(e.overall_score for e in evaluations) / len(evaluations), 1)

        # Technical vs Behavioral breakdown
        tech_evals = [
            e for e in evaluations if "behavioral" not in e.answer.question.category.lower()
        ]
        behav_evals = [e for e in evaluations if "behavioral" in e.answer.question.category.lower()]

        tech_avg = (
            round(sum(e.overall_score for e in tech_evals) / len(tech_evals), 1)
            if tech_evals
            else overall_avg
        )
        behav_avg = (
            round(sum(e.overall_score for e in behav_evals) / len(behav_evals), 1)
            if behav_evals
            else overall_avg
        )

        # Category performance
        cat_scores: dict[str, list[float]] = {}
        diff_scores: dict[str, list[float]] = {}
        for e in evaluations:
            cat = e.answer.question.category
            diff = e.answer.question.difficulty
            cat_scores.setdefault(cat, []).append(e.overall_score)
            diff_scores.setdefault(diff, []).append(e.overall_score)

        cat_perf = {k: round(sum(v) / len(v), 1) for k, v in cat_scores.items()}
        diff_perf = {k: round(sum(v) / len(v), 1) for k, v in diff_scores.items()}

        # Strong and weak areas
        strong_areas = [k.replace("_", " ").title() for k, v in cat_perf.items() if v >= 75.0]
        weak_areas = [k.replace("_", " ").title() for k, v in cat_perf.items() if v < 70.0]

        # Recommended revision topics (accumulate from missing points)
        missing_aggregate: list[str] = []
        for e in evaluations:
            if e.overall_score < 75.0 and e.missing_points:
                for pt in e.missing_points:
                    if pt and "no critical omissions" not in pt.lower():
                        missing_aggregate.append(pt[:70])

        recommended_topics = list(dict.fromkeys(missing_aggregate))[:5]
        if not recommended_topics:
            recommended_topics = [
                "System Design Trade-offs",
                "Database Indexing Strategies",
                "Concurrency Patterns",
            ]

        # Score trend chronologically
        trend_points = []
        for s in sorted(completed_sessions, key=lambda x: x.completed_at or x.created_at):
            if s.average_score is not None:
                trend_points.append(
                    ScoreTrendPoint(
                        session_id=s.id,
                        date=s.completed_at or s.created_at,
                        score=s.average_score,
                        title=s.title,
                        category=s.category,
                    )
                )

        return InterviewAnalyticsResponse(
            total_sessions_started=total_started,
            total_sessions_completed=total_completed,
            total_questions_attempted=total_attempted,
            overall_average_score=overall_avg,
            technical_average_score=tech_avg,
            behavioral_average_score=behav_avg,
            category_performance=cat_perf,
            difficulty_performance=diff_perf,
            strong_areas=strong_areas,
            weak_areas=weak_areas,
            recommended_revision_topics=recommended_topics,
            score_trend=trend_points,
        )

    # =========================================================================
    # 6. Notification Reminders Integration
    # =========================================================================

    @classmethod
    def create_interview_reminder(
        cls,
        db: Session,
        user: User,
        data: InterviewReminderCreateRequest,
    ) -> NotificationResponse:
        """Create scheduled interview reminder using existing NotificationService."""
        title = data.reminder_title or "Upcoming Interview Reminder"
        message = (
            data.notes
            or data.custom_message
            or "You have an interview scheduled soon. Review your preparation plan and mock notes."
        )
        scheduled_time = data.remind_at or data.scheduled_at or datetime.now(timezone.utc)
        target_entity_id = data.session_id or data.application_interview_id or data.application_id

        notif = NotificationService.create_notification(
            db=db,
            user_id=user.id,
            notification_type=data.reminder_type or "interview_reminder",
            title=title,
            message=message,
            entity_type="interview_session" if data.session_id else "application_interview",
            entity_id=target_entity_id,
            action_url="/dashboard/interview-prep",
            scheduled_for=scheduled_time,
            delivery_status="pending",
        )

        if not notif:
            # User notifications disabled in preferences
            raise BadRequestError("Notifications are disabled in your user preferences.")

        return NotificationResponse.model_validate(notif)

    # =========================================================================
    # Helpers
    # =========================================================================

    @classmethod
    def _resolve_resume_and_analysis(
        cls,
        db: Session,
        user: User,
        resume_version_id: Optional[uuid.UUID] = None,
    ) -> tuple[Optional[ResumeVersion], ResumeAnalysisResult]:
        """Resolve candidate resume version and parsed AI analysis."""
        version: Optional[ResumeVersion] = None
        if resume_version_id:
            version = (
                db.query(ResumeVersion)
                .join(Resume, Resume.id == ResumeVersion.resume_id)
                .filter(ResumeVersion.id == resume_version_id, Resume.user_id == user.id)
                .first()
            )
            if not version:
                raise NotFoundError("Requested resume version not found")
        else:
            latest_resume = (
                db.query(Resume)
                .filter(Resume.user_id == user.id)
                .order_by(Resume.created_at.desc())
                .first()
            )
            if latest_resume and latest_resume.current_version_id:
                version = (
                    db.query(ResumeVersion)
                    .filter(ResumeVersion.id == latest_resume.current_version_id)
                    .first()
                )

        if not version:
            raise BadRequestError(
                "No resume found. Please upload a resume before starting an Interview Prep session."
            )

        analysis = (
            db.query(ResumeAnalysis)
            .filter(
                ResumeAnalysis.version_id == version.id,
                ResumeAnalysis.status == "completed",
            )
            .order_by(ResumeAnalysis.created_at.desc())
            .first()
        )
        if not analysis:
            raise BadRequestError(
                "Resume has not been analyzed yet. Please run AI analysis on your resume first."
            )

        return version, ResumeAnalysisResult.model_validate(analysis.result)

    @classmethod
    def _build_session_detail(
        cls,
        db: Session,
        session: InterviewPreparationSession,
    ) -> InterviewSessionDetail:
        """Construct full session detail response with populated questions and answers."""
        job_title = session.job.title if session.job else None
        company_name = (
            session.company.name
            if session.company
            else (session.job.company.name if session.job and session.job.company else None)
        )

        question_details = []
        for q in session.questions:
            answer_details = []
            for ans in q.answers:
                eval_detail = (
                    InterviewEvaluationDetail.model_validate(ans.evaluation)
                    if ans.evaluation
                    else None
                )
                answer_details.append(
                    InterviewAnswerDetail(
                        id=ans.id,
                        session_id=ans.session_id,
                        question_id=ans.question_id,
                        user_id=ans.user_id,
                        answer_text=ans.answer_text,
                        submitted_code=ans.submitted_code,
                        submitted_language=ans.submitted_language,
                        time_spent_seconds=ans.time_spent_seconds,
                        created_at=ans.created_at,
                        evaluation=eval_detail,
                    )
                )

            question_details.append(
                InterviewQuestionDetail(
                    id=q.id,
                    session_id=q.session_id,
                    question_order=q.question_order,
                    category=q.category,
                    difficulty=q.difficulty,
                    question_text=q.question_text,
                    context_hint=q.context_hint,
                    expected_points=q.expected_points,
                    evaluation_criteria=q.evaluation_criteria,
                    ideal_answer_outline=q.ideal_answer_outline,
                    project_name=q.project_name,
                    created_at=q.created_at,
                    answers=answer_details,
                )
            )

        return InterviewSessionDetail(
            id=session.id,
            user_id=session.user_id,
            job_id=session.job_id,
            company_id=session.company_id,
            application_id=session.application_id,
            resume_version_id=session.resume_version_id,
            title=session.title,
            interview_type=session.interview_type,
            interview_round=session.interview_round,
            difficulty=session.difficulty,
            category=session.category,
            status=session.status,
            total_questions=session.total_questions,
            completed_questions=session.completed_questions,
            average_score=session.average_score,
            created_at=session.created_at,
            completed_at=session.completed_at,
            job_title=job_title,
            company_name=company_name,
            preparation_plan=session.preparation_plan,
            user_instructions=session.user_instructions,
            provider=session.provider,
            model=session.model,
            is_deterministic_fallback=session.is_deterministic_fallback,
            questions=question_details,
        )

    @classmethod
    def _record_application_activity(
        cls,
        db: Session,
        user: User,
        application_id: uuid.UUID,
        activity_type: str,
        title: str,
        description: str,
    ) -> None:
        """Helper to append an activity event to linked JobApplication."""
        app_rec = (
            db.query(JobApplication)
            .filter(
                JobApplication.id == application_id,
                JobApplication.user_id == user.id,
            )
            .first()
        )
        if not app_rec:
            return

        activity = ApplicationActivity(
            application_id=app_rec.id,
            user_id=user.id,
            activity_type=activity_type,
            title=title,
            description=description,
        )
        db.add(activity)
        db.commit()
