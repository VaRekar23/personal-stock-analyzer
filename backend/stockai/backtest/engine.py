"""Deterministic historical replay engine (backtest_v1).

No look-ahead: the decision at bar i sees only candles[:i+1] (signal on bar
close). Entry is a limit order at the entry-zone edge valid for the next bar
only. Levels come from the existing Risk Engine; this module never invents
prices. Exit accounting is conservative (stop-first on ambiguous bars).
See docs/STRATEGY_EVALUATION.md for every rule.
"""
from __future__ import annotations
import bisect
import math
from datetime import datetime

from ..indicators import engine as ind
from ..strategies import swing, intraday
from ..risk import engine as risk_engine
from ..context.engines import _direction_from_trend

WINDOW = {"1d": 400, "15m": 260, "5m": 300}
WARMUP = {"1d": 60, "15m": 60, "5m": 60}
MODE_INTERVALS = {"swing": ["1d"], "intraday": ["15m", "5m"]}

DEFAULT_ASSUMPTIONS = {
    "signal_timing": "bar_close",
    "entry_rule": "limit_at_entry_zone_edge_next_bar_only",
    "entry_valid_bars": 1,
    "exit_target": "target_1_full_exit",
    "target_2": "counterfactual_only (recorded, not traded)",
    "same_bar_rule": "stop_first",
    "limit_fill_bar_targets": "ignored (intra-bar order unknown)",
    "gap_rule": "stop gaps fill at open; target gaps fill at target price",
    "max_hold_bars_swing": 20,
    "intraday_session_exit": True,
    "intraday_no_entry_last_bars": 2,
    "slippage_bps": 0.0,
    "cost_bps_per_side": 0.0,
    "position_sizing": "fixed_fractional_on_initial_capital_no_compounding",
    "one_position_per_symbol": True,
    "cross_symbol_capital_constraint": "not_modelled",
    "market_context": "point_in_time RELIANCE proxy (same proxy as live engine)",
    "sector_context": "excluded (factor missing; weights renormalised)",
    "price_adjustment": "unadjusted (as stored)",
}


def _day(ts: str) -> str:
    return ts[:10]


def opening_range(hist: list[dict], bars: int = 4) -> dict | None:
    # Mirrors Orchestrator._opening_range so backtest == live strategy inputs.
    if len(hist) < bars:
        return None
    w = hist[-bars:]
    return {"high": round(max(c["high"] for c in w), 2), "low": round(min(c["low"] for c in w), 2)}


def _rel_strength(hist, bench, lookback=20):
    if not bench or len(hist) <= lookback or len(bench) <= lookback:
        return None
    s = (hist[-1]["close"] / hist[-lookback]["close"] - 1) * 100
    b = (bench[-1]["close"] / bench[-lookback]["close"] - 1) * 100
    return round(s - b, 2)


def default_signal(symbol, hist, mode, interval, ctx_hist, bench_hist, risk_cfg, weights):
    feats = ind.compute_features(symbol, hist[-WINDOW[interval]:], interval)
    market_ctx = {}
    if ctx_hist and len(ctx_hist) >= 50:
        cf = ind.compute_features("CTX", ctx_hist[-400:], "1d")
        market_ctx = {"nifty": {"direction": _direction_from_trend(cf.get("trend"), cf.get("rsi"))}}
    rel = _rel_strength(hist, bench_hist)
    if mode == "intraday":
        score = intraday.run(feats, market_ctx, {}, opening_range(hist), rel, weights)
    else:
        score = swing.run(feats, market_ctx, {}, rel, weights)
    sr = feats.get("support_resistance") or {}
    setup = risk_engine.build_setup(
        bias=score.bias, price=feats.get("last_price"), atr=feats.get("atr"),
        support=sr.get("support"), resistance=sr.get("resistance"),
        risk_cfg=risk_cfg, mode=mode)
    return score.to_dict(), setup


def validate_setup(s: dict | None) -> str | None:
    if not s or s.get("setup_validity") != "valid":
        return "no_setup"
    need = ("entry", "stop_loss", "target_1", "target_2", "entry_zone")
    if any(s.get(k) is None for k in need):
        return "invalid_setup"
    e, st, t1, t2 = s["entry"], s["stop_loss"], s["target_1"], s["target_2"]
    if s["direction"] == "LONG" and not (st < e < t1 <= t2):
        return "invalid_setup"
    if s["direction"] == "SHORT" and not (st > e > t1 >= t2):
        return "invalid_setup"
    if s["direction"] not in ("LONG", "SHORT"):
        return "invalid_setup"
    return None


