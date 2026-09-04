"""Backend API integration tests for Personal AI Stock Analysis Platform."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback for backend-only run
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

API = f"{BASE_URL}/api"
TIMEOUT = 60


@pytest.fixture(scope="module")
def sess():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------- Health ----------
class TestHealth:
    def test_health(self, sess):
        r = sess.get(f"{API}/health", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        # services present
        services = d.get("services", d)
        # tolerate different shapes: dict or list
        text = str(d).lower()
        assert "database" in text or "postgres" in text
        assert "cache" in text or "redis" in text
        assert "version" in text or "versions" in text or "version_registry" in text


# ---------- Market Overview ----------
class TestMarket:
    def test_market_overview(self, sess):
        r = sess.get(f"{API}/market/overview", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "market_status" in d
        assert "context" in d or "indices" in d
        sectors = d.get("sectors") or d.get("sector_heatmap") or []
        assert isinstance(sectors, list)
        assert len(sectors) >= 10


# ---------- Analyze ----------
class TestAnalyze:
    def test_analyze_long_term(self, sess):
        r = sess.post(f"{API}/analyze", json={"symbol": "RELIANCE", "mode": "long_term"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        score_obj = d["score"]
        assert 0 <= score_obj["score"] <= 100
        assert 0 <= score_obj["confidence"] <= 1
        assert "factors" in score_obj and isinstance(score_obj["factors"], list)
        assert "fundamentals" in d
        f = d["fundamentals"]
        for k in ("income_statement", "valuation", "cash_flow", "shareholding"):
            assert k in f, f"missing fundamentals.{k}"
        assert "market_context" in d
        assert "sector_context" in d
        ai = d.get("ai") or {}
        for k in ("bias", "summary", "bullish_factors", "bearish_factors", "risks", "invalidation_conditions"):
            assert k in ai, f"missing ai.{k}"
        assert "provenance" in d or "versions" in d

    def test_analyze_swing_trade_setup(self, sess):
        r = sess.post(f"{API}/analyze", json={"symbol": "RELIANCE", "mode": "swing"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        ts = d.get("trade_setup")
        assert ts, "trade_setup missing"
        direction = ts.get("direction", "").upper()
        entry = ts.get("entry")
        stop = ts.get("stop_loss")
        t1 = ts.get("target_1")
        t2 = ts.get("target_2")
        assert all(v is not None for v in (entry, stop, t1, t2))
        assert "risk_reward_1" in ts or "rr_1" in ts
        assert "entry_zone" in ts
        if direction == "LONG":
            assert stop < entry < t1 < t2, f"LONG order invalid: {stop}<{entry}<{t1}<{t2}"

    def test_analyze_intraday(self, sess):
        r = sess.post(f"{API}/analyze", json={"symbol": "RELIANCE", "mode": "intraday"}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        # vwap present in intraday features
        blob = str(d).lower()
        assert "vwap" in blob
        assert d.get("trade_setup") is not None

    def test_analyze_invalid_symbol(self, sess):
        r = sess.post(f"{API}/analyze", json={"symbol": "FOOBAR", "mode": "long_term"}, timeout=TIMEOUT)
        assert r.status_code == 404, f"got {r.status_code}: {r.text}"

    def test_analyze_invalid_mode(self, sess):
        r = sess.post(f"{API}/analyze", json={"symbol": "RELIANCE", "mode": "bogus"}, timeout=TIMEOUT)
        assert r.status_code in (400, 422), f"got {r.status_code}: {r.text}"

    def test_analyze_cache(self, sess):
        payload = {"symbol": "TCS", "mode": "long_term"}
        r1 = sess.post(f"{API}/analyze", json=payload, timeout=TIMEOUT)
        assert r1.status_code == 200
        r2 = sess.post(f"{API}/analyze", json=payload, timeout=TIMEOUT)
        assert r2.status_code == 200
        assert r2.json().get("from_cache") is True


# ---------- Scanner ----------
class TestScan:
    @pytest.mark.parametrize("mode", ["swing", "long_term", "intraday"])
    def test_scan_modes(self, sess, mode):
        r = sess.get(f"{API}/scan", params={"mode": mode}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        results = d.get("results") or d.get("ranked") or []
        assert len(results) == 50, f"expected 50 got {len(results)}"
        scores = [x["score"] for x in results]
        assert scores == sorted(scores, reverse=True), "not sorted desc"
        assert results[0].get("rank") == 1
        if mode == "swing":
            assert (d.get("ai_finalists") or 0) > 0

    def test_scan_cache(self, sess):
        sess.get(f"{API}/scan", params={"mode": "swing"}, timeout=TIMEOUT)
        r = sess.get(f"{API}/scan", params={"mode": "swing"}, timeout=TIMEOUT)
        assert r.json().get("from_cache") is True


# ---------- Portfolio ----------
class TestPortfolio:
    def test_portfolio(self, sess):
        r = sess.get(f"{API}/portfolio", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        s = d.get("summary", d)
        assert s.get("holdings_count") == 10
        for k in ("invested", "current_value", "pnl", "pnl_pct"):
            assert k in s
        for k in ("healthy", "watch", "review"):
            assert k in s
        holdings = d.get("holdings", [])
        assert len(holdings) == 10
        assert all("pnl" in h and "health" in h for h in holdings)
        assert all(h["health"] in ("Healthy", "Watch", "Review") for h in holdings)


# ---------- Fundamentals / News / Candles ----------
class TestData:
    def test_fundamentals(self, sess):
        r = sess.get(f"{API}/fundamentals/TCS", timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json().get("source") == "mock"

    def test_news(self, sess):
        r = sess.get(f"{API}/news/TCS", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        items = d.get("items", [])
        assert len(items) > 0
        assert items[0].get("source") == "mock"

    def test_candles(self, sess):
        r = sess.get(f"{API}/candles/RELIANCE", params={"interval": "1d", "count": 100}, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "candles" in d and len(d["candles"]) > 0
        assert "market_data_version" in d


# ---------- Evals ----------
class TestEvals:
    def test_evals_run(self, sess):
        r = sess.post(f"{API}/evals/run", json={"sample_size": 6}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("passed", "failed", "total", "pass_rate", "avg_score"):
            assert k in d
        # synthetic hallucinations flagged
        results = d.get("results") or d.get("cases") or []
        ids = {(x.get("case_id") or x.get("id")) for x in results}
        # if not in top-level, look at nested
        blob = str(d)
        assert "syn_rsi_consistency_fail" in blob
        assert "syn_entry_override_fail" in blob

    def test_evals_latest(self, sess):
        r = sess.get(f"{API}/evals/latest", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "latest_run" in d
        datasets = d.get("datasets", [])
        assert len(datasets) == 3
        assert "cases" in d
        assert "results" in d


# ---------- Settings ----------
class TestSettings:
    def test_get_settings(self, sess):
        r = sess.get(f"{API}/settings", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        s = d.get("settings", d)
        for k in ("risk", "cache", "thresholds", "providers"):
            assert k in s, f"missing {k}"

    def test_put_settings_risk(self, sess):
        r = sess.put(f"{API}/settings/risk", json={"values": {"risk_per_trade_pct": 1.5}}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        r2 = sess.get(f"{API}/settings", timeout=TIMEOUT)
        s = r2.json().get("settings", r2.json())
        assert float(s["risk"]["risk_per_trade_pct"]) == 1.5
