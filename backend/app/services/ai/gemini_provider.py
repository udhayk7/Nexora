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


class GeminiProvider(AIProvider):
    """Google Gemini AI Provider using official google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.name = "gemini"
        self._api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.GEMINI_MODEL

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def _get_client(self) -> Any:
        if not self.is_configured:
            raise AIConfigurationError(
                "Google Gemini API key is not configured. Set GEMINI_API_KEY in environment."
            )
        from google import genai

        return genai.Client(api_key=self._api_key)

    def analyze_resume(
        self,
        resume_text: str,
        structured_sections: Optional[dict[str, Any]] = None,
    ) -> AIProviderResponse:
        client = self._get_client()
        user_prompt = build_analysis_prompt(resume_text, structured_sections)

        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ResumeAnalysisResult,
            temperature=0.2,
        )

        max_retries = max(0, settings.AI_MAX_RETRIES)
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                logger.info(
                    f"Calling Gemini API (model: {self.model_name}, attempt: {attempt + 1})"
                )
                response = client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=config,
                )

                raw_text = response.text
                if not raw_text or not raw_text.strip():
                    raise AIProviderError("Gemini returned an empty response")

                # Validate structured schema
                parsed_json = json.loads(raw_text)
                validated_result = ResumeAnalysisResult.model_validate(parsed_json)

                # Extract token usage if reliably provided
                prompt_tokens: Optional[int] = None
                completion_tokens: Optional[int] = None
                total_tokens: Optional[int] = None
                estimated_cost: Optional[float] = None

                usage = getattr(response, "usage_metadata", None)
                if usage:
                    prompt_tokens = getattr(usage, "prompt_token_count", None)
                    completion_tokens = getattr(usage, "candidates_token_count", None)
                    total_tokens = getattr(usage, "total_token_count", None)
                    if prompt_tokens is not None and completion_tokens is not None:
                        # Gemini 2.5 Flash pricing: ~$0.075 / 1M prompt, ~$0.30 / 1M completion
                        estimated_cost = round(
                            (prompt_tokens * 0.000000075) + (completion_tokens * 0.0000003),
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

                if "timeout" in err_str or "timed out" in err_str:
                    if attempt < max_retries:
                        time.sleep(1)
                        continue
                    raise AITimeoutError(f"Gemini request timed out: {exc}") from exc

                if "429" in err_str or "quota" in err_str or "resource_exhausted" in err_str:
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    raise AIRateLimitError("Gemini quota or rate limit exceeded") from exc

                # Non-retryable validation or client error
                if attempt >= max_retries:
                    break
                time.sleep(1)

        logger.error(f"Gemini analysis failed after retries: {last_exception}")
        raise AIProviderError(f"Gemini analysis failed: {last_exception}") from last_exception

