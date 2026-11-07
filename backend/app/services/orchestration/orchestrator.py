import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.audit import audit_service
from app.core.errors import NotFoundError
from app.models.orchestration import AgentExecutionRecord, CopilotMessage, CopilotSession
from app.models.user import User
from app.schemas.orchestration import (
    AgentExecutionRecordResponse,
    ApprovalActionResponse,
    CopilotMessageResponse,
    CopilotSessionDetailResponse,
    CopilotSessionResponse,
)
from app.services.orchestration.agents import (
    ApplicationPreparationAgent,
    BaseAgent,
    CareerStrategyAgent,
    CompanyIntelligenceAgent,
    InterviewPreparationAgent,
    JobDiscoveryAgent,
    JobMatchingAgent,
    RecruiterNetworkingAgent,
    ResumeIntelligenceAgent,
)
from app.services.orchestration.candidate_context import SharedCandidateContext
from app.services.orchestration.model_router import ModelRouter

logger = logging.getLogger("nexora.orchestration.orchestrator")


class AIOrchestrator:
    """Central AI Orchestration layer coordinating agents, shared context, and Copilot sessions."""

    _agents: dict[str, BaseAgent] = {
        "resume_intelligence": ResumeIntelligenceAgent(),
        "job_discovery": JobDiscoveryAgent(),
        "job_matching": JobMatchingAgent(),
        "company_intelligence": CompanyIntelligenceAgent(),
        "application_preparation": ApplicationPreparationAgent(),
        "recruiter_networking": RecruiterNetworkingAgent(),
        "interview_preparation": InterviewPreparationAgent(),
        "career_strategy": CareerStrategyAgent(),
    }

    @classmethod
    def get_or_create_session(
        cls,
        db: Session,
        user: User,
        session_id: Optional[uuid.UUID] = None,
        title: Optional[str] = None,
        session_type: str = "career_strategy",
    ) -> CopilotSession:
        """Retrieves existing active session or creates a new session."""
        if session_id:
            sess = (
                db.query(CopilotSession)
                .filter(CopilotSession.id == session_id, CopilotSession.user_id == user.id)
                .first()
            )
            if sess:
                return sess

        # Create new session
        context = SharedCandidateContext.build(db, user)
        target_label = context.target_roles[0] if context.target_roles else "General"
        new_sess = CopilotSession(
            id=uuid.uuid4(),
            user_id=user.id,
            title=title or f"Career Strategy ({target_label})",
            session_type=session_type,
            is_active=True,
            context_summary=context.to_lean_summary(),
        )
        db.add(new_sess)
        db.commit()
        db.refresh(new_sess)

        audit_service.record_event(
            action="copilot.session_created",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="copilot_session",
            resource_id=str(new_sess.id),
            metadata={"session_type": session_type},
        )
        return new_sess

    @classmethod
    def list_user_sessions(
        cls, db: Session, user: User, limit: int = 20
    ) -> list[CopilotSessionResponse]:
        """Lists active Copilot sessions for a candidate."""
        sessions = (
            db.query(CopilotSession)
            .filter(CopilotSession.user_id == user.id)
            .order_by(CopilotSession.updated_at.desc())
            .limit(limit)
            .all()
        )
        responses = []
        for s in sessions:
            msg_count = db.query(CopilotMessage).filter(CopilotMessage.session_id == s.id).count()
            responses.append(
                CopilotSessionResponse(
                    id=s.id,
                    user_id=s.user_id,
                    title=s.title,
                    session_type=s.session_type,
                    is_active=s.is_active,
                    context_summary=s.context_summary or {},
                    message_count=msg_count,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )
        return responses

    @classmethod
    def get_session_detail(
        cls, db: Session, user: User, session_id: uuid.UUID
    ) -> CopilotSessionDetailResponse:
        """Retrieves session details including full message history and lean context snapshot."""
        sess = (
            db.query(CopilotSession)
            .filter(CopilotSession.id == session_id, CopilotSession.user_id == user.id)
            .first()
        )
        if not sess:
            raise NotFoundError(f"Copilot session {session_id} not found.")

        messages = (
            db.query(CopilotMessage)
            .filter(CopilotMessage.session_id == sess.id)
            .order_by(CopilotMessage.created_at.asc())
            .all()
        )

        msg_responses = [
            CopilotMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                intent=m.intent,
                agent_trace=m.agent_trace or [],
                action_proposals=m.action_proposals or [],
                token_usage=m.token_usage or {},
                created_at=m.created_at,
            )
            for m in messages
        ]

        sess_resp = CopilotSessionResponse(
            id=sess.id,
            user_id=sess.user_id,
            title=sess.title,
            session_type=sess.session_type,
            is_active=sess.is_active,
            context_summary=sess.context_summary or {},
            message_count=len(messages),
            created_at=sess.created_at,
            updated_at=sess.updated_at,
        )

        return CopilotSessionDetailResponse(
            session=sess_resp,
            messages=msg_responses,
            context_snapshot=sess.context_summary or {},
        )

    @classmethod
    def delete_session(cls, db: Session, user: User, session_id: uuid.UUID) -> dict[str, str]:
        """Deletes a Copilot session and cascades deletion of its messages."""
        sess = (
            db.query(CopilotSession)
            .filter(CopilotSession.id == session_id, CopilotSession.user_id == user.id)
            .first()
        )
        if not sess:
            raise NotFoundError(f"Copilot session {session_id} not found.")

        db.delete(sess)
        db.commit()
        return {"status": "success", "message": f"Copilot session {session_id} deleted."}

    @classmethod
    def process_message(
        cls,
        db: Session,
        user: User,
        session_id: uuid.UUID,
        prompt: str,
        target_job_id: Optional[uuid.UUID] = None,
        target_company_id: Optional[uuid.UUID] = None,
    ) -> CopilotMessageResponse:
        """Central orchestration flow: Classifies intent, plans pipeline, and records history."""
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        sess = (
            db.query(CopilotSession)
            .filter(CopilotSession.id == session_id, CopilotSession.user_id == user.id)
            .first()
        )
        if not sess:
            raise NotFoundError(f"Copilot session {session_id} not found.")

        # 1. Record User Message
        user_msg = CopilotMessage(
            id=uuid.uuid4(),
            session_id=sess.id,
            user_id=user.id,
            role="user",
            content=prompt.strip(),
            intent=None,
            agent_trace=[],
            action_proposals=[],
            token_usage={},
        )
        db.add(user_msg)
        db.flush()

        # 2. Build Shared Candidate Context
        context = SharedCandidateContext.build(
            db,
            user,
            target_job_id=target_job_id,
            target_company_id=target_company_id,
        )

        # 3. Classify Intent
        intent = ModelRouter.classify_intent_deterministic(prompt)
        user_msg.intent = intent

        # 4. Multi-Agent Pipeline Plan (Bounded sequence, maximum 4 agents)
        pipeline = cls._resolve_agent_pipeline(intent)

        # 5. Execute Pipeline with Shared Context and History
        agent_traces: list[dict[str, Any]] = []
        action_proposals: list[dict[str, Any]] = []
        agent_summaries: list[str] = []
        intermediate_params: dict[str, Any] = {
            "target_job_id": target_job_id,
            "target_company_id": target_company_id,
        }

        for agent_name in pipeline:
            agent = cls._agents.get(agent_name)
            if not agent:
                continue

            try:
                t0 = time.time()
                result = agent.run(db=db, context=context, params=intermediate_params)
                latency = int((time.time() - t0) * 1000)

                # Record execution audit in DB
                exec_rec = AgentExecutionRecord(
                    id=uuid.uuid4(),
                    workflow_id=workflow_id,
                    session_id=sess.id,
                    user_id=user.id,
                    agent_name=agent_name,
                    operation=result.operation,
                    status=result.status,
                    latency_ms=latency,
                    tokens_used=result.tokens_used,
                    provider=result.provider,
                    requires_approval=result.requires_approval,
                    approval_state="pending" if result.requires_approval else "none",
                    input_context_summary=context.to_lean_summary(),
                    output_payload=result.data,
                    error_message=result.error_message,
                )
                db.add(exec_rec)
                db.flush()

                # Add trace step
                agent_traces.append(
                    {
                        "agent_name": agent_name,
                        "operation": result.operation,
                        "status": result.status,
                        "latency_ms": latency,
                        "reasoning_summary": result.summary,
                        "output_summary": dict(list(result.data.items())[:3]),
                    }
                )
                agent_summaries.append(result.summary)

                # Collect action proposals
                if result.action_proposals:
                    action_proposals.extend(result.action_proposals)

                # Feed forward relevant data to downstream agents
                if "discovered_jobs" in result.data:
                    intermediate_params["jobs"] = result.data["discovered_jobs"]
                if "company" in result.data:
                    intermediate_params["company_name"] = result.data["company"].get("name")

            except Exception as exc:
                logger.error(
                    "Agent %s failed in workflow %s: %s",
                    agent_name,
                    workflow_id,
                    exc,
                    exc_info=True,
                )
                agent_traces.append(
                    {
                        "agent_name": agent_name,
                        "operation": "execute",
                        "status": "failed",
                        "latency_ms": 0,
                        "reasoning_summary": f"Execution halted: {exc}",
                    }
                )

        # 6. Synthesize Final Conversational Output
        final_content, token_usage = ModelRouter.generate_conversational_response(
            prompt=prompt,
            intent=intent,
            candidate_summary=context.to_lean_summary(),
            agent_summaries=agent_summaries,
        )

        # 7. Record Assistant Message
        assistant_msg = CopilotMessage(
            id=uuid.uuid4(),
            session_id=sess.id,
            user_id=user.id,
            role="assistant",
            content=final_content,
            intent=intent,
            agent_trace=agent_traces,
            action_proposals=action_proposals[:5],
            token_usage=token_usage,
        )
        db.add(assistant_msg)

        # Update session timestamp & lean context
        sess.updated_at = now
        sess.context_summary = context.to_lean_summary()

        db.commit()
        db.refresh(assistant_msg)

        audit_service.record_event(
            action="copilot.message_processed",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="copilot_message",
            resource_id=str(assistant_msg.id),
            metadata={
                "intent": intent,
                "workflow_id": workflow_id,
                "agent_count": len(pipeline),
                "proposals_count": len(action_proposals),
            },
        )

        return CopilotMessageResponse(
            id=assistant_msg.id,
            session_id=assistant_msg.session_id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            intent=assistant_msg.intent,
            agent_trace=assistant_msg.agent_trace or [],
            action_proposals=assistant_msg.action_proposals or [],
            token_usage=assistant_msg.token_usage or {},
            created_at=assistant_msg.created_at,
        )

    @classmethod
    def execute_quick_action(
        cls,
        db: Session,
        user: User,
        action: str,
        target_id: Optional[uuid.UUID] = None,
        parameters: Optional[dict[str, Any]] = None,
    ) -> CopilotMessageResponse:
        """Executes a pre-configured quick career action workflow."""
        action_prompts = {
            "career_diagnosis": "Analyze my career readiness, strengths, and critical gaps.",
            "discover_and_match": "Find verified jobs for my profile and rank my top matches.",
            "prepare_application": "Prepare a tailored application pack with cover letter.",
            "interview_coaching": "Create a personalized interview plan and practice questions.",
            "skill_gap_analysis": "What skills am I missing and what tracks do you recommend?",
            "weekly_action_plan": "Create my prioritized weekly career action plan.",
        }
        prompt = action_prompts.get(action, f"Execute career action: {action.replace('_', ' ')}")

        sess = cls.get_or_create_session(
            db, user, title=f"Quick Action: {action.replace('_', ' ').title()}"
        )
        return cls.process_message(
            db=db,
            user=user,
            session_id=sess.id,
            prompt=prompt,
            target_job_id=target_id if action == "prepare_application" else None,
            target_company_id=target_id if action == "company_research" else None,
        )

    @classmethod
    def handle_action_approval(
        cls,
        db: Session,
        user: User,
        record_id: uuid.UUID,
        action: str,
        notes: Optional[str] = None,
    ) -> ApprovalActionResponse:
        """Evaluates and persists candidate approval or rejection for an action record."""
        record = (
            db.query(AgentExecutionRecord)
            .filter(AgentExecutionRecord.id == record_id, AgentExecutionRecord.user_id == user.id)
            .first()
        )
        if not record:
            raise NotFoundError(f"Agent execution record {record_id} not found.")

        now = datetime.now(timezone.utc)
        if action == "approve":
            record.approval_state = "approved"
            record.approved_at = now
            msg = f"Proposal approved for {record.agent_name} ({record.operation})."
        else:
            record.approval_state = "rejected"
            msg = f"Action proposal rejected by candidate for {record.agent_name}."

        db.commit()
        db.refresh(record)

        audit_service.record_event(
            action=f"copilot.proposal_{action}d",
            actor_type="user",
            actor_id=str(user.id),
            resource_type="agent_execution_record",
            resource_id=str(record.id),
            metadata={"notes": notes},
        )

        return ApprovalActionResponse(
            record_id=record.id,
            status=record.approval_state,
            message=msg,
            approved_at=record.approved_at,
        )

    @classmethod
    def get_workflow_executions(
        cls, db: Session, user: User, workflow_id: str
    ) -> list[AgentExecutionRecordResponse]:
        """Lists execution audit records for a specific multi-agent workflow run."""
        records = (
            db.query(AgentExecutionRecord)
            .filter(
                AgentExecutionRecord.workflow_id == workflow_id,
                AgentExecutionRecord.user_id == user.id,
            )
            .order_by(AgentExecutionRecord.created_at.asc())
            .all()
        )
        return [
            AgentExecutionRecordResponse(
                id=r.id,
                workflow_id=r.workflow_id,
                agent_name=r.agent_name,
                operation=r.operation,
                status=r.status,
                latency_ms=r.latency_ms,
                tokens_used=r.tokens_used,
                provider=r.provider,
                model_name=r.model_name,
                requires_approval=r.requires_approval,
                approval_state=r.approval_state,
                approved_at=r.approved_at,
                input_context_summary=r.input_context_summary or {},
                output_payload=r.output_payload or {},
                error_message=r.error_message,
                created_at=r.created_at,
            )
            for r in records
        ]

    @classmethod
    def _resolve_agent_pipeline(cls, intent: str) -> list[str]:
        """Maps classified intent into a bounded, coordinated multi-agent pipeline."""
        pipeline_map = {
            "job_discovery_match": ["resume_intelligence", "job_discovery", "job_matching"],
            "application_prep": [
                "resume_intelligence",
                "company_intelligence",
                "application_preparation",
            ],
            "interview_prep": [
                "resume_intelligence",
                "company_intelligence",
                "interview_preparation",
            ],
            "skill_gap_roadmap": ["resume_intelligence", "job_matching", "career_strategy"],
            "recruiter_outreach": ["company_intelligence", "recruiter_networking"],
            "career_strategy": [
                "resume_intelligence",
                "job_discovery",
                "job_matching",
                "career_strategy",
            ],
        }
        return pipeline_map.get(intent, ["resume_intelligence", "career_strategy"])
