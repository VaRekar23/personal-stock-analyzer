"""MockMarketDataProvider — deterministic, reproducible synthetic OHLCV.

Data is generated from a per-symbol seed so the same symbol always yields the
same series (reproducible/auditable). Clearly labelled source='mock'. This lets
the whole pipeline (indicators, scoring, risk, AI, evals) run without any live
credentials. Never presented as verified live data.
"""
from __future__ import annotations
import hashlib
import math
import random
from datetime import datetime, timedelta, timezone

from ..base import MarketDataProvider  # noqa: F401 (structural typing)
from ...data.nifty50 import NIFTY50, SYMBOLS

IST = timezone(timedelta(hours=5, minutes=30))

_INTERVAL_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}

# Deterministic per-symbol base price + drift/vol characteristics.
def _seed(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest(), 16) % (2**31)


def _base_price(symbol: str) -> float:
    return 150 + (_seed(symbol) % 4200)


class MockMarketDataProvider:
    mode = "mock"

    async def get_instruments(self) -> list[dict]:
        return [
            {"symbol": s, "name": n, "exchange": "NSE", "segment": "EQ",
             "sector": sec, "instrument_token": _seed(s) % 1000000}
            for s, n, sec in NIFTY50
        ]

    def _series(self, symbol: str, interval: str, count: int) -> list[dict]:
        rng = random.Random(_seed(symbol) + _INTERVAL_MINUTES[interval])
        price = _base_price(symbol)
        drift = ((_seed(symbol) % 7) - 3) * 0.0004  # small per-symbol drift
        vol = 0.012 if interval == "1d" else 0.004
        step = timedelta(minutes=_INTERVAL_MINUTES[interval])
        now = datetime.now(IST).replace(second=0, microsecond=0)
        if interval == "1d":
            now = now.replace(hour=15, minute=30)
        candles = []
        t = now - step * count
        for i in range(count):
            shock = rng.gauss(drift, vol)
            o = price
            c = max(1.0, o * (1 + shock))
            hi = max(o, c) * (1 + abs(rng.gauss(0, vol / 2)))
            lo = min(o, c) * (1 - abs(rng.gauss(0, vol / 2)))
            base_vol = 200000 + (_seed(symbol) % 800000)
            v = int(base_vol * (1 + abs(rng.gauss(0, 0.4))))
            candles.append({
                "ts": t.isoformat(),
                "open": round(o, 2), "high": round(hi, 2),
                "low": round(lo, 2), "close": round(c, 2),
                "volume": v, "open_interest": 0, "source": "mock",
            })
            price = c
            t += step
        return candles

    async def get_candles(self, symbol: str, interval: str,
                          start: datetime, end: datetime) -> list[dict]:
        minutes = _INTERVAL_MINUTES.get(interval, 1440)
        span = max(1, int((end - start).total_seconds() / 60 / minutes))
        count = min(span, 500 if interval != "1d" else 400)
        return self._series(symbol, interval, count)

    async def get_quote(self, symbol: str) -> dict:
        last = self._series(symbol, "1d", 2)
        c = last[-1]
        prev = last[-2]["close"]
        chg = c["close"] - prev
        return {
            "symbol": symbol, "last_price": c["close"],
            "prev_close": prev, "change": round(chg, 2),
            "change_pct": round(chg / prev * 100, 2),
            "volume": c["volume"], "source": "mock",
            "ts": datetime.now(IST).isoformat(),
        }


def market_status(now: datetime | None = None) -> str:
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return "CLOSED"
    t = now.hour * 60 + now.minute
    if 9 * 60 <= t < 9 * 60 + 15:
        return "PRE-MARKET"
    if 9 * 60 + 15 <= t <= 15 * 60 + 30:
        return "OPEN"
    return "CLOSED"
