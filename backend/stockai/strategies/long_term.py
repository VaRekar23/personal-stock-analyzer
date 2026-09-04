"""Long-term strategy (long_term_v1).

Combines fundamentals (growth, profitability, valuation, balance sheet, cash
flow) with long-term technical/context (trend, 50/200 DMA, 52-week position,
relative & sector strength, market context). Weights are configurable
(config/weights.yaml). Produces a deterministic 0–100 score + confidence.
"""
from __future__ import annotations

from ..scoring.engine import Factor, score_factors, ScoreResult
from . import base as nz


def run(features: dict, fundamentals: dict, market_ctx: dict,
        sector_ctx: dict, weights: dict) -> ScoreResult:
    gw = weights["long_term"]["group_weights"]
    inc = fundamentals.get("income_statement", {})
    val = fundamentals.get("valuation", {})
    bs = fundamentals.get("balance_sheet", {})
    cf = fundamentals.get("cash_flow", {})

    price = features.get("last_price")
    sma200 = features.get("sma200")
    sma50 = features.get("sma50")
    trend_val = nz.direction_score(features.get("trend"))
    dma200_val = (100.0 if (price and sma200 and price > sma200) else 0.0) if sma200 else None
    dma50_val = (100.0 if (price and sma50 and price > sma50) else 0.0) if sma50 else None
    technical_trend = None
    parts = [p for p in (trend_val, dma200_val, dma50_val) if p is not None]
    if parts:
        technical_trend = sum(parts) / len(parts)

    w52 = features.get("week52") or {}

    factors = [
        Factor("fundamentals", "Fundamentals (PAT & scale)", gw["fundamentals"],
               nz.linear(inc.get("pat"), 0, 60000),
               "Absolute profitability & scale"),
        Factor("growth", "Growth (rev & profit)", gw["growth"],
               _avg(nz.linear(inc.get("revenue_growth_pct"), 0, 25),
                    nz.linear(inc.get("pat_growth_pct"), -5, 30)),
               "Revenue & PAT growth"),
        Factor("profitability", "Profitability (ROE/ROCE/margin)", gw["profitability"],
               _avg(nz.linear(val.get("roe_pct"), 8, 30),
                    nz.linear(val.get("roce_pct"), 9, 28),
                    nz.linear(val.get("ebitda_margin_pct"), 10, 40)),
               "Return ratios & margins"),
        Factor("valuation", "Valuation (P/E, P/B)", gw["valuation"],
               _avg(nz.inverse_linear(val.get("pe"), 10, 60),
                    nz.inverse_linear(val.get("pb"), 1, 10)),
               "Lower is cheaper"),
        Factor("balance_sheet", "Balance sheet (D/E)", gw["balance_sheet"],
               nz.inverse_linear(val.get("debt_to_equity"), 0, 1.5),
               "Leverage"),
        Factor("cash_flow", "Cash flow (FCF positive)", gw["cash_flow"],
               (100.0 if (cf.get("free_cash_flow") or 0) > 0 else 20.0)
               if cf.get("free_cash_flow") is not None else None,
               "Free cash flow generation"),
        Factor("technical_trend", "Long-term trend (50/200 DMA, 52w)", gw["technical_trend"],
               _avg(technical_trend, nz.linear(w52.get("position_pct"), 20, 90)),
               "Price above key averages"),
        Factor("sector_strength", "Sector strength", gw["sector_strength"],
               nz.direction_score(sector_ctx.get("direction")),
               "Sector direction"),
        Factor("market_context", "Market context", gw["market_context"],
               nz.direction_score((market_ctx.get("nifty") or {}).get("direction")),
               "Broad market direction"),
    ]
    return score_factors(factors)


def _avg(*vals):
    present = [v for v in vals if v is not None]
    return sum(present) / len(present) if present else None
