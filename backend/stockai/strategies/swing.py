"""Swing strategy (swing_v1).

Short-term price-action focus: market/sector trend, price structure, EMA
alignment, momentum (RSI/MACD), volume, support/resistance, volatility (ATR)
and relative strength. Configurable weights (config/weights.yaml).
"""
from __future__ import annotations

from ..scoring.engine import Factor, score_factors, ScoreResult
from . import base as nz


def run(features: dict, market_ctx: dict, sector_ctx: dict,
        rel_strength: float | None, weights: dict) -> ScoreResult:
    fw = weights["swing"]["factor_weights"]
    price = features.get("last_price")
    ema20, ema50 = features.get("ema20"), features.get("ema50")
    macd = features.get("macd") or {}
    rsi = features.get("rsi")

    ema_align = None
    if ema20 and ema50 and price:
        ema_align = 100.0 if price > ema20 > ema50 else (0.0 if price < ema20 < ema50 else 50.0)

    price_structure = nz.direction_score(features.get("trend"))
    if ema_align is not None:
        price_structure = _avg(price_structure, ema_align)

    momentum = _avg(
        nz.band(rsi, 55, 70, 30, 85),
        100.0 if macd.get("histogram", 0) > 0 else (0.0 if macd.get("histogram") is not None else None),
    )

    vol = features.get("relative_volume")
    volume_score = nz.linear(vol, 0.8, 2.0)

    sr = features.get("support_resistance") or {}
    sr_score = None
    if price and sr.get("support") and sr.get("resistance") and sr["resistance"] > sr["support"]:
        pos = (price - sr["support"]) / (sr["resistance"] - sr["support"])
        sr_score = nz.clamp((1 - abs(pos - 0.35)) * 120)  # reward room above support

    atr = features.get("atr")
    volatility_score = None
    if atr and price:
        atr_pct = atr / price * 100
        volatility_score = nz.band(atr_pct, 1.0, 3.0, 0.2, 6.0)

    factors = [
        Factor("market_trend", "Market trend", fw["market_trend"],
               nz.direction_score((market_ctx.get("nifty") or {}).get("direction"))),
        Factor("sector_trend", "Sector trend", fw["sector_trend"],
               nz.direction_score(sector_ctx.get("direction"))),
        Factor("price_structure", "Price structure / EMA alignment", fw["price_structure"],
               price_structure),
        Factor("momentum", "Momentum (RSI/MACD)", fw["momentum"], momentum),
        Factor("volume", "Relative volume", fw["volume"], volume_score),
        Factor("support_resistance", "Support/Resistance position", fw["support_resistance"], sr_score),
        Factor("volatility", "Volatility (ATR)", fw["volatility"], volatility_score),
        Factor("relative_strength", "Relative strength", fw["relative_strength"],
               nz.linear(rel_strength, -5, 5) if rel_strength is not None else None),
    ]
    return score_factors(factors)


def _avg(*vals):
    present = [v for v in vals if v is not None]
    return sum(present) / len(present) if present else None
