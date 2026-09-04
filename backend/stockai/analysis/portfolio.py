"""Portfolio analysis — deterministic health classification.

Health labels (Healthy / Watch / Review) follow documented rules, NOT arbitrary
AI judgement. See docs/ANALYSIS_ENGINE.md. No order placement.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from ..providers import registry
from ..data.nifty50 import SECTOR_OF, NAME_OF
from .orchestrator import get_orchestrator

IST = timezone(timedelta(hours=5, minutes=30))


def _health(pnl_pct: float, swing_score: float, swing_bias: str) -> tuple[str, list[str]]:
    """Documented rule set."""
    reasons = []
    status = "Healthy"
    if pnl_pct < -8:
        status = "Review"; reasons.append("Unrealised loss beyond -8%")
    elif pnl_pct < -3:
        status = "Watch"; reasons.append("Position in mild drawdown")
    if swing_bias == "bearish" and swing_score < 45:
        status = "Review"; reasons.append("Technical bias bearish (score < 45)")
    elif swing_bias == "neutral" and status == "Healthy":
        status = "Watch"; reasons.append("Neutral technical structure")
    if not reasons:
        reasons.append("Positive P&L and constructive technicals")
    return status, reasons


async def analyze_portfolio() -> dict:
    portfolio = registry.portfolio_provider()
    orch = get_orchestrator()
    holdings = await portfolio.get_holdings()

    enriched = []
    total_invested = total_current = 0.0
    healthy = watch = review = 0
    top_risks = []

    for h in holdings:
        sym = h["symbol"]
        qty, avg, ltp = h["quantity"], h["average_price"], h["last_price"]
        invested = qty * avg
        current = qty * ltp
        pnl = current - invested
        pnl_pct = (pnl / invested * 100) if invested else 0
        total_invested += invested
        total_current += current

        analysis = await orch.analyze_stock(sym, "swing", run_ai=False)
        swing_score = analysis["score"]["score"]
        swing_bias = analysis["score"]["bias"]
        status, reasons = _health(pnl_pct, swing_score, swing_bias)
        if status == "Healthy":
            healthy += 1
        elif status == "Watch":
            watch += 1
        else:
            review += 1
            top_risks.append({"symbol": sym, "reason": reasons[0], "pnl_pct": round(pnl_pct, 2)})

        enriched.append({
            "symbol": sym, "name": NAME_OF.get(sym, sym),
            "sector": SECTOR_OF.get(sym), "quantity": qty,
            "average_price": avg, "last_price": ltp,
            "invested": round(invested, 2), "current_value": round(current, 2),
            "pnl": round(pnl, 2), "pnl_pct": round(pnl_pct, 2),
            "swing_score": swing_score, "swing_bias": swing_bias,
            "health": status, "health_reasons": reasons,
        })

    total_pnl = total_current - total_invested
    return {
        "as_of": datetime.now(IST).isoformat(),
        "data_source": "mock",
        "summary": {
            "holdings_count": len(enriched),
            "invested": round(total_invested, 2),
            "current_value": round(total_current, 2),
            "pnl": round(total_pnl, 2),
            "pnl_pct": round(total_pnl / total_invested * 100, 2) if total_invested else 0,
            "positive_pnl": sum(1 for e in enriched if e["pnl"] >= 0),
            "negative_pnl": sum(1 for e in enriched if e["pnl"] < 0),
            "healthy": healthy, "watch": watch, "review": review,
        },
        "top_risks": sorted(top_risks, key=lambda x: x["pnl_pct"])[:5],
        "holdings": enriched,
    }