def try_entry(s: dict, bar: dict):
    """Limit order at the zone edge for one bar. Returns (fill, fill_type|reason)."""
    lo, hi = s["entry_zone"]
    if s["direction"] == "LONG":
        if bar["open"] <= hi:
            fill, kind = bar["open"], "open"
        elif bar["low"] <= hi:
            fill, kind = hi, "limit"
        else:
            return None, "entry_not_triggered"
        if fill <= s["stop_loss"]:
            return None, "opened_beyond_stop"
    else:
        if bar["open"] >= lo:
            fill, kind = bar["open"], "open"
        elif bar["high"] >= lo:
            fill, kind = lo, "limit"
        else:
            return None, "entry_not_triggered"
        if fill >= s["stop_loss"]:
            return None, "opened_beyond_stop"
    return fill, kind


def simulate_exit(s, bars, j0, fill_type, max_hold=None, session_end_idx=None):
    """Walk bars from the entry bar j0. Conservative ordering throughout."""
    d = 1 if s["direction"] == "LONG" else -1
    stop, t1 = s["stop_loss"], s["target_1"]
    for k in range(j0, len(bars)):
        b = bars[k]
        if k > j0:
            if d * (b["open"] - stop) <= 0:
                return {"exit_idx": k, "exit_price": b["open"], "reason": "stop_gap", "ambiguous": False}
            if d * (b["open"] - t1) >= 0:
                return {"exit_idx": k, "exit_price": t1, "reason": "target_1_gap", "ambiguous": False}
        stop_hit = (b["low"] <= stop) if d == 1 else (b["high"] >= stop)
        tgt_hit = (b["high"] >= t1) if d == 1 else (b["low"] <= t1)
        if k == j0 and fill_type == "limit":
            if stop_hit:
                return {"exit_idx": k, "exit_price": stop, "reason": "stop_loss", "ambiguous": True}
            tgt_hit = False
        if stop_hit:
            return {"exit_idx": k, "exit_price": stop, "reason": "stop_loss", "ambiguous": bool(tgt_hit)}
        if tgt_hit:
            return {"exit_idx": k, "exit_price": t1, "reason": "target_1", "ambiguous": False}
        if session_end_idx is not None and k >= session_end_idx:
            return {"exit_idx": k, "exit_price": b["close"], "reason": "session_end", "ambiguous": False}
        if max_hold and (k - j0 + 1) >= max_hold:
            return {"exit_idx": k, "exit_price": b["close"], "reason": "time_exit", "ambiguous": False}
    return {"exit_idx": len(bars) - 1, "exit_price": bars[-1]["close"], "reason": "unresolved", "ambiguous": False}


def t2_reached(s, bars, exit_idx, horizon_end):
    """Counterfactual: would T2 be hit before the stop by the horizon? Stop-first."""
    d = 1 if s["direction"] == "LONG" else -1
    stop, t2 = s["stop_loss"], s["target_2"]
    for k in range(exit_idx, min(horizon_end, len(bars) - 1) + 1):
        b = bars[k]
        stop_hit = (b["low"] <= stop) if d == 1 else (b["high"] >= stop)
        if stop_hit and k > exit_idx:
            return False
        if (b["high"] >= t2) if d == 1 else (b["low"] <= t2):
            return not (stop_hit and k > exit_idx)
    return False


def account(s, entry, exit_price, qty, slippage_bps, cost_bps):
    d = 1 if s["direction"] == "LONG" else -1
    slip = slippage_bps / 1e4
    entry_eff = entry * (1 + d * slip)
    exit_eff = exit_price * (1 - d * slip)
    costs = (entry_eff + exit_eff) * qty * cost_bps / 1e4
    risk = abs(entry - s["stop_loss"])
    gross = d * (exit_price - entry) * qty
    net = d * (exit_eff - entry_eff) * qty - costs
    return {
        "gross_pnl": round(gross, 2), "net_pnl": round(net, 2), "costs": round(costs, 2),
        "entry_effective": round(entry_eff, 4), "exit_effective": round(exit_eff, 4),
        "risk_per_share": round(risk, 4),
        "r_gross": round(d * (exit_price - entry) / risk, 4) if risk else None,
        "r_net": round(net / (qty * risk), 4) if risk and qty else None,
        "return_pct": round(net / (entry * qty) * 100, 4) if qty else None,
    }


def size(entry, stop, capital, risk_pct):
    risk = abs(entry - stop)
    if risk <= 0 or entry <= 0:
        return 0
    return max(0, min(math.floor(capital * risk_pct / 100 / risk), math.floor(capital / entry)))


