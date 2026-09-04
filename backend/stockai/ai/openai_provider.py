"""OpenAIProvider — live AI explanation via the user's own OpenAI key (BYOK).

Implements the AIProvider interface: async generate(prompt, context,
response_schema) -> dict. The key stays server-side (env only). Deterministic
values remain authoritative: after the model responds we OVERRIDE bias and
confidence with the deterministic score, so AI never changes the numbers.
"""
from __future__ import annotations
import json

from openai import (AsyncOpenAI, APIConnectionError, APITimeoutError,
                    AuthenticationError, BadRequestError, RateLimitError,
                    APIStatusError, APIError)

from ..core.config import OPENAI_API_KEY, AI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS
from ..core.logging_config import get_logger

logger = get_logger("stockai.ai.openai")

_FIELDS = ("bias, confidence, summary, bullish_factors[], bearish_factors[], "
           "risks[], invalidation_conditions[], setup_commentary, "
           "missing_data_warnings[]")


class AIProviderError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or OPENAI_API_KEY
        if not key:
            raise AIProviderError("no_key", "OPENAI_API_KEY is not configured")
        self.model = model or AI_MODEL
        self.client = AsyncOpenAI(api_key=key, timeout=30.0, max_retries=0)

    async def generate(self, prompt: str, context: dict,
                       response_schema: dict | None = None) -> dict:
        system = (
            "You are a grounded financial-analysis explainer for a personal Indian "
            "equities research tool. Use ONLY the numbers and facts in the supplied "
            "CONTEXT JSON. Never invent prices, indicators, news or trade levels. If a "
            "fact is absent, say 'data unavailable'. All trade levels (entry/stop/"
            "targets) come from the deterministic Risk Engine and are authoritative — "
            "explain them, never change them. Use research language (bias, potential "
            "setup, hypothetical, risk, invalidation), never guarantees. "
            f"Return ONLY a JSON object with keys: {_FIELDS}. bias must be one of "
            "LONG, SHORT, NEUTRAL; confidence a number 0..1; list fields arrays of short strings."
        )
        user = (f"{prompt}\n\nCONTEXT JSON:\n"
                f"{json.dumps(context, default=str)[:12000]}")
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user}],
                response_format={"type": "json_object"},
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS,
            )
            content = resp.choices[0].message.content or "{}"
            data = json.loads(content)
        except AuthenticationError as e:
            raise AIProviderError("auth", "OpenAI authentication failed; check the API key") from e
        except RateLimitError as e:
            raise AIProviderError("rate_limit", "OpenAI rate limit / quota exceeded") from e
        except (APITimeoutError, APIConnectionError) as e:
            raise AIProviderError("timeout", "OpenAI request timed out / connection error") from e
        except BadRequestError as e:
            raise AIProviderError("bad_request", "OpenAI rejected the request") from e
        except (APIStatusError, APIError) as e:
            raise AIProviderError("api_error", "OpenAI API error") from e
        except json.JSONDecodeError as e:
            raise AIProviderError("invalid_json", "OpenAI returned invalid JSON") from e

        # Deterministic values are authoritative — override AI numbers.
        score = context.get("score") or {}
        det_bias = (score.get("bias") or "").lower()
        data["bias"] = {"bullish": "LONG", "bearish": "SHORT"}.get(det_bias, "NEUTRAL")
        if score.get("confidence") is not None:
            data["confidence"] = score["confidence"]
        data.setdefault("summary", "")
        for k in ("bullish_factors", "bearish_factors", "risks",
                  "invalidation_conditions", "missing_data_warnings"):
            v = data.get(k)
            if not isinstance(v, list):
                data[k] = [] if v is None else [str(v)]
        data["provider"] = self.name
        data["model"] = self.model
        data["prompt_version"] = context.get("prompt_version", "")
        data["grounded"] = True
        return data
