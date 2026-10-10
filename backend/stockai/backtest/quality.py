"""Candle coverage & quality assessment before a backtest. Never fabricates data."""
from __future__ import annotations
from collections import Counter
from datetime import date, datetime

SESSION_BARS = {"15m": 25, "5m": 75}
STEP_MIN = {"15m": 15, "5m": 5}


def assess(symbol, candles, interval, start: date, end: date, warmup_bars: int) -> dict:
    warnings = []
    if not candles:
        return {"symbol": symbol, "interval": interval, "bars": 0, "warmup_bars": 0, "first": None,
                "last": None, "duplicates": 0, "gaps": [], "gap_count": 0, "discontinuities": [],
                "invalid_ohlc": 0, "partial_sessions": 0, "sources": [], "synthetic": False,
                "price_adjustment": None, "ok": False,
                "warnings": [f"{symbol}: no stored {interval} candles — use 'Prepare data'."]}
    ts = [c["ts"] for c in candles]
    dups = sum(v - 1 for v in Counter(ts).values() if v > 1)
    in_range = [c for c in candles if start.isoformat() <= c["ts"][:10] <= end.isoformat()]
    pre = len(candles) - len(in_range) - sum(1 for c in candles if c["ts"][:10] > end.isoformat())
    first_day = in_range[0]["ts"][:10] if in_range else None
    last_day = in_range[-1]["ts"][:10] if in_range else None
    if dups:
        warnings.append(f"{symbol}: {dups} duplicate timestamps.")
    if interval == "1d":
        day_dups = sum(v - 1 for v in Counter(t[:10] for t in ts).values() if v > 1)
        if day_dups:
            dups += day_dups
            warnings.append(f"{symbol}: {day_dups} trading dates have more than one daily candle "
                            "(mixed data sources?) — results are unreliable.")
    if pre < warmup_bars:
        warnings.append(f"{symbol}: only {pre} warm-up bars before start (need {warmup_bars}); "
                        "early signals are delayed until warm-up is satisfied.")
    if not in_range:
        warnings.append(f"{symbol}: no candles inside the requested range.")
    else:
        if (date.fromisoformat(first_day) - start).days > 5:
            warnings.append(f"{symbol}: data starts {first_day}, after requested start {start}.")
        if (end - date.fromisoformat(last_day)).days > 5:
            warnings.append(f"{symbol}: data ends {last_day}, before requested end {end}.")

    gaps, jumps, bad = [], [], 0
    for a, b in zip(in_range, in_range[1:]):
        da, db_ = datetime.fromisoformat(a["ts"]), datetime.fromisoformat(b["ts"])
        if interval == "1d":
            if (db_ - da).days > 5:
                gaps.append([a["ts"][:10], b["ts"][:10]])
        elif a["ts"][:10] == b["ts"][:10] and (db_ - da).total_seconds() / 60 > STEP_MIN[interval] * 1.5:
            gaps.append([a["ts"], b["ts"]])
        if a["close"] and abs(b["open"] / a["close"] - 1) > 0.2:
            jumps.append({"ts": b["ts"], "prev_close": a["close"], "open": b["open"]})
    for c in in_range:
        if c["high"] < c["low"] or not (c["low"] <= c["close"] <= c["high"]):
            bad += 1
    partial = 0
    if interval in SESSION_BARS:
        per_day = Counter(c["ts"][:10] for c in in_range)
        partial = sum(1 for v in per_day.values() if v < SESSION_BARS[interval])
        if partial:
            warnings.append(f"{symbol}: {partial} intraday sessions have fewer than "
                            f"{SESSION_BARS[interval]} bars.")
    if gaps:
        warnings.append(f"{symbol}: {len(gaps)} missing-data gaps inside the range.")
    if jumps:
        warnings.append(f"{symbol}: {len(jumps)} price discontinuities >20% — possible unadjusted "
                        "corporate action (split/bonus); signals around them may be false.")
    if bad:
        warnings.append(f"{symbol}: {bad} candles with inconsistent OHLC.")
    sources = sorted({c.get("source") or "unknown" for c in candles})
    synthetic = any(s in ("mock", "synthetic", "unknown") for s in sources)
    if len(sources) > 1:
        warnings.append(f"{symbol}: mixed data sources {sources} in one series.")
    if synthetic:
        warnings.append(f"{symbol}: SYNTHETIC/MOCK candles used — no real Zerodha history is stored "
                        "for this range. Connect Zerodha and click 'Prepare data'.")
    return {
        "symbol": symbol, "interval": interval, "bars": len(in_range), "warmup_bars": pre,
        "first": first_day, "last": last_day, "duplicates": dups, "gaps": gaps[:20],
        "gap_count": len(gaps), "discontinuities": jumps[:20], "invalid_ohlc": bad,
        "partial_sessions": partial, "sources": sources, "synthetic": synthetic,
        "price_adjustment": "unadjusted (Zerodha historical candles are not split/bonus adjusted)"
        if not synthetic else "synthetic",
        "ok": bool(in_range) and not dups and not bad, "warnings": warnings,
    }
