"""Strategy-evaluation tests (backtest_v1). All fixtures are SYNTHETIC."""
import pytest

from stockai.backtest import fixtures as F
from stockai.backtest.service import validate_request, BacktestError


@pytest.mark.parametrize("case", F.CASES, ids=[c.__name__ for c in F.CASES])
def test_strategy_fixture(case):
    ok, detail = case()
    assert ok, detail


def test_suite_summary_all_pass():
    r = F.run_strategy_evals()
    assert r["failed"] == 0 and r["total"] == len(F.CASES)
    assert all("SYNTHETIC" in x["label"] for x in r["results"])


@pytest.mark.parametrize("bad", [
    {"mode": "long_term", "interval": "1d", "symbols": ["ITC"], "start": "2025-01-01", "end": "2025-06-01"},
    {"mode": "swing", "interval": "15m", "symbols": ["ITC"], "start": "2025-01-01", "end": "2025-06-01"},
    {"mode": "swing", "interval": "1d", "symbols": [], "start": "2025-01-01", "end": "2025-06-01"},
    {"mode": "swing", "interval": "1d", "symbols": ["ITC"], "start": "2025-06-01", "end": "2025-01-01"},
    {"mode": "swing", "interval": "1d", "symbols": ["ITC"], "start": "2025-01-01", "end": "2025-06-01",
     "universe": "NIFTY50"},
    {"mode": "intraday", "interval": "5m", "symbols": ["ITC"], "start": "2024-01-01", "end": "2025-06-01"},
])
def test_request_validation_rejects(bad):
    with pytest.raises(BacktestError):
        validate_request(bad)


def test_request_normalised():
    r = validate_request({"mode": "swing", "interval": "1d", "symbols": [" itc", "ITC", "tcs"],
                          "start": "2025-01-01", "end": "2025-06-01"})
    assert r["symbols"] == ["ITC", "TCS"] and r["slippage_bps"] == 0
