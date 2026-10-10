"""Deterministic performance metrics (definitions: docs/STRATEGY_EVALUATION.md)."""
from __future__ import annotations
from collections import Counter

MIN_SAMPLE = 30


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 4) if xs else None


def equity_curve(trades, capital):
    eq, peak, mdd, mdd_pct, curve = capital, capital, 0.0, 0.0, [{"ts": None, "equity": capital}]
    for t in sorted(trades, key=lambda x: x["exit_ts"]):
        eq += t["net_pnl"]
        peak = max(peak, eq)
        dd = peak - eq
        if dd > mdd:
            mdd, mdd_pct = dd, (dd / peak * 100 if peak else 0.0)
        curve.append({"ts": t["exit_ts"], "equity": round(eq, 2)})
    return curve, round(mdd, 2), round(mdd_pct, 4)


def compute_metrics(trades, open_trades, skipped, capital, no_setup=0, decisions=0) -> dict:
    n = len(trades)
    wins = [t for t in trades if t["net_pnl"] > 0]
    losses = [t for t in trades if t["net_pnl"] < 0]
    gw = sum(t["net_pnl"] for t in wins)
    gl = -sum(t["net_pnl"] for t in losses)
    curve, mdd, mdd_pct = equity_curve(trades, capital)
    rate = (lambda k: round(k / n, 4) if n else None)
    warnings = []
    if n == 0:
        warnings.append("Zero completed trades: no performance statistics can be computed.")
    elif n < MIN_SAMPLE:
        warnings.append(f"Insufficient sample ({n} < {MIN_SAMPLE} completed trades): "
                        "results are not statistically reliable.")
    return {
        "total_trades": n,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "breakeven_trades": n - len(wins) - len(losses),
        "win_rate": rate(len(wins)),
        "gross_pnl": round(sum(t["gross_pnl"] for t in trades), 2),
        "net_pnl": round(sum(t["net_pnl"] for t in trades), 2),
        "total_costs": round(sum(t["costs"] for t in trades), 2),
        "avg_return_pct": _avg([t["return_pct"] for t in trades]),
        "avg_r_gross": _avg([t["r_gross"] for t in trades]),
        "avg_r": _avg([t["r_net"] for t in trades]),
        "expectancy_r": _avg([t["r_net"] for t in trades]),
        "profit_factor": round(gw / gl, 4) if gl > 0 else None,
        "profit_factor_note": None if gl > 0 else ("undefined: no losing trades" if n else "undefined: no trades"),
        "max_drawdown": mdd,
        "max_drawdown_pct": mdd_pct,
        "avg_holding_bars": _avg([t["bars_held"] for t in trades]),
        "target_1_hit_rate": rate(sum(1 for t in trades if t["exit_reason"].startswith("target_1"))),
        "target_2_hit_rate": rate(sum(1 for t in trades if t.get("t2_reached"))),
        "stop_loss_hit_rate": rate(sum(1 for t in trades if t["exit_reason"] in ("stop_loss", "stop_gap"))),
        "ambiguous_bars": sum(1 for t in trades if t.get("ambiguous")),
        "open_trades": len(open_trades),
        "skipped_trades": len(skipped),
        "skipped_by_reason": dict(Counter(s["reason"] for s in skipped)),
        "no_setup_decisions": no_setup,
        "decisions_evaluated": decisions,
        "ending_equity": curve[-1]["equity"],
        "sample_warnings": warnings,
    }, curve
