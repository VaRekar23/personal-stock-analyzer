"""Unit tests for deterministic engines (indicators, scoring, risk, cache keys).

Pure functions only — no DB/network. Run: `cd /app/backend && python -m pytest tests -q`.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from stockai.indicators import engine as ind
from stockai.scoring.engine import Factor, score_factors
from stockai.risk import engine as risk
from stockai.ai.service import make_cache_key
from stockai.providers.mock.market import MockMarketDataProvider


def _candles(n=120, start=100.0):
    out, p = [], start
    for i in range(n):
        o = p; c = p * (1 + (0.002 if i % 2 == 0 else -0.001))
        out.append({"ts": f"2026-01-{(i % 28)+1:02d}T00:00:00+05:30",
                    "open": o, "high": max(o, c) * 1.01, "low": min(o, c) * 0.99,
                    "close": c, "volume": 100000 + i * 10, "open_interest": 0, "source": "mock"})
        p = c
    return out


def test_indicators_structured_output():
    f = ind.compute_features("TEST", _candles(), "1d")
    assert f["symbol"] == "TEST"
    assert f["indicator_version"] == "technical_v1"
    assert 0 <= f["rsi"] <= 100
    assert f["ema20"] is not None and f["ema50"] is not None
    assert f["trend"] in ("uptrend", "downtrend", "sideways")


def test_rsi_bounds_and_atr_positive():
    closes = np.array([float(x) for x in range(1, 60)])
    assert ind.rsi(closes) == 100.0  # strictly rising
    assert ind.atr(_candles()) > 0


def test_scoring_missing_data_not_negative():
    factors = [
        Factor("a", "A", 0.5, 80.0),
        Factor("b", "B", 0.5, None),  # missing
    ]
    r = score_factors(factors)
    assert abs(r.score - 80.0) < 1e-6      # missing factor excluded, not zeroed
    assert r.confidence == 0.5             # half the weight had data
    assert "B" in r.missing


def test_scoring_bias_thresholds():
    assert score_factors([Factor("a", "A", 1.0, 90.0)]).bias == "bullish"
    assert score_factors([Factor("a", "A", 1.0, 10.0)]).bias == "bearish"
    assert score_factors([Factor("a", "A", 1.0, 50.0)]).bias == "neutral"


def test_risk_setup_long_rr_and_authority():
    cfg = {"account_capital": 1000000, "risk_per_trade_pct": 1.0,
           "atr_stop_multiplier_swing": 1.5, "atr_target1_multiplier_swing": 2.0,
           "atr_target2_multiplier_swing": 3.5, "atr_stop_multiplier_intraday": 1.0,
           "atr_target1_multiplier_intraday": 1.2, "atr_target2_multiplier_intraday": 2.0}
    s = risk.build_setup(bias="bullish", price=1000, atr=20, support=None,
                         resistance=None, risk_cfg=cfg, mode="swing")
    assert s["direction"] == "LONG"
    assert s["stop_loss"] < s["entry"] < s["target_1"] < s["target_2"]
    assert s["risk_reward_1"] > 0 and s["position_size"] >= 0


def test_risk_neutral_no_setup():
    s = risk.build_setup(bias="neutral", price=1000, atr=20, support=None,
                         resistance=None, risk_cfg={}, mode="swing")
    assert s["setup_validity"] == "no_setup"


def test_cache_key_varies_by_type_and_version():
    base = dict(market_data_version="v1", strategy_version="swing_v1",
                prompt_version="p1", provider="mock", model="m", date_context="2026-01-01")
    k_swing = make_cache_key("RELIANCE", "swing", **base)
    k_long = make_cache_key("RELIANCE", "long_term", **{**base, "strategy_version": "long_term_v1"})
    assert k_swing != k_long
    assert k_swing == make_cache_key("RELIANCE", "swing", **base)  # deterministic


def test_mock_market_reproducible():
    m = MockMarketDataProvider()
    a = m._series("RELIANCE", "1d", 10)
    b = m._series("RELIANCE", "1d", 10)
    assert [c["close"] for c in a] == [c["close"] for c in b]
