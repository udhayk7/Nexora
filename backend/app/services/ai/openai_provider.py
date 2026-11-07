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


class OpenAIProvider(AIProvider):
    """OpenAI Provider using official openai SDK with structured outputs and model routing."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None) -> None:
        self.name = "openai"
        self._api_key = api_key or settings.OPENAI_API_KEY
        self.model_name = model or settings.OPENAI_MODEL

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key.strip())

    def get_model_for_tier(self, tier: ModelTier = "routine") -> str:
        """Route to economical model for routine tasks, or stronger model for complex work."""
        if tier == "strong":
            return settings.OPENAI_STRONG_MODEL
        return self.model_name

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost based on OpenAI published rates."""
        if "gpt-4o-mini" in model:
            # $0.15 / 1M prompt, $0.60 / 1M completion
            return round((prompt_tokens * 0.00000015) + (completion_tokens * 0.0000006), 6)
        # gpt-4o standard: $2.50 / 1M prompt, $10.00 / 1M completion
        return round((prompt_tokens * 0.0000025) + (completion_tokens * 0.00001), 6)

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
        model = self.get_model_for_tier("routine")

        messages = [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ]

        max_retries = max(0, settings.AI_MAX_RETRIES)
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Calling OpenAI API (model: {model}, attempt: {attempt + 1})")
                response = client.beta.chat.completions.parse(
                    model=model,
                    messages=messages,
                    response_format=ResumeAnalysisResult,
                    temperature=0.2,
                )

                parsed_message = response.choices[0].message
                if parsed_message.refusal:
                    raise AIProviderError(f"OpenAI refused request: {parsed_message.refusal}")

                validated_result = parsed_message.parsed
                if not validated_result:
                    content_str = parsed_message.content or ""
                    validated_result = ResumeAnalysisResult.model_validate(json.loads(content_str))

                prompt_tokens: Optional[int] = None
                completion_tokens: Optional[int] = None
                total_tokens: Optional[int] = None
                estimated_cost: Optional[float] = None

                if response.usage:
                    prompt_tokens = response.usage.prompt_tokens
                    completion_tokens = response.usage.completion_tokens
                    total_tokens = response.usage.total_tokens
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

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        start_time = time.time()
        response = client.chat.completions.create(**kwargs)
        latency_ms = int((time.time() - start_time) * 1000)

        content = response.choices[0].message.content or ""
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        total_tokens = response.usage.total_tokens if response.usage else 0
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

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        if schema:
            response = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                response_format=schema,
                temperature=0.2,
            )
            parsed_message = response.choices[0].message
            validated = parsed_message.parsed
            result_dict = (
                validated.model_dump()
                if hasattr(validated, "model_dump")
                else json.loads(parsed_message.content or "{}")
            )
        else:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            content_str = response.choices[0].message.content or "{}"
            result_dict = json.loads(content_str)

        latency_ms = int((time.time() - start_time) * 1000)
        prompt_tokens = response.usage.prompt_tokens if response.usage else 0
        completion_tokens = response.usage.completion_tokens if response.usage else 0
        total_tokens = response.usage.total_tokens if response.usage else 0
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
                "message": "OPENAI_API_KEY is not set in environment.",
            }

        start_time = time.time()
        try:
            client = self._get_client()
            model = self.get_model_for_tier("routine")
            client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2,
            )
            latency = int((time.time() - start_time) * 1000)
            return {
                "status": "connected",
                "provider": self.name,
                "model": model,
                "latency_ms": latency,
                "message": f"Successfully connected to OpenAI ({model})",
            }
        except Exception as exc:
            latency = int((time.time() - start_time) * 1000)
            err_msg = str(exc)
            # Never expose raw keys in diagnostic output
            return {
                "status": "disconnected",
                "provider": self.name,
                "latency_ms": latency,
                "error": err_msg[:200],
                "message": f"OpenAI connection failed: {err_msg[:120]}",
            }
