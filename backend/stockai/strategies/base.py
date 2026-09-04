"""Shared helpers for mapping raw metrics into normalized 0..100 factor values.

None inputs propagate as None (data unavailable) so the scoring engine can
distinguish missing data from a negative signal.
"""
from __future__ import annotations


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def linear(value, low, high) -> float | None:
    """Map value in [low, high] -> 0..100 (clamped). None-safe."""
    if value is None:
        return None
    if high == low:
        return 50.0
    return clamp((value - low) / (high - low) * 100)


def band(value, ideal_low, ideal_high, hard_low, hard_high) -> float | None:
    """Score highest inside [ideal_low, ideal_high], falling off outside."""
    if value is None:
        return None
    if ideal_low <= value <= ideal_high:
        return 100.0
    if value < ideal_low:
        return linear(value, hard_low, ideal_low)
    return linear(hard_high - (value - ideal_high), hard_low, ideal_low)


def direction_score(direction: str | None) -> float | None:
    if direction is None:
        return None
    return {"bullish": 100.0, "neutral": 50.0, "bearish": 0.0,
            "uptrend": 100.0, "sideways": 50.0, "downtrend": 0.0}.get(direction, 50.0)


def inverse_linear(value, low, high) -> float | None:
    """Lower is better (e.g. valuation, debt)."""
    v = linear(value, low, high)
    return None if v is None else 100.0 - v
