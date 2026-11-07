import time
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.services.orchestration.agents.base_agent import AgentResult, BaseAgent
from app.services.orchestration.candidate_context import SharedCandidateContext


class CareerStrategyAgent(BaseAgent):
    """Primary coordinator synthesizing career goals, learning, and action plans."""

    name = "career_strategy"
    description = "Synthesizes multi-module insights into a prioritized weekly career action plan."

    def run(
        self,
        db: Session,
        context: SharedCandidateContext,
        params: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        start_time = time.time()
        params = params or {}
        target_role = context.target_job_title or (
            context.target_roles[0] if context.target_roles else "Software Engineer"
        )
        readiness = context.career_readiness_score

        # 1. Synthesize prioritized career actions
        actions = []

        # Application action
        if context.active_applications_count < 3:
            actions.append(
                {
                    "priority": "high",
                    "category": "applications",
                    "action": f"Apply to 2-3 verified {target_role} jobs with tailored resumes.",
                    "rationale": (
                        "Pipeline has few active applications; steady submission cadence "
                        "maximizes interview volume."
                    ),
                    "deep_link": "/dashboard/discovery",
                }
            )
        else:
            actions.append(
                {
                    "priority": "medium",
                    "category": "applications",
                    "action": "Follow up respectfully on active applications older than 5 days.",
                    "rationale": (
                        f"You currently have {context.active_applications_count} applications "
                        "in flight."
                    ),
                    "deep_link": "/dashboard/applications",
                }
            )

        # Networking action
        actions.append(
            {
                "priority": "high",
                "category": "networking",
                "action": "Connect with 2 verified tech recruiters using ≤300 char LinkedIn notes.",
                "rationale": (
                    "Direct recruiter outreach increases response probability compared to "
                    "portal-only applications."
                ),
                "deep_link": "/dashboard/networking",
            }
        )

        # Skill & Interview prep action
        actions.append(
            {
                "priority": "medium",
                "category": "interview_prep",
                "action": (
                    f"Complete 1 mock interview session focused on {target_role} system design "
                    "and STAR project review."
                ),
                "rationale": "Mock practice with rubric scoring boosts confidence.",
                "deep_link": "/dashboard/interview-prep",
            }
        )

        # Portfolio action
        if not context.portfolio_published:
            actions.append(
                {
                    "priority": "medium",
                    "category": "portfolio",
                    "action": "Publish your Portfolio Studio profile to showcase projects.",
                    "rationale": "A published evidence-backed portfolio increases recruiter trust.",
                    "deep_link": "/dashboard/portfolio-studio",
                }
            )

        # Learning roadmap recommendation
        recommended_tracks = ["Backend Python Track", "Full Stack Web Track", "AI/ML Track"]

        latency = int((time.time() - start_time) * 1000)

        proposals = [
            {
                "id": "action_open_career_command_center",
                "action_type": "view_command_center",
                "title": f"Review Command Center ({round(readiness)}% Readiness)",
                "description": "Pipeline funnel, skills gap analysis, and conversion analytics.",
                "deep_link": "/dashboard/career-command-center",
                "requires_approval": False,
            },
            {
                "id": "action_open_learning_roadmap",
                "action_type": "start_learning_roadmap",
                "title": "Explore Recommended Learning Roadmap",
                "description": f"Curated 4-stage technical track for {target_role}.",
                "deep_link": "/dashboard/learning-roadmap",
                "requires_approval": False,
            },
        ]

        summary = (
            f"Formulated career strategy for {context.full_name} targeting {target_role} "
            f"(Readiness: {round(readiness)}%). Established {len(actions)} prioritized weekly "
            f"milestones across applications, networking, mock interviews, and portfolio."
        )

        return AgentResult(
            agent_name=self.name,
            operation="synthesize_strategy",
            status="completed",
            summary=summary,
            data={
                "target_role": target_role,
                "career_readiness_score": round(readiness, 1),
                "weekly_action_plan": actions,
                "recommended_tracks": recommended_tracks,
                "active_pipeline_summary": {
                    "applications": context.active_applications_count,
                    "interviews": context.interviews_scheduled_count,
                    "projects": len(context.verified_projects),
                },
            },
            action_proposals=proposals,
            latency_ms=latency,
            tokens_used=160,
            provider="deterministic",
        )
