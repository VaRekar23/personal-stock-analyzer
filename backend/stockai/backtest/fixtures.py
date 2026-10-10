"""Strategy-evaluation EVAL fixtures (deterministic, SYNTHETIC — never real history).

Each case hand-constructs OHLC bars and asserts a mathematically defined
outcome. Kept separate from AI EVALS (evals/datasets.py): these measure the
backtester's accounting, not language-model quality.
"""
from __future__ import annotations
import math
from datetime import date, timedelta

from ..core.config import DEFAULT_SETTINGS, load_weights
from ..risk import engine as risk_engine
from . import engine as E
from .metrics import compute_metrics
from .quality import assess

LABEL = "SYNTHETIC FIXTURE — not real market data"
RISK = {**DEFAULT_SETTINGS["risk"]}


def _b(i, o, h, l, c, day0=date(2024, 1, 1)):
    return {"ts": f"{(day0 + timedelta(days=i)).isoformat()}T15:30:00+05:30",
            "open": o, "high": h, "low": l, "close": c, "volume": 1000, "source": "synthetic"}


def _long():
    # price 100, ATR 2 -> entry 100, zone [99.5,100.5], stop 97, T1 104, T2 107.
    return risk_engine.build_setup(bias="bullish", price=100.0, atr=2.0, support=None,
                                   resistance=None, risk_cfg=RISK, mode="swing")


def _short():
    # SHORT: entry 100, zone [99.5,100.5], stop 103, T1 96, T2 93.
    return risk_engine.build_setup(bias="bearish", price=100.0, atr=2.0, support=None,
                                   resistance=None, risk_cfg=RISK, mode="swing")


def _trade(setup, bars, max_hold=None):
    fill, kind = E.try_entry(setup, bars[1])
    if fill is None:
        return {"skipped": kind}
    ex = E.simulate_exit(setup, bars, 1, kind, max_hold)
    acc = E.account(setup, fill, ex["exit_price"], 100, 0, 0)
    return {"fill": fill, "kind": kind, **ex, **acc}


def synthetic_series(n, day0=date(2024, 1, 1)):
    out, d, k = [], day0, 0
    while len(out) < n:
        if d.weekday() < 5:
            mid = 100 + 10 * math.sin(k / 8) + 0.15 * k
            o, c = mid - 0.5 * math.cos(k / 3), mid + 0.5 * math.cos(k / 3)
            out.append({"ts": f"{d.isoformat()}T15:30:00+05:30", "open": round(o, 2),
                        "high": round(max(o, c) + 1.0, 2), "low": round(min(o, c) - 1.0, 2),
                        "close": round(c, 2), "volume": 1000 + (k % 7) * 150, "source": "synthetic"})
            k += 1
        d += timedelta(days=1)
    return out


def _replay(candles, **kw):
    return E.replay_symbol("SYNTH", candles, mode="swing", interval="1d", risk_cfg=RISK,
                           weights=load_weights(), assumptions={}, capital=1_000_000, **kw)


def case_entry_then_target():
    s = _long()
    r = _trade(s, [_b(0, 100, 101, 99, 100), _b(1, 100, 100.8, 99.8, 100.5), _b(2, 100.6, 104.5, 100.2, 104.2)])
    return r["reason"] == "target_1" and r["exit_price"] == 104 and abs(r["r_gross"] - 4 / 3) < 1e-3, r


def case_entry_then_stop():
    s = _long()
    r = _trade(s, [_b(0, 100, 101, 99, 100), _b(1, 100, 100.5, 99.5, 100), _b(2, 99, 99.5, 96.5, 97.2)])
    return r["reason"] == "stop_loss" and r["exit_price"] == 97 and abs(r["r_gross"] + 1) < 1e-9, r


def case_same_bar_stop_and_target():
    s = _long()
    r = _trade(s, [_b(0, 100, 101, 99, 100), _b(1, 100, 100.5, 99.5, 100), _b(2, 100, 105, 96, 101)])
    return r["reason"] == "stop_loss" and r["ambiguous"] is True and abs(r["r_gross"] + 1) < 1e-9, r


def case_entry_never_triggered():
    r = _trade(_long(), [_b(0, 100, 101, 99, 100), _b(1, 102, 103, 101, 102.5)])
    return r.get("skipped") == "entry_not_triggered", r


def case_opened_beyond_stop():
    r = _trade(_long(), [_b(0, 100, 101, 99, 100), _b(1, 96, 97, 95, 96.5)])
    return r.get("skipped") == "opened_beyond_stop", r


