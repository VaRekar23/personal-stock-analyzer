"""Regression: mock and Zerodha candles stored for the same dates must never be mixed."""
import asyncio
from datetime import date, datetime, timedelta, timezone
import pytest

from stockai.core import db
from stockai.backtest import service
from stockai.backtest.quality import assess

IST = timezone(timedelta(hours=5, minutes=30))
SYM = "TESTMIXSRC"


def _bar(d, hh, px, src):
    return {"ts": datetime(d.year, d.month, d.day, hh, 30 if hh == 15 else 0, tzinfo=IST).isoformat(),
            "open": px, "high": px * 1.01, "low": px * 0.99, "close": px, "volume": 1, "source": src}


def test_quality_flags_two_candles_on_same_date():
    d = date(2026, 3, 2)
    c = [_bar(d, 0, 100, "zerodha"), _bar(d, 15, 150, "mock")]
    q = assess(SYM, c, "1d", d, d, 0)
    assert q["duplicates"] == 1 and any("more than one daily candle" in w for w in q["warnings"])
    assert any("mixed data sources" in w for w in q["warnings"])


async def _scenario():
    await db.disconnect()
    await db.connect()
    if not db.is_up():
        return "SKIP"
    try:
        await db.execute("DELETE FROM market.candles_1d WHERE symbol=$1", SYM)
        rows = []
        for i in range(10):
            d = date(2026, 3, 2) + timedelta(days=i)
            for hh, px, src in ((0, 100.0, "zerodha"), (15, 150.0, "mock")):
                rows.append((SYM, datetime.fromisoformat(_bar(d, hh, px, src)["ts"]), px, px, px, px, 1, 0, src))
        await db.executemany(
            """INSERT INTO market.candles_1d (symbol,ts,open,high,low,close,volume,open_interest,source)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT DO NOTHING""", rows)
        real = await service.load_stored(SYM, "1d", "2026-03-01", "2026-03-20")
        await db.execute("DELETE FROM market.candles_1d WHERE symbol=$1 AND source='zerodha'", SYM)
        mock_only = await service.load_stored(SYM, "1d", "2026-03-01", "2026-03-20")
        await db.execute("DELETE FROM market.candles_1d WHERE symbol=$1", SYM)
        return real, mock_only
    finally:
        await db.disconnect()


def test_load_stored_prefers_zerodha_and_never_mixes():
    r = asyncio.run(_scenario())
    if r == "SKIP":
        pytest.skip("PostgreSQL not available")
    real, mock_only = r
    assert len(real) == 10 and {c["source"] for c in real} == {"zerodha"}
    assert len(mock_only) == 10 and {c["source"] for c in mock_only} == {"mock"}
