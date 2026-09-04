"""Deterministic technical-indicator engine (indicator_version = technical_v1).

Pure functions over OHLCV lists. The LLM never calculates these. Output is a
structured feature dict. Uses numpy for vectorised math.
"""
from __future__ import annotations
import numpy as np


def _closes(candles): return np.array([c["close"] for c in candles], dtype=float)
def _highs(candles): return np.array([c["high"] for c in candles], dtype=float)
def _lows(candles): return np.array([c["low"] for c in candles], dtype=float)
def _vols(candles): return np.array([c["volume"] for c in candles], dtype=float)


def sma(values: np.ndarray, period: int):
    if len(values) < period:
        return None
    return float(np.mean(values[-period:]))


def ema_series(values: np.ndarray, period: int):
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


def ema(values, period):
    v = ema_series(values, period)
    return float(v) if v is not None else None


def rsi(values: np.ndarray, period: int = 14):
    if len(values) <= period:
        return None
    delta = np.diff(values)
    gains = np.where(delta > 0, delta, 0.0)
    losses = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(round(100 - (100 / (1 + rs)), 2))


def macd(values: np.ndarray, fast=12, slow=26, signal=9):
    if len(values) < slow + signal:
        return None
    def _ema_arr(arr, p):
        k = 2 / (p + 1)
        out = [arr[0]]
        for v in arr[1:]:
            out.append(v * k + out[-1] * (1 - k))
        return np.array(out)
    macd_line = _ema_arr(values, fast) - _ema_arr(values, slow)
    signal_line = _ema_arr(macd_line, signal)
    hist = macd_line[-1] - signal_line[-1]
    return {"macd": float(round(macd_line[-1], 2)),
            "signal": float(round(signal_line[-1], 2)),
            "histogram": float(round(hist, 2))}


def atr(candles, period: int = 14):
    if len(candles) <= period:
        return None
    h, l, c = _highs(candles), _lows(candles), _closes(candles)
    prev_close = c[:-1]
    tr = np.maximum(h[1:] - l[1:],
                    np.maximum(np.abs(h[1:] - prev_close), np.abs(l[1:] - prev_close)))
    return float(round(np.mean(tr[-period:]), 2))


def vwap(candles):
    if not candles:
        return None
    h, l, c, v = _highs(candles), _lows(candles), _closes(candles), _vols(candles)
    tp = (h + l + c) / 3
    denom = np.sum(v)
    if denom == 0:
        return None
    return float(round(np.sum(tp * v) / denom, 2))


def supertrend(candles, period: int = 10, multiplier: float = 3.0):
    if len(candles) <= period:
        return None
    a = atr(candles, period)
    if a is None:
        return None
    c = _closes(candles)
    h, l = _highs(candles), _lows(candles)
    hl2 = (h[-1] + l[-1]) / 2
    upper = hl2 + multiplier * a
    lower = hl2 - multiplier * a
    return "bullish" if c[-1] >= (upper + lower) / 2 else "bearish"


def bollinger(values: np.ndarray, period: int = 20, mult: float = 2.0):
    if len(values) < period:
        return None
    window = values[-period:]
    mid = float(np.mean(window))
    sd = float(np.std(window))
    return {"upper": round(mid + mult * sd, 2), "middle": round(mid, 2),
            "lower": round(mid - mult * sd, 2)}


def pivots(candles):
    if len(candles) < 2:
        return None
    prev = candles[-2]
    p = (prev["high"] + prev["low"] + prev["close"]) / 3
    r1 = 2 * p - prev["low"]
    s1 = 2 * p - prev["high"]
    r2 = p + (prev["high"] - prev["low"])
    s2 = p - (prev["high"] - prev["low"])
    return {"pivot": round(p, 2), "r1": round(r1, 2), "s1": round(s1, 2),
            "r2": round(r2, 2), "s2": round(s2, 2)}


def relative_volume(candles, lookback: int = 20):
    if len(candles) < lookback + 1:
        return None
    v = _vols(candles)
    avg = np.mean(v[-lookback - 1:-1])
    if avg == 0:
        return None
    return float(round(v[-1] / avg, 2))


def support_resistance(candles, lookback: int = 20):
    if len(candles) < lookback:
        return None
    window = candles[-lookback:]
    return {"support": round(min(c["low"] for c in window), 2),
            "resistance": round(max(c["high"] for c in window), 2)}


def trend_classification(values: np.ndarray):
    e20, e50 = ema(values, 20), ema(values, 50)
    if e20 is None or e50 is None:
        return "unknown"
    last = float(values[-1])
    if last > e20 > e50:
        return "uptrend"
    if last < e20 < e50:
        return "downtrend"
    return "sideways"


def compute_features(symbol: str, candles: list[dict], timeframe: str) -> dict:
    """Master function: returns the structured technical feature set."""
    c = _closes(candles)
    if len(c) == 0:
        return {"symbol": symbol, "timeframe": timeframe, "error": "no data"}
    sr = support_resistance(candles)
    week52 = None
    if timeframe == "1d" and len(candles) >= 60:
        window = candles[-min(250, len(candles)):]
        hi = max(x["high"] for x in window)
        lo = min(x["low"] for x in window)
        last = c[-1]
        week52 = {"high": round(hi, 2), "low": round(lo, 2),
                  "position_pct": round((last - lo) / (hi - lo) * 100, 1) if hi > lo else None}
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "last_price": round(float(c[-1]), 2),
        "sma50": round(sma(c, 50), 2) if sma(c, 50) else None,
        "sma200": round(sma(c, 200), 2) if sma(c, 200) else None,
        "ema20": round(ema(c, 20), 2) if ema(c, 20) else None,
        "ema50": round(ema(c, 50), 2) if ema(c, 50) else None,
        "ema200": round(ema(c, 200), 2) if ema(c, 200) else None,
        "rsi": rsi(c),
        "macd": macd(c),
        "atr": atr(candles),
        "vwap": vwap(candles[-75:]) if timeframe != "1d" else None,
        "supertrend": supertrend(candles),
        "bollinger": bollinger(c),
        "pivots": pivots(candles),
        "relative_volume": relative_volume(candles),
        "support_resistance": sr,
        "week52": week52,
        "trend": trend_classification(c),
        "indicator_version": "technical_v1",
    }
