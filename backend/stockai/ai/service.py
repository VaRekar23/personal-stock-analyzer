"""AIService — orchestrates the AI explanation layer with aggressive caching.

Cache key considers symbol, analysis_type, date context, market_data_version,
strategy_version, prompt_version, provider and model — so swing/intraday/
long-term are cached separately and identical inputs are not re-billed.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone

from ..core import cache, db
from ..core.config import DEFAULT_SETTINGS
from .prompts import build_prompt
from .schemas import AIAnalysis


def make_cache_key(symbol: str, analysis_type: str, *, market_data_version: str,
                   strategy_version: str, prompt_version: str, provider: str,
                   model: str, date_context: str) -> str:
    raw = "|".join([symbol, analysis_type, date_context, market_data_version,
                    strategy_version, prompt_version, provider, model])
    digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return f"ai:{analysis_type}:{symbol}:{digest}"


class AIService:
    def __init__(self, provider):
        self.provider = provider

    async def explain(self, *, symbol: str, analysis_type: str, context: dict,
                      market_data_version: str, strategy_version: str,
                      prompt_version: str) -> tuple[dict, bool]:
        provider_name = getattr(self.provider, "name", "mock")
        model = getattr(self.provider, "model", "mock")
        date_context = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = make_cache_key(
            symbol, analysis_type, market_data_version=market_data_version,
            strategy_version=strategy_version, prompt_version=prompt_version,
            provider=provider_name, model=model, date_context=date_context)

        cached = await cache.get_json(key)
        if cached:
            return cached, True
        row = await db.fetchrow(
            "SELECT result FROM analysis.ai_analyses WHERE cache_key=$1", key)
        if row:
            result = row["result"] if isinstance(row["result"], dict) else json.loads(row["result"])
            await cache.set_json(key, result, DEFAULT_SETTINGS["cache"]["ai_ttl_seconds"])
            return result, True

        prompt = build_prompt(analysis_type, symbol)
        ctx = {**context, "prompt_version": prompt_version, "symbol": symbol}
        raw = await self.provider.generate(prompt, ctx, AIAnalysis.json_schema())
        validated = AIAnalysis(**raw).model_dump()  # schema enforcement

        await cache.set_json(key, validated, DEFAULT_SETTINGS["cache"]["ai_ttl_seconds"])
        await db.execute(
            """INSERT INTO analysis.ai_analyses
               (cache_key, symbol, analysis_type, provider, model, prompt_version, result)
               VALUES ($1,$2,$3,$4,$5,$6,$7)
               ON CONFLICT (cache_key) DO NOTHING""",
            key, symbol, analysis_type, provider_name, model, prompt_version,
            json.dumps(validated))
        return validated, False
