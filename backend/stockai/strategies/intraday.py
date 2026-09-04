"""Intraday strategy (intraday_v1).

A SEPARATE strategy (not the swing score reused). Uses intraday features:
NIFTY/BANKNIFTY direction, sector direction, VWAP position, EMA alignment,
momentum, relative volume, opening-range and relative strength. Requires
recent intraday candles (fetched on demand).
"""
from __future__ import annotations

from ..scoring.engine import Factor, score_factors, ScoreResult
from . import base as nz


def run(features: dict, market_ctx: dict, sector_ctx: dict,
        opening_range: dict | None, rel_strength: float | None,
        weights: dict) -> ScoreResult:
    fw = weights["intraday"]["factor_weights"]
    price = features.get("last_price")
    vwap = features.get("vwap")
    ema20, ema50 = features.get("ema20"), features.get("ema50")
    rsi = features.get("rsi")

    vwap_pos = None
    if price and vwap:
        vwap_pos = 100.0 if price > vwap else 0.0

    ema_align = None
    if ema20 and ema50 and price:
        ema_align = 100.0 if price > ema20 > ema50 else (0.0 if price < ema20 < ema50 else 50.0)

    momentum = nz.band(rsi, 55, 72, 30, 85)

    or_score = None
    if opening_range and price:
        if opening_range.get("high") and price > opening_range["high"]:
            or_score = 100.0
        elif opening_range.get("low") and price < opening_range["low"]:
            or_score = 0.0
        else:
            or_score = 50.0

    factors = [
        Factor("nifty_direction", "NIFTY direction", fw["nifty_direction"],
               nz.direction_score((market_ctx.get("nifty") or {}).get("direction"))),
        Factor("sector_direction", "Sector direction", fw["sector_direction"],
               nz.direction_score(sector_ctx.get("direction"))),
        Factor("vwap_position", "VWAP position", fw["vwap_position"], vwap_pos),
        Factor("ema_alignment", "EMA alignment", fw["ema_alignment"], ema_align),
        Factor("momentum", "Momentum (RSI)", fw["momentum"], momentum),
        Factor("relative_volume", "Relative volume", fw["relative_volume"],
               nz.linear(features.get("relative_volume"), 0.8, 2.5)),
        Factor("opening_range", "Opening range", fw["opening_range"], or_score),
        Factor("relative_strength", "Relative strength", fw["relative_strength"],
               nz.linear(rel_strength, -3, 3) if rel_strength is not None else None),
    ]
    return score_factors(factors)
