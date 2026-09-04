"""Deterministic Risk Engine (risk_version = risk_v1).

Computes HYPOTHETICAL trade setups (entry/zone, stop, targets, R:R, position
size). The AI must NOT invent trade prices — these are authoritative. Nothing
here places orders. Risk assumptions (capital, risk %, ATR multipliers) are
configurable (config / Settings), never hard-coded.
"""
from __future__ import annotations


def _round(x, tick=0.05):
    if x is None:
        return None
    return round(round(x / tick) * tick, 2)


def build_setup(*, bias: str, price: float, atr: float | None,
                support: float | None, resistance: float | None,
                risk_cfg: dict, mode: str) -> dict | None:
    """Return a hypothetical trade setup or None if bias is neutral/insufficient."""
    if bias not in ("bullish", "bearish") or price is None or atr is None or atr <= 0:
        return {
            "direction": bias.upper() if bias else "NEUTRAL",
            "setup_validity": "no_setup",
            "reason": "Neutral bias or insufficient volatility data for a setup.",
        }

    if mode == "intraday":
        stop_mult = risk_cfg["atr_stop_multiplier_intraday"]
        t1_mult = risk_cfg["atr_target1_multiplier_intraday"]
        t2_mult = risk_cfg["atr_target2_multiplier_intraday"]
    else:
        stop_mult = risk_cfg["atr_stop_multiplier_swing"]
        t1_mult = risk_cfg["atr_target1_multiplier_swing"]
        t2_mult = risk_cfg["atr_target2_multiplier_swing"]

    direction = "LONG" if bias == "bullish" else "SHORT"
    zone_half = atr * 0.25

    if direction == "LONG":
        entry = price
        entry_low, entry_high = price - zone_half, price + zone_half
        stop = price - stop_mult * atr
        if support and support < price:
            stop = min(stop, support - 0.1 * atr)
        t1 = price + t1_mult * atr
        t2 = price + t2_mult * atr
    else:
        entry = price
        entry_low, entry_high = price - zone_half, price + zone_half
        stop = price + stop_mult * atr
        if resistance and resistance > price:
            stop = max(stop, resistance + 0.1 * atr)
        t1 = price - t1_mult * atr
        t2 = price - t2_mult * atr

    risk_per_share = abs(entry - stop)
    reward1 = abs(t1 - entry)
    reward2 = abs(t2 - entry)
    rr1 = round(reward1 / risk_per_share, 2) if risk_per_share else None
    rr2 = round(reward2 / risk_per_share, 2) if risk_per_share else None

    capital = risk_cfg.get("account_capital", 0)
    risk_amount = capital * risk_cfg.get("risk_per_trade_pct", 1.0) / 100
    qty = int(risk_amount / risk_per_share) if risk_per_share else 0
    capital_required = round(qty * entry, 2)

    return {
        "direction": direction,
        "entry": _round(entry),
        "entry_zone": [_round(min(entry_low, entry_high)), _round(max(entry_low, entry_high))],
        "stop_loss": _round(stop),
        "target_1": _round(t1),
        "target_2": _round(t2),
        "risk_per_share": _round(risk_per_share),
        "reward_per_share_1": _round(reward1),
        "reward_per_share_2": _round(reward2),
        "risk_reward_1": rr1,
        "risk_reward_2": rr2,
        "position_size": qty,
        "capital_required": capital_required,
        "risk_amount": round(risk_amount, 2),
        "setup_validity": "valid",
        "assumptions": {
            "atr": atr, "stop_multiplier": stop_mult,
            "target1_multiplier": t1_mult, "target2_multiplier": t2_mult,
            "risk_per_trade_pct": risk_cfg.get("risk_per_trade_pct"),
            "account_capital": capital,
        },
        "risk_version": "risk_v1",
    }