def _session_end(bars, i):
    day = _day(bars[i]["ts"])
    k = i
    while k + 1 < len(bars) and _day(bars[k + 1]["ts"]) == day:
        k += 1
    return k


def replay_symbol(symbol, candles, *, mode, interval, risk_cfg, weights, assumptions,
                  capital, start_ts=None, ctx_candles=None, bench_candles=None,
                  signal_fn=None, eligible=None) -> dict:
    a = {**DEFAULT_ASSUMPTIONS, **(assumptions or {})}
    signal_fn = signal_fn or default_signal
    n = len(candles)
    warm = WARMUP[interval]
    trades, open_trades, skipped = [], [], []
    no_setup = decisions = 0
    ctx_candles = ctx_candles or []
    ctx_keys = [(_day(c["ts"]) if mode == "intraday" else c["ts"]) for c in ctx_candles]
    bench_candles = bench_candles or []
    bench_ts = [c["ts"] for c in bench_candles]

    first = warm - 1
    if start_ts:
        idx = next((k for k, c in enumerate(candles) if c["ts"] >= start_ts), n)
        first = max(first, idx)
    if n < warm:
        return {"trades": [], "open_trades": [], "skipped": [], "no_setup": 0, "decisions": 0,
                "warnings": [f"{symbol}: insufficient warm-up history ({n} < {warm} bars)"]}

    i = first
    while i < n - 1:
        T = candles[i]["ts"]
        if eligible and not eligible(T):
            i += 1
            continue
        session_end_idx = None
        if mode == "intraday":
            session_end_idx = _session_end(candles, i)
            if session_end_idx - i < a["intraday_no_entry_last_bars"]:
                i += 1
                continue
        decisions += 1
        hist = candles[:i + 1]
        if mode == "intraday":  # only fully completed prior days for daily context
            ctx_hist = ctx_candles[:bisect.bisect_left(ctx_keys, _day(T))]
        else:
            ctx_hist = ctx_candles[:bisect.bisect_right(ctx_keys, T)]
        bench_hist = bench_candles[:bisect.bisect_right(bench_ts, T)]
        score, setup = signal_fn(symbol, hist, mode, interval, ctx_hist, bench_hist, risk_cfg, weights)
        reason = validate_setup(setup)
        if reason == "no_setup":
            no_setup += 1
            i += 1
            continue
        if reason:
            skipped.append({"symbol": symbol, "signal_ts": T, "reason": reason})
            i += 1
            continue
        nb = candles[i + 1]
        fill, kind = try_entry(setup, nb)
        if fill is None:
            skipped.append({"symbol": symbol, "signal_ts": T, "reason": kind,
                            "direction": setup["direction"]})
            i += 1
            continue
        qty = size(fill, setup["stop_loss"], capital, risk_cfg.get("risk_per_trade_pct", 1.0))
        if qty == 0:
            skipped.append({"symbol": symbol, "signal_ts": T, "reason": "position_size_zero"})
            i += 1
            continue
        j0 = i + 1
        max_hold = a["max_hold_bars_swing"] if mode == "swing" else None
        ex = simulate_exit(setup, candles, j0, kind, max_hold, session_end_idx if mode == "intraday" else None)
        acc = account(setup, fill, ex["exit_price"], qty, a["slippage_bps"], a["cost_bps_per_side"])
        rec = {
            "symbol": symbol, "direction": setup["direction"], "signal_ts": T,
            "entry_ts": nb["ts"], "exit_ts": candles[ex["exit_idx"]]["ts"],
            "entry_price": round(fill, 4), "exit_price": round(ex["exit_price"], 4),
            "fill_type": kind, "stop_loss": setup["stop_loss"], "target_1": setup["target_1"],
            "target_2": setup["target_2"], "entry_zone": setup["entry_zone"], "qty": qty,
            "exit_reason": ex["reason"], "ambiguous": ex["ambiguous"],
            "bars_held": ex["exit_idx"] - j0 + 1, "score": score.get("score"), **acc,
        }
        if ex["reason"] == "unresolved":
            rec["t2_reached"] = None
            open_trades.append(rec)
            break
        if ex["reason"].startswith("target_1"):
            horizon = (session_end_idx if mode == "intraday" else j0 + (max_hold or 0) - 1)
            rec["t2_reached"] = t2_reached(setup, candles, ex["exit_idx"], horizon)
        else:
            rec["t2_reached"] = False
        trades.append(rec)
        i = ex["exit_idx"]  # next decision at the close of the exit bar
    return {"trades": trades, "open_trades": open_trades, "skipped": skipped,
            "no_setup": no_setup, "decisions": decisions, "warnings": []}