def case_invalid_setup():
    neutral = risk_engine.build_setup(bias="neutral", price=100.0, atr=2.0, support=None,
                                      resistance=None, risk_cfg=RISK, mode="swing")
    broken = {**_long(), "stop_loss": 101.0}
    r = {"neutral": E.validate_setup(neutral), "broken": E.validate_setup(broken)}
    return r == {"neutral": "no_setup", "broken": "invalid_setup"}, r


def case_stop_gap():
    r = _trade(_long(), [_b(0, 100, 101, 99, 100), _b(1, 100, 100.5, 99.5, 100), _b(2, 95, 96, 94, 95.5)])
    return r["reason"] == "stop_gap" and r["exit_price"] == 95 and abs(r["r_gross"] + 5 / 3) < 1e-3, r


def case_costs_reduce_net():
    s = _long()
    qty = E.size(100.0, s["stop_loss"], 1_000_000, 1.0)  # floor(10000/3)=3333
    acc = E.account(s, 100.0, 104.0, qty, slippage_bps=5, cost_bps=10)
    ee, xe = 100 * 1.0005, 104 * 0.9995
    exp_net = (xe - ee) * qty - (ee + xe) * qty * 0.001
    ok = qty == 3333 and acc["gross_pnl"] == 4 * qty and abs(acc["net_pnl"] - exp_net) < 0.01 \
        and acc["net_pnl"] < acc["gross_pnl"]
    return ok, {"qty": qty, **acc, "expected_net": round(exp_net, 2)}


def case_unresolved_at_end():
    bars = [_b(0, 100, 101, 99, 100), _b(1, 100, 100.5, 99.5, 100)] + \
           [_b(i, 100, 101, 99, 100) for i in range(2, 5)]
    r = _trade(_long(), bars)
    return r["reason"] == "unresolved" and r["exit_price"] == 100, r


def case_target2_counterfactual():
    s = _long()
    bars = [_b(0, 100, 101, 99, 100), _b(1, 100, 100.8, 99.8, 100.5),
            _b(2, 100.6, 104.5, 100.2, 104.2), _b(3, 104, 107.5, 103, 107)]
    ex = E.simulate_exit(s, bars, 1, "open")
    reached = E.t2_reached(s, bars, ex["exit_idx"], len(bars) - 1)
    stop_first = E.t2_reached(s, bars[:3] + [_b(3, 104, 108, 96, 100)], ex["exit_idx"], 3)
    return reached is True and stop_first is False, {"reached": reached, "same_bar_stop": stop_first}


def case_limit_fill_ignores_entry_bar_target():
    r = _trade(_long(), [_b(0, 100, 101, 99, 100), _b(1, 101, 105, 100.2, 101),
                         _b(2, 101, 104.2, 100.6, 104)])
    return r["kind"] == "limit" and r["fill"] == 100.5 and r["exit_idx"] == 2 \
        and abs(r["r_gross"] - 1.0) < 1e-9, r


def case_time_exit():
    bars = [_b(0, 100, 101, 99, 100), _b(1, 100, 100.5, 99.5, 100)] + \
           [_b(i, 100, 101, 99, 100.4) for i in range(2, 6)]
    r = _trade(_long(), bars, max_hold=3)
    return r["reason"] == "time_exit" and r["exit_idx"] == 3 and r["exit_price"] == 100.4, r


def case_short_target():
    r = _trade(_short(), [_b(0, 100, 101, 99, 100), _b(1, 100, 100.2, 99.6, 99.9),
                          _b(2, 99.5, 99.8, 95.5, 96.2)])
    return r["reason"] == "target_1" and r["exit_price"] == 96 and abs(r["r_gross"] - 4 / 3) < 1e-3, r


def case_next_candle_execution():
    candles = synthetic_series(160)
    seen = []

    def sig(sym, hist, mode, interval, ctx, bench, risk, w):
        seen.append(len(hist))
        bias = "bullish" if len(hist) % 15 == 0 else "neutral"
        return {"score": 0}, risk_engine.build_setup(bias=bias, price=hist[-1]["close"], atr=2.0,
                                                     support=None, resistance=None, risk_cfg=risk, mode="swing")
    r = _replay(candles, signal_fn=sig)
    idx = {c["ts"]: k for k, c in enumerate(candles)}
    ok_hist = all(seen[k] < seen[k + 1] for k in range(len(seen) - 1))
    ok_next = all(idx[t["entry_ts"]] == idx[t["signal_ts"]] + 1 for t in r["trades"])
    return ok_hist and ok_next and len(r["trades"]) > 0, {"trades": len(r["trades"]), "decisions": r["decisions"]}


