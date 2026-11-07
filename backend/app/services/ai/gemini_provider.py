import json
import time
from typing import Any, Optional

from pydantic import BaseModel

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
    ModelTier,
)
from app.services.ai.prompts import SYSTEM_INSTRUCTION, build_analysis_prompt


class GeminiProvider(AIProvider):
    """Google Gemini AI Provider using official google-genai SDK with model routing."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.name = "gemini"
        self._api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model or settings.GEMINI_MODEL

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def get_model_for_tier(self, tier: ModelTier = "routine") -> str:
        """Route to economical model for routine tasks, or stronger model for complex work."""
        if tier == "strong":
            return settings.GEMINI_STRONG_MODEL
        return self.model_name

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost based on Google Gemini published rates."""
        if "flash" in model.lower():
            # Gemini Flash: ~$0.075 / 1M prompt, ~$0.30 / 1M completion
            return round((prompt_tokens * 0.000000075) + (completion_tokens * 0.0000003), 6)
        # Gemini Pro: ~$1.25 / 1M prompt, ~$5.00 / 1M completion
        return round((prompt_tokens * 0.00000125) + (completion_tokens * 0.000005), 6)

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
        model = self.get_model_for_tier("routine")

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
                logger.info(f"Calling Gemini API (model: {model}, attempt: {attempt + 1})")
                response = client.models.generate_content(
                    model=model,
                    contents=user_prompt,
                    config=config,
                )

                raw_text = response.text
                if not raw_text or not raw_text.strip():
                    raise AIProviderError("Gemini returned an empty response")

                # Validate structured schema
                parsed_json = json.loads(raw_text)
                validated_result = ResumeAnalysisResult.model_validate(parsed_json)

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
                        estimated_cost = self._calculate_cost(
                            model, prompt_tokens, completion_tokens
                        )

                return AIProviderResponse(
                    result=validated_result,
                    provider=self.name,
                    model=model,
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

                if attempt >= max_retries:
                    break
                time.sleep(1)

        logger.error(f"Gemini analysis failed after retries: {last_exception}")
        raise AIProviderError(f"Gemini analysis failed: {last_exception}") from last_exception

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        tier: ModelTier = "routine",
        max_tokens: Optional[int] = None,
    ) -> tuple[str, dict[str, Any]]:
        """Generate open-ended text response with usage telemetry."""
        client = self._get_client()
        model = self.get_model_for_tier(tier)

        from google.genai import types

        config_kwargs: dict[str, Any] = {"temperature": 0.2}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if max_tokens:
            config_kwargs["max_output_tokens"] = max_tokens

        config = types.GenerateContentConfig(**config_kwargs)

        start_time = time.time()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        latency_ms = int((time.time() - start_time) * 1000)

        content = response.text or ""
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        total_tokens = getattr(usage, "total_token_count", 0) if usage else 0
        estimated_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        telemetry = {
            "provider": self.name,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
            "latency_ms": latency_ms,
        }
        return content.strip(), telemetry

    def generate_json(
        self,
        prompt: str,
        schema: Optional[type[BaseModel]] = None,
        system_instruction: Optional[str] = None,
        tier: ModelTier = "routine",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate structured JSON response with usage telemetry."""
        client = self._get_client()
        model = self.get_model_for_tier(tier)

        from google.genai import types

        config_kwargs: dict[str, Any] = {
            "temperature": 0.2,
            "response_mime_type": "application/json",
        }
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if schema:
            config_kwargs["response_schema"] = schema

        config = types.GenerateContentConfig(**config_kwargs)

        start_time = time.time()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        latency_ms = int((time.time() - start_time) * 1000)

        raw_text = response.text or "{}"
        try:
            result_dict = json.loads(raw_text)
        except Exception:
            result_dict = {"raw_output": raw_text}

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        total_tokens = getattr(usage, "total_token_count", 0) if usage else 0
        estimated_cost = self._calculate_cost(model, prompt_tokens, completion_tokens)

        telemetry = {
            "provider": self.name,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost,
            "latency_ms": latency_ms,
        }
        return result_dict, telemetry

    def test_connection(self) -> dict[str, Any]:
        """Perform a safe diagnostic connectivity check without crashing."""
        if not self.is_configured:
            return {
                "status": "unconfigured",
                "provider": self.name,
                "message": "GEMINI_API_KEY is not set in environment.",
            }

        start_time = time.time()
        try:
            client = self._get_client()
            model = self.get_model_for_tier("routine")
            from google.genai import types

            client.models.generate_content(
                model=model,
                contents="ping",
                config=types.GenerateContentConfig(max_output_tokens=2),
            )
            latency = int((time.time() - start_time) * 1000)
            return {
                "status": "connected",
                "provider": self.name,
                "model": model,
                "latency_ms": latency,
                "message": f"Successfully connected to Google Gemini ({model})",
            }
        except Exception as exc:
            latency = int((time.time() - start_time) * 1000)
            err_msg = str(exc)
            return {
                "status": "disconnected",
                "provider": self.name,
                "latency_ms": latency,
                "error": err_msg[:200],
                "message": f"Gemini connection failed: {err_msg[:120]}",
            }
