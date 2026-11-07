from typing import Any, Optional

from app.core.config import settings
from app.core.logging import logger
from app.services.ai.base import AIConfigurationError, AIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider


def get_ai_provider(provider_name: Optional[str] = None, allow_fallback: bool = True) -> AIProvider:
    """Resolve configured AI provider based on environment routing and priority.

    Priority:
    1. Explicitly requested provider (if specified).
    2. Primary configured provider (default: AI_PRIMARY_PROVIDER or AI_PROVIDER or 'openai').
    3. Secondary configured provider (default: 'gemini') if primary is unconfigured and
       allow_fallback=True.
    """
    raw_provider = provider_name or settings.AI_PROVIDER
    selected = (raw_provider or "").lower().strip()

    if selected == "none":
        raise AIConfigurationError(
            "AI features are disabled (AI_PROVIDER='none'). "
            "Configure OPENAI_API_KEY or GEMINI_API_KEY to enable AI intelligence."
        )

    if provider_name:
        return _create_provider(selected)

    if selected not in ("openai", "gemini"):
        raise AIConfigurationError(
            f"Unsupported AI provider '{selected}'. Supported providers are 'openai' and 'gemini'."
        )

    # 1. Try Primary Provider (OpenAI by default, or settings.AI_PRIMARY_PROVIDER)
    primary_name = getattr(settings, "AI_PRIMARY_PROVIDER", selected or "openai").lower().strip()
    primary = _create_provider(primary_name)
    if primary.is_configured:
        return primary

    # 2. Try Secondary Provider if fallback allowed (Gemini by default)
    if allow_fallback:
        secondary_name = getattr(settings, "AI_SECONDARY_PROVIDER", "gemini").lower().strip()
        if secondary_name != primary_name:
            secondary = _create_provider(secondary_name)
            if secondary.is_configured:
                logger.info(
                    "Primary AI provider '%s' unconfigured; dynamically routed to secondary '%s'",
                    primary_name,
                    secondary_name,
                )
                return secondary

    # If neither is configured, return primary provider instance
    # (which will raise AIConfigurationError on call)
    return primary


def _create_provider(name: str) -> AIProvider:
    """Instantiate a provider by name."""
    if name == "openai":
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
        )
    elif name == "gemini":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )
    raise AIConfigurationError(
        f"Unsupported AI provider '{name}'. Supported providers are 'openai' and 'gemini'."
    )


def test_all_ai_providers() -> dict[str, Any]:
    """Diagnostic helper testing connectivity to all configured AI providers."""
    openai_prov = _create_provider("openai")
    gemini_prov = _create_provider("gemini")

    return {
        "primary_provider": getattr(settings, "AI_PRIMARY_PROVIDER", "openai"),
        "secondary_provider": getattr(settings, "AI_SECONDARY_PROVIDER", "gemini"),
        "openai": openai_prov.test_connection(),
        "gemini": gemini_prov.test_connection(),
    }
