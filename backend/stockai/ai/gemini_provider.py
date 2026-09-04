"""GeminiProvider — fallback AI explanation via Google Gemini (BYOK, server-side).

Implements the AIProvider interface (async generate). Used by AIService as a
FALLBACK when the primary (OpenAI) provider fails. Uses the google-genai SDK
async client with JSON output mode. Deterministic values remain authoritative:
bias/confidence are overridden with the deterministic score after generation.
"""
from __future__ import annotations
import asyncio
import json

from google import genai
from google.genai import types, errors

from ..core.config import GEMINI_API_KEY, GEMINI_MODEL, AI_TEMPERATURE, AI_MAX_TOKENS
from ..core.logging_config import get_logger
from .openai_provider import AIProviderError

logger = get_logger("stockai.ai.gemini")

_FIELDS = ("bias, confidence, summary, bullish_factors[], bearish_factors[], "
           "risks[], invalidation_conditions[], setup_commentary, missing_data_warnings[]")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or GEMINI_API_KEY
        if not key:
            raise AIProviderError("no_key", "GEMINI_API_KEY is not configured")
        self.model = model or GEMINI_MODEL
        self._client = genai.Client(api_key=key)

    async def generate(self, prompt: str, context: dict,
                       response_schema: dict | None = None) -> dict:
        system = (
            "You are a grounded financial-analysis explainer for a personal Indian "
            "equities research tool. Use ONLY the numbers and facts in the supplied "
            "CONTEXT JSON. Never invent prices, indicators, news or trade levels. If a "
            "fact is absent, say 'data unavailable'. Trade levels come from the "
            "deterministic Risk Engine and are authoritative — explain, never change them. "
            "Use research language (bias, potential setup, hypothetical, risk, invalidation). "
            f"Return ONLY a JSON object with keys: {_FIELDS}. bias in LONG/SHORT/NEUTRAL; "
            "confidence a number 0..1; list fields arrays of short strings."
        )
        contents = (f"{system}\n\n{prompt}\n\nCONTEXT JSON:\n"
                    f"{json.dumps(context, default=str)[:12000]}")
        cfg = types.GenerateContentConfig(
            temperature=AI_TEMPERATURE, max_output_tokens=AI_MAX_TOKENS,
            response_mime_type="application/json")
        try:
            resp = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model, contents=contents, config=cfg),
                timeout=35.0)
            data = json.loads(resp.text or "{}")
        except errors.APIError as e:
            code = getattr(e, "code", None) or getattr(e, "status_code", None)
            if code in (401, 403):
                raise AIProviderError("auth", "Gemini authentication/permission failed") from e
            if code == 429:
                raise AIProviderError("rate_limit", "Gemini rate limit / quota exceeded") from e
            raise AIProviderError("api_error", f"Gemini API error ({code})") from e
        except (asyncio.TimeoutError, TimeoutError) as e:
            raise AIProviderError("timeout", "Gemini request timed out") from e
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            raise AIProviderError("invalid_json", "Gemini returned invalid JSON") from e

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
