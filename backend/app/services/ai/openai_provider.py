import json
import time
from typing import Any, Optional

from app.core.config import settings
from app.core.logging import logger
from app.schemas.analysis import ResumeAnalysisResult
from app.services.ai.base import (
    AIConfigurationError,
    AIProvider,
    AIProviderError,
    AIProviderResponse,
    AIRateLimitError,
    AITimeoutError,
)
from app.services.ai.prompts import SYSTEM_INSTRUCTION, build_analysis_prompt


class OpenAIProvider(AIProvider):
    """OpenAI Provider using official openai SDK with structured outputs."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.name = "openai"
        self._api_key = api_key or settings.OPENAI_API_KEY
        self.model_name = model or settings.OPENAI_MODEL

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def _get_client(self) -> Any:
        if not self.is_configured:
            raise AIConfigurationError(
                "OpenAI API key is not configured. Set OPENAI_API_KEY in environment."
            )
        from openai import OpenAI

        return OpenAI(
            api_key=self._api_key,
            timeout=float(settings.AI_REQUEST_TIMEOUT_SECONDS),
        )

    def analyze_resume(
        self,
        resume_text: str,
        structured_sections: Optional[dict[str, Any]] = None,
    ) -> AIProviderResponse:
        client = self._get_client()
        user_prompt = build_analysis_prompt(resume_text, structured_sections)

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ]

        max_retries = max(0, settings.AI_MAX_RETRIES)
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    f"Calling OpenAI API (model: {self.model_name}, attempt: {attempt + 1})"
                )
                response = client.beta.chat.completions.parse(
                    model=self.model_name,
                    messages=messages,
                    response_format=ResumeAnalysisResult,
                    temperature=0.2,
                )

                parsed_message = response.choices[0].message
                if parsed_message.refusal:
                    raise AIProviderError(f"OpenAI refused request: {parsed_message.refusal}")

                validated_result = parsed_message.parsed
                if not validated_result:
                    # Fallback to content parsing if parsed is None
                    content_str = parsed_message.content or ""
                    validated_result = ResumeAnalysisResult.model_validate(json.loads(content_str))

                # Extract token usage
                prompt_tokens: Optional[int] = None
                completion_tokens: Optional[int] = None
                total_tokens: Optional[int] = None
                estimated_cost: Optional[float] = None

                if response.usage:
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                    total_tokens = response.usage.total_tokens
                    # gpt-4o-mini pricing: ~$0.15 / 1M prompt, ~$0.60 / 1M completion
                    if prompt_tokens is not None and completion_tokens is not None:
                        estimated_cost = round(
                            (prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006),
                            6,
                        )

                return AIProviderResponse(
                    result=validated_result,
                    provider=self.name,
                    model=self.model_name,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=estimated_cost,
                )

            except AIConfigurationError:
                raise
            except Exception as exc:
                last_exception = exc
                err_str = str(exc).lower()

                if "timeout" in err_str:
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    raise AITimeoutError(f"OpenAI request timed out: {exc}") from exc

                if "429" in err_str or "rate limit" in err_str:
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    raise AIRateLimitError("OpenAI rate limit or quota exceeded") from exc

                if attempt >= max_retries:
                    break
                time.sleep(1)

        logger.error(f"OpenAI analysis failed after retries: {last_exception}")
        raise AIProviderError(f"OpenAI analysis failed: {last_exception}") from last_exception

