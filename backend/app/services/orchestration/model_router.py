import logging
from typing import Any

from app.core.config import settings
from app.services.ai.factory import get_ai_provider

logger = logging.getLogger("nexora.orchestration.router")


class ModelRouter:
    """Manages intelligent model selection, token budget routing, and deterministic fallbacks."""

    @classmethod
    def classify_intent_deterministic(cls, prompt: str) -> str:
        """Fast, zero-cost deterministic intent classifier based on keyword patterns."""
        p = prompt.lower().strip()

        # Job search / discovery
        if any(
            w in p
            for w in [
                "find job",
                "search job",
                "discover job",
                "jobs for my profile",
                "suitable job",
                "show jobs",
                "openings",
            ]
        ):
            return "job_discovery_match"

        # Application preparation / tailoring
        if any(
            w in p
            for w in [
                "prepare application",
                "tailor resume",
                "write cover letter",
                "apply for",
                "cover letter",
                "application package",
            ]
        ):
            return "application_prep"

        # Interview coaching
        if any(
            w in p
            for w in [
                "interview",
                "mock interview",
                "prepare me for",
                "interview questions",
                "practice questions",
            ]
        ):
            return "interview_prep"

        # Skill gap analysis & learning roadmaps
        if any(
            w in p
            for w in [
                "skill gap",
                "skills missing",
                "what skills",
                "learn",
                "roadmap",
                "study",
            ]
        ):
            return "skill_gap_roadmap"

        # Recruiter networking
        if any(
            w in p
            for w in [
                "recruiter",
                "networking",
                "linkedin note",
                "outreach",
                "connect with",
                "hiring manager",
            ]
        ):
            return "recruiter_outreach"

        # High-level career strategy & diagnosis
        if any(
            w in p
            for w in [
                "career strategy",
                "action plan",
                "improve my chances",
                "weekly plan",
                "career diagnosis",
                "readiness",
            ]
        ):
            return "career_strategy"

        # Default general career assistant inquiry
        return "general_copilot"

    @classmethod
    def generate_conversational_response(
        cls,
        prompt: str,
        intent: str,
        candidate_summary: dict[str, Any],
        agent_summaries: list[str],
    ) -> tuple[str, dict[str, Any]]:
        """
        Synthesizes final conversational response from agent outputs using AI provider
        if configured, or structured deterministic synthesis if unconfigured.
        """
        provider_name = settings.AI_PROVIDER.lower()
        token_usage = {
            "prompt_tokens": 150,
            "completion_tokens": 200,
            "total_tokens": 350,
            "provider": provider_name,
            "model": "deterministic_synthesis",
        }

        # Check if AI provider can be leveraged
        try:
            provider = get_ai_provider()
            generate_func = getattr(provider, "generate_text", None)
            if callable(generate_func):
                system_instruction = (
                    "You are Nexora's AI Career Copilot. Ground all responses strictly "
                    "in the verified facts and agent findings provided. Present clear next steps."
                )
                agent_context_text = "\n".join(f"- {s}" for s in agent_summaries)
                llm_prompt = (
                    f"Candidate Request: {prompt}\n"
                    f"Intent: {intent}\n"
                    f"Candidate Context: {candidate_summary}\n"
                    f"Specialized Agent Findings:\n{agent_context_text}\n\n"
                    "Provide an actionable, structured response synthesizing the agent findings."
                )

                ai_response = str(
                    generate_func(prompt=llm_prompt, system_instruction=system_instruction)
                )
                token_usage["provider"] = provider.name
                token_usage["model"] = provider.model_name
                return ai_response.strip(), token_usage
        except Exception as exc:
            logger.info(
                "AI provider unavailable or returned error, using deterministic synthesis: %s", exc
            )

        # Robust Deterministic Synthesis
        name = candidate_summary.get("candidate_name", "there")
        target = candidate_summary.get("target_focus", "Software Engineering")
        readiness = candidate_summary.get("readiness_score", 70)

        sections = [
            f"Hello {name}! Based on your qualifications (Career Readiness: {readiness}%), "
            f"here is your career intelligence for {target}:",
        ]

        if agent_summaries:
            sections.append("\n**Key Agent Insights:**")
            for summary in agent_summaries:
                sections.append(f"• {summary}")

        sections.append(
            "\n**Recommended Next Actions:**\n"
            "1. Review the tailored proposals and strong matches card below.\n"
            "2. Tailor your resume before applying to ensure alignment.\n"
            "3. Connect with recruitment contacts in your Networking CRM.\n\n"
            "Ask me to tailor an application, prep for interviews, or explore company intelligence!"
        )

        return "\n".join(sections), token_usage
