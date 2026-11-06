from typing import Optional

from app.core.config import settings
from app.services.ai.base import AIConfigurationError, AIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.openai_provider import OpenAIProvider


def get_ai_provider(provider_name: Optional[str] = None) -> AIProvider:
    """
    Resolve configured AI provider based on settings or explicit provider request.
    Does not silently switch providers.
    """
    selected = (provider_name or settings.AI_PROVIDER).lower().strip()

    if selected == "gemini":
        return GeminiProvider(
            api_key=settings.GEMINI_API_KEY,
            model=settings.GEMINI_MODEL,
        )
    elif selected == "openai":
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
        )
    elif selected == "none":
        raise AIConfigurationError(
            "AI features are disabled (AI_PROVIDER='none'). "
            "Configure GEMINI_API_KEY or OPENAI_API_KEY to enable AI Resume Intelligence."
        )

    raise AIConfigurationError(
        f"Unsupported AI provider '{selected}'. Supported providers are 'gemini' and 'openai'."
    )