def case_no_lookahead():
    candles = synthetic_series(220)
    cut = 150
    future_changed = candles[:cut] + [{**c, "open": c["open"] * 1.4, "high": c["high"] * 1.5,
                                       "low": c["low"] * 0.6, "close": c["close"] * 0.7}
                                      for c in candles[cut:]]
    a, b = _replay(candles), _replay(future_changed)
    cut_ts = candles[cut]["ts"]
    pa = [t for t in a["trades"] if t["exit_ts"] < cut_ts]
    pb = [t for t in b["trades"] if t["exit_ts"] < cut_ts]
    return pa == pb, {"trades_before_cut": len(pa), "total_a": len(a["trades"]), "total_b": len(b["trades"])}


def case_determinism():
    c = synthetic_series(200)
    return _replay(c) == _replay(c), {"trades": len(_replay(c)["trades"])}


def case_levels_from_risk_engine():
    candles = synthetic_series(220)
    r = _replay(candles)
    idx = {c["ts"]: k for k, c in enumerate(candles)}
    for t in r["trades"]:
        k = idx[t["signal_ts"]]
        _, s = E.default_signal("SYNTH", candles[:k + 1], "swing", "1d", [], [], RISK, load_weights())
        if (s["stop_loss"], s["target_1"], s["target_2"]) != (t["stop_loss"], t["target_1"], t["target_2"]):
            return False, {"mismatch": t["signal_ts"]}
    return True, {"trades_checked": len(r["trades"])}


def case_insufficient_warmup():
    r = _replay(synthetic_series(30))
    return r["decisions"] == 0 and any("warm-up" in w for w in r["warnings"]), r["warnings"]


def case_missing_candles_flagged():
    c = synthetic_series(80)
    c = c[:40] + [{**x, "ts": (date.fromisoformat(x["ts"][:10]) + timedelta(days=14)).isoformat()
                   + "T15:30:00+05:30"} for x in c[40:]]
    q = assess("SYNTH", c, "1d", date.fromisoformat(c[0]["ts"][:10]),
               date.fromisoformat(c[-1]["ts"][:10]), 0)
    return q["gap_count"] >= 1 and q["synthetic"] is True, {"gaps": q["gap_count"], "warnings": q["warnings"]}


def case_membership_changes():
    candles = synthetic_series(220)
    join = candles[120]["ts"]
    r = _replay(candles, eligible=lambda T: T >= join)
    return all(t["signal_ts"] >= join for t in r["trades"] + r["open_trades"]) and \
        all(s["signal_ts"] >= join for s in r["skipped"]), {"trades": len(r["trades"])}


def case_metrics_zero_and_small_sample():
    m0, _ = compute_metrics([], [], [], 100000)
    t = {"net_pnl": 100.0, "gross_pnl": 100.0, "costs": 0.0, "return_pct": 1.0, "r_gross": 1.0,
         "r_net": 1.0, "bars_held": 2, "exit_reason": "target_1", "t2_reached": False,
         "exit_ts": "2024-01-02", "ambiguous": False}
    m3, _ = compute_metrics([t, {**t, "exit_ts": "2024-01-03"},
                             {**t, "net_pnl": -50.0, "gross_pnl": -50.0, "r_net": -0.5,
                              "exit_reason": "stop_loss", "exit_ts": "2024-01-04"}], [], [], 100000)
    ok = (m0["total_trades"] == 0 and m0["win_rate"] is None and m0["profit_factor"] is None
          and m0["sample_warnings"] and m3["profit_factor"] == 4.0 and m3["win_rate"] == round(2 / 3, 4)
          and m3["max_drawdown"] == 50.0 and any("Insufficient sample" in w for w in m3["sample_warnings"]))
    return ok, {"zero": m0["sample_warnings"], "three": m3["sample_warnings"]}


CASES = [
    case_entry_then_target, case_entry_then_stop, case_same_bar_stop_and_target,
    case_entry_never_triggered, case_opened_beyond_stop, case_invalid_setup, case_stop_gap,
    case_costs_reduce_net, case_unresolved_at_end, case_target2_counterfactual,
    case_limit_fill_ignores_entry_bar_target, case_time_exit, case_short_target,
    case_next_candle_execution, case_no_lookahead, case_determinism,
    case_levels_from_risk_engine, case_insufficient_warmup, case_missing_candles_flagged,
    case_membership_changes, case_metrics_zero_and_small_sample,
]


def run_strategy_evals() -> dict:
    results = []
    for fn in CASES:
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001 — a crash is a failed case
            ok, detail = False, {"error": f"{type(e).__name__}: {e}"}
        results.append({"case_id": fn.__name__.removeprefix("case_"), "passed": bool(ok),
                        "label": LABEL, "detail": detail})
    passed = sum(r["passed"] for r in results)
    return {"suite": "strategy_evaluation", "version": E.__name__ and "backtest_v1",
            "passed": passed, "failed": len(results) - passed, "total": len(results),
            "results": results, "label": LABEL}
