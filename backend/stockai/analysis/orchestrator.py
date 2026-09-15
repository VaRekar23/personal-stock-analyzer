"""Analysis orchestrator — the deterministic-first pipeline.

Flow: warehouse candles -> indicators -> market/sector context -> strategy
score -> risk engine -> (optional) AI explanation. AI is NEVER the first stage
and is only called for finalists (cost control). Results are cached (Redis) and
persisted (analysis.analysis_runs) with full version provenance.
"""
from __future__ import annotations
import uuid
import json
from datetime import datetime, timedelta, timezone

from ..core import cache, db
from ..core.config import load_weights, DEFAULT_SETTINGS
from ..core import versions as V
from ..providers import registry
from ..indicators import engine as ind
from ..context.engines import MarketContextEngine, SectorContextEngine
from ..strategies import long_term, swing, intraday
from ..risk import engine as risk_engine
from ..ai.service import AIService
from ..data.warehouse import Warehouse
from ..data.nifty50 import SECTOR_OF, SYMBOLS, NAME_OF
from ..settings_store import get_settings
from ..providers.base import UnknownSymbolError
from ..core.logging_config import get_logger

logger = get_logger("stockai.orchestrator")

IST = timezone(timedelta(hours=5, minutes=30))


class Orchestrator:
    def __init__(self):
        self.market = registry.market_provider()
        self.fundamental = registry.fundamental_provider()
        self.news = registry.news_provider()
        self.warehouse = Warehouse(self.market)
        self.market_ctx_engine = MarketContextEngine(self.warehouse)
        self.sector_ctx_engine = SectorContextEngine(self.warehouse)
        self.ai = AIService(registry.ai_provider(), registry.ai_fallback_providers())
        self.weights = load_weights()

    async def _relative_strength(self, candles: list[dict], bench: list[dict],
                                 lookback: int = 20) -> float | None:
        if len(candles) <= lookback or len(bench) <= lookback:
            return None
        s_ret = (candles[-1]["close"] / candles[-lookback]["close"] - 1) * 100
        b_ret = (bench[-1]["close"] / bench[-lookback]["close"] - 1) * 100
        return round(s_ret - b_ret, 2)

    async def analyze_stock(self, symbol: str, mode: str, run_ai: bool = True,
                            force: bool = False) -> dict:
        symbol = symbol.upper()
        settings = await get_settings()
        cache_key = f"analysis:{mode}:{symbol}"
        if not force:
            cached = await cache.get_json(cache_key)
            if cached and not (run_ai and cached.get("ai") is None):
                cached["from_cache"] = True
                return cached

        interval = "15m" if mode == "intraday" else "1d"
        candles = await self.warehouse.get_candles(symbol, interval)
        bench = await self.warehouse.get_candles("RELIANCE", interval)
        mdv = self.warehouse.market_data_version(candles)

        features = ind.compute_features(symbol, candles, interval)
        market_ctx = await self.market_ctx_engine.compute()
        sector = SECTOR_OF.get(symbol, "market")
        sector_ctx = await self.sector_ctx_engine.compute(sector)
        rel = await self._relative_strength(candles, bench)

        fundamentals = None
        if mode == "long_term":
            fundamentals = await self.fundamental.get_fundamentals(symbol)
            score = long_term.run(features, fundamentals, market_ctx, sector_ctx, self.weights)
        elif mode == "intraday":
            opening_range = self._opening_range(candles)
            score = intraday.run(features, market_ctx, sector_ctx, opening_range, rel, self.weights)
        else:
            score = swing.run(features, market_ctx, sector_ctx, rel, self.weights)

        # Risk engine (deterministic trade levels). None for long_term (investing).
        setup = None
        if mode in ("swing", "intraday"):
            sr = features.get("support_resistance") or {}
            setup = risk_engine.build_setup(
                bias=score.bias, price=features.get("last_price"),
                atr=features.get("atr"), support=sr.get("support"),
                resistance=sr.get("resistance"),
                risk_cfg=settings["risk"], mode=mode)

        strategy_version = V.STRATEGY_VERSIONS[mode]
        prompt_version = V.PROMPT_VERSIONS[mode]

        ai_result, ai_cached = None, False
        if run_ai:
            ctx = {"symbol": symbol, "mode": mode, "score": score.to_dict(),
                   "features": features, "market_context": market_ctx,
                   "sector_context": sector_ctx, "risk_setup": setup,
                   "fundamentals": fundamentals}
            ai_result, ai_cached = await self.ai.explain(
                symbol=symbol, analysis_type=mode, context=ctx,
                market_data_version=mdv, strategy_version=strategy_version,
                prompt_version=prompt_version)

        result = {
            "id": str(uuid.uuid4()),
            "symbol": symbol, "name": NAME_OF.get(symbol, symbol),
            "mode": mode, "sector": sector,
            "as_of": datetime.now(IST).isoformat(),
            "features": features,
            "fundamentals": fundamentals,
            "market_context": market_ctx,
            "sector_context": sector_ctx,
            "relative_strength": rel,
            "score": score.to_dict(),
            "trade_setup": setup,
            "ai": ai_result,
            "ai_cached": ai_cached,
            "provenance": {
                "strategy_version": strategy_version,
                "indicator_version": V.INDICATOR_VERSION,
                "scoring_version": V.SCORING_VERSION,
                "risk_version": V.RISK_VERSION,
                "prompt_version": prompt_version,
                "provider": getattr(registry.ai_provider(), "name", "mock"),
                "model": getattr(registry.ai_provider(), "model", "mock"),
                "market_data_version": mdv,
            },
            "data_source": registry.data_source(),
            "from_cache": False,
        }
        await cache.set_json(cache_key, result, settings["cache"]["analysis_ttl_seconds"])
        await self._persist_run(result)
        return result

    def _opening_range(self, candles: list[dict], bars: int = 4) -> dict | None:
        if len(candles) < bars:
            return None
        window = candles[-bars:]
        return {"high": round(max(c["high"] for c in window), 2),
                "low": round(min(c["low"] for c in window), 2)}

    async def _persist_run(self, r: dict) -> None:
        p = r["provenance"]
        await db.execute(
            """INSERT INTO analysis.analysis_runs
               (id,symbol,analysis_type,strategy_version,indicator_version,
                scoring_version,risk_version,prompt_version,provider,model,
                market_data_version,cache_key,ai_cached,result)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)""",
            uuid.UUID(r["id"]), r["symbol"], r["mode"], p["strategy_version"],
            p["indicator_version"], p["scoring_version"], p["risk_version"],
            p["prompt_version"], p["provider"], p["model"],
            p["market_data_version"], f"analysis:{r['mode']}:{r['symbol']}",
            r["ai_cached"], json.dumps(r, default=str))

    async def scan(self, mode: str, symbols: list[str] | None = None) -> dict:
        """Deterministic-first scan: score ALL, AI only on finalists."""
        symbols = symbols or SYMBOLS
        settings = await get_settings()
        cache_key = f"scanner:{mode}:{len(symbols)}"
        cached = await cache.get_json(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

        rows = []
        if mode == "long_term":
            # Prefetch fundamentals concurrently (bounded) so 50 sequential
            # yfinance calls don't dominate wall-time; each call self-caches.
            import asyncio as _asyncio
            sem = _asyncio.Semaphore(8)

            async def _pf(sym):
                async with sem:
                    try:
                        await self.fundamental.get_fundamentals(sym)
                    except Exception:  # noqa: BLE001
                        pass
            await _asyncio.gather(*[_pf(s) for s in symbols])

        skipped = []
        for sym in symbols:
            try:
                r = await self.analyze_stock(sym, mode, run_ai=False)
            except UnknownSymbolError as e:
                # A single unresolvable instrument must not fail the whole scan.
                logger.warning("scan: skipping unresolvable symbol %s (%s)", sym, e)
                skipped.append({"symbol": sym, "reason": "unresolvable_instrument"})
                continue
            except Exception as e:  # noqa: BLE001 — isolate per-symbol failures
                logger.warning("scan: skipping %s (%s: %s)", sym, type(e).__name__, e)
                skipped.append({"symbol": sym, "reason": type(e).__name__})
                continue
            setup = r.get("trade_setup") or {}
            rows.append({
                "symbol": sym, "name": r["name"], "sector": r["sector"],
                "price": r["features"].get("last_price"),
                "score": r["score"]["score"], "confidence": r["score"]["confidence"],
                "bias": r["score"]["bias"], "trend": r["features"].get("trend"),
                "rsi": r["features"].get("rsi"),
                "relative_volume": r["features"].get("relative_volume"),
                "trade_setup": {k: setup.get(k) for k in
                                ("direction", "entry", "stop_loss", "target_1",
                                 "target_2", "risk_reward_1", "setup_validity")} if setup else None,
            })

        rows.sort(key=lambda x: x["score"], reverse=True)
        for i, row in enumerate(rows, 1):
            row["rank"] = i

        # Cost control: run AI only on top finalists above threshold.
        top_n = settings["thresholds"]["shortlist_top_n"]
        min_score = settings["thresholds"]["shortlist_min_score"]
        finalists = [r for r in rows[:top_n] if r["score"] >= min_score]
        for row in finalists:
            full = await self.analyze_stock(row["symbol"], mode, run_ai=True)
            row["ai_summary"] = (full.get("ai") or {}).get("summary")
            row["ai_bias"] = (full.get("ai") or {}).get("bias")

        result = {
            "mode": mode, "as_of": datetime.now(IST).isoformat(),
            "universe": "NIFTY 50", "count": len(rows),
            "skipped": skipped,
            "ai_finalists": len(finalists),
            "results": rows, "data_source": registry.data_source(), "from_cache": False,
            "provenance": {"strategy_version": V.STRATEGY_VERSIONS[mode],
                           "scoring_version": V.SCORING_VERSION},
        }
        await cache.set_json(cache_key, result, settings["cache"]["scanner_ttl_seconds"])
        return result


_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def reset_orchestrator() -> None:
    """Rebuild providers/engines (e.g. after a Kite login switches to live data)."""
    global _orchestrator
    _orchestrator = None
