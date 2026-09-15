"""FastAPI routes. Thin handlers — business logic lives in the domain layer.

All routes are under /api (Kubernetes ingress requirement). Errors are surfaced
as structured, actionable responses; nothing returns fabricated data silently.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .core import db, cache
from .core import versions as V
from .core.config import ZERODHA_API_KEY, ZERODHA_API_SECRET
from .providers import registry
from .providers.mock.market import market_status
from .providers.zerodha import session as kite_session
from .analysis.orchestrator import get_orchestrator, reset_orchestrator
from .analysis.portfolio import analyze_portfolio
from .evals.datasets import run_evals
from .settings_store import get_settings, update_settings
from .data.nifty50 import NIFTY50

IST = timezone(timedelta(hours=5, minutes=30))
api_router = APIRouter(prefix="/api")

VALID_MODES = {"long_term", "swing", "intraday"}


@api_router.get("/")
async def root():
    return {"app": "StockAI", "version": V.SCORING_VERSION, "status": "ok",
            "data_source": registry.data_source()}


# ---------------- Health / Data Health ----------------
@api_router.get("/health")
async def health():
    orch = get_orchestrator()
    db_h = await db.health()
    redis_h = await cache.health()
    modes = registry.provider_modes()
    last_ingest = await orch.warehouse.last_ingestion_summary()

    last_analysis = None
    row = await db.fetchrow(
        "SELECT symbol, analysis_type, created_at FROM analysis.analysis_runs "
        "ORDER BY created_at DESC LIMIT 1")
    if row:
        last_analysis = {"symbol": row["symbol"], "type": row["analysis_type"],
                         "at": row["created_at"].isoformat()}

    def prov_status(m):
        return "OPERATIONAL" if m["live"] else "DEMO-MOCK"

    return {
        "as_of": datetime.now(IST).isoformat(),
        # Clean top-level signals the frontend badge/UI consume directly.
        "data_source": modes["data"]["mode"],
        "live": {
            "market": modes["data"]["live"],
            "fundamental": modes["fundamental"]["live"],
            "news": modes["news"]["live"],
            "ai": modes["ai"]["live"],
        },
        "services": {
            "database": {"status": db_h["status"].upper(), "detail": db_h["detail"],
                         "engine": "PostgreSQL 15 (Timescale-ready)"},
            "cache": {"status": redis_h["status"].upper(), "detail": redis_h["detail"],
                      "stats": cache.stats()},
            "zerodha": {"status": prov_status(modes["data"]),
                        "detail": ("Zerodha Kite live" if modes["data"]["live"]
                                   else "Mock — connect via Settings → Broker Connection")},
            "fundamental": {"status": prov_status(modes["fundamental"]),
                            "detail": f"provider={modes['fundamental']['mode']}"},
            "news": {"status": prov_status(modes["news"]),
                     "detail": f"provider={modes['news']['mode']}"},
            "ai": {"status": prov_status(modes["ai"]),
                   "detail": f"Provider={modes['ai']['selected']} model={modes['ai'].get('model','')}"
                             + (f" fallback={modes['ai'].get('fallback')}" if modes['ai'].get('fallback') else "")},
            "knowledge_rag": {"status": "PENDING-V2", "detail": "RAG seam only in V1"},
        },
        "last_ingestion": last_ingest,
        "last_analysis": last_analysis,
        "versions": {
            "indicator": V.INDICATOR_VERSION, "scoring": V.SCORING_VERSION,
            "risk": V.RISK_VERSION, "strategies": V.STRATEGY_VERSIONS,
            "prompts": V.PROMPT_VERSIONS,
        },
    }


# ---------------- Market ----------------
@api_router.get("/market/overview")
async def market_overview():
    orch = get_orchestrator()
    ctx = await orch.market_ctx_engine.compute()
    sectors = await orch.sector_ctx_engine.all_sectors()
    return {
        "as_of": datetime.now(IST).isoformat(),
        "market_status": market_status(),
        "context": ctx, "sectors": sectors,
        "data_source": registry.data_source(),
    }


@api_router.get("/instruments")
async def instruments():
    return {"count": len(NIFTY50),
            "instruments": [{"symbol": s, "name": n, "sector": sec}
                            for s, n, sec in NIFTY50]}


@api_router.get("/quote/{symbol}")
async def quote(symbol: str):
    return await registry.market_provider().get_quote(symbol.upper())


@api_router.get("/candles/{symbol}")
async def candles(symbol: str, interval: str = "1d", count: int = Query(200, le=500)):
    orch = get_orchestrator()
    data = await orch.warehouse.get_candles(symbol.upper(), interval, count)
    if not data:
        raise HTTPException(404, f"No candle data for {symbol}")
    return {"symbol": symbol.upper(), "interval": interval,
            "market_data_version": orch.warehouse.market_data_version(data),
            "candles": data, "data_source": registry.data_source()}


# ---------------- Analysis ----------------
class AnalyzeRequest(BaseModel):
    symbol: str
    mode: str = "swing"
    run_ai: bool = True
    force: bool = False


@api_router.post("/analyze")
async def analyze(req: AnalyzeRequest):
    if req.mode not in VALID_MODES:
        raise HTTPException(400, f"Invalid mode. Use one of {sorted(VALID_MODES)}")
    valid = {s for s, _, _ in NIFTY50}
    if req.symbol.upper() not in valid:
        raise HTTPException(404, f"Unknown symbol '{req.symbol}'. V1 covers NIFTY 50.")
    orch = get_orchestrator()
    return await orch.analyze_stock(req.symbol, req.mode, req.run_ai, req.force)


@api_router.get("/analysis/history/{symbol}")
async def analysis_history(symbol: str, limit: int = 10):
    rows = await db.fetch(
        """SELECT id,analysis_type,strategy_version,prompt_version,provider,model,
                  market_data_version,ai_cached,created_at
           FROM analysis.analysis_runs WHERE symbol=$1
           ORDER BY created_at DESC LIMIT $2""", symbol.upper(), limit)
    return {"symbol": symbol.upper(),
            "runs": [{**r, "id": str(r["id"]),
                      "created_at": r["created_at"].isoformat()} for r in rows]}


@api_router.get("/scan")
async def scan(mode: str = "swing"):
    if mode not in VALID_MODES:
        raise HTTPException(400, f"Invalid mode. Use one of {sorted(VALID_MODES)}")
    return await get_orchestrator().scan(mode)


# ---------------- Portfolio ----------------
@api_router.get("/portfolio")
async def portfolio():
    return await analyze_portfolio()


# ---------------- Fundamentals / News ----------------
@api_router.get("/fundamentals/{symbol}")
async def fundamentals(symbol: str):
    return await registry.fundamental_provider().get_fundamentals(symbol.upper())


@api_router.get("/news/{symbol}")
async def news(symbol: str, limit: int = 8):
    return {"symbol": symbol.upper(),
            "items": await registry.news_provider().get_news(symbol.upper(), limit),
            "note": "News is a separate evidence source, not an automatic signal."}


# ---------------- EVALS ----------------
class EvalRequest(BaseModel):
    sample_size: int = 6


@api_router.post("/evals/run")
async def evals_run(req: EvalRequest):
    return await run_evals(req.sample_size)


@api_router.get("/evals/latest")
async def evals_latest():
    run = await db.fetchrow(
        "SELECT * FROM evaluation.eval_runs ORDER BY started_at DESC LIMIT 1")
    datasets = await db.fetch("SELECT * FROM evaluation.eval_datasets ORDER BY id")
    cases = await db.fetch(
        "SELECT case_id,dataset_id,evaluation_type,label FROM evaluation.eval_cases")
    results = []
    if run:
        results = await db.fetch(
            """SELECT case_id,evaluation_type,passed,score,detail
               FROM evaluation.eval_results WHERE run_id=$1""", run["id"])
    return {
        "latest_run": {**run, "id": str(run["id"]),
                       "started_at": run["started_at"].isoformat(),
                       "avg_score": float(run["avg_score"]) if run["avg_score"] else None}
        if run else None,
        "datasets": [{**d, "created_at": d["created_at"].isoformat()} for d in datasets],
        "cases": cases,
        "results": [{**r, "score": float(r["score"]) if r["score"] is not None else None}
                    for r in results],
    }


# ---------------- Settings ----------------
@api_router.get("/settings")
async def settings_get():
    s = await get_settings()
    return {"settings": s, "note": "Sensitive credentials are never exposed here.",
            "providers_editable": ["ai_model"], "versions": {
                "strategies": V.STRATEGY_VERSIONS, "prompts": V.PROMPT_VERSIONS}}


class SettingsUpdate(BaseModel):
    values: dict


@api_router.put("/settings/{section}")
async def settings_update(section: str, body: SettingsUpdate):
    allowed = {"risk", "cache", "thresholds", "providers"}
    if section not in allowed:
        raise HTTPException(400, f"Editable sections: {sorted(allowed)}")
    try:
        s = await update_settings(section, body.values)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    await cache.delete("analysis:")
    await cache.delete("scanner:")
    return {"settings": s, "updated": section}



# ---------------- Zerodha / Kite Connect (server-side login) ----------------
@api_router.get("/kite/status")
async def kite_status():
    s = kite_session.status()
    return {"configured": bool(ZERODHA_API_KEY and ZERODHA_API_SECRET),
            "api_key_present": bool(ZERODHA_API_KEY),
            "live": registry.data_source() == "zerodha", **s,
            "note": "Kite access tokens expire daily (~06:00 IST); re-login each day."}


@api_router.get("/kite/login-url")
async def kite_login_url():
    if not ZERODHA_API_KEY:
        raise HTTPException(400, "ZERODHA_API_KEY not configured")
    url = f"https://kite.zerodha.com/connect/login?v=3&api_key={ZERODHA_API_KEY}"
    return {"login_url": url,
            "instructions": "Open this URL, log in to Zerodha, then copy the "
                            "'request_token' from the redirected URL and submit it below."}


class KiteSession(BaseModel):
    request_token: str


@api_router.post("/kite/session")
async def kite_create_session(body: KiteSession):
    if not (ZERODHA_API_KEY and ZERODHA_API_SECRET):
        raise HTTPException(400, "Zerodha API key/secret not configured")
    try:
        from kiteconnect import KiteConnect
        import asyncio
        kite = KiteConnect(api_key=ZERODHA_API_KEY)
        data = await asyncio.to_thread(
            kite.generate_session, body.request_token.strip(),
            api_secret=ZERODHA_API_SECRET)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Kite session exchange failed: {e}")
    await kite_session.persist(data["access_token"], str(data.get("login_time")))
    reset_orchestrator()  # switch to live market/portfolio providers
    await cache.delete("analysis:")
    await cache.delete("scanner:")
    return {"connected": True, "live": registry.data_source() == "zerodha",
            "login_time": str(data.get("login_time"))}


@api_router.post("/kite/logout")
async def kite_logout():
    await kite_session.clear()
    reset_orchestrator()
    await cache.delete("analysis:")
    await cache.delete("scanner:")
    return {"connected": False}
