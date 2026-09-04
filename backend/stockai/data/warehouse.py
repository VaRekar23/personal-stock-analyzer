"""Market-data warehouse & ingestion service.

Principle: fetch once, store, reuse. Historical data is not re-downloaded for
every analysis. Ingestion is idempotent (composite PK + ON CONFLICT DO NOTHING),
supports incremental updates (only missing candles) and records job runs. If
Postgres is unavailable it falls back to deterministic in-memory generation so
the pipeline still works (Data Health then reports DB DOWN).
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timedelta, timezone

from ..core import db
from ..core.logging_config import get_logger

logger = get_logger("stockai.warehouse")
IST = timezone(timedelta(hours=5, minutes=30))

_TABLE = {"1m": "market.candles_1m", "5m": "market.candles_5m",
          "15m": "market.candles_15m", "1h": "market.candles_1h",
          "1d": "market.candles_1d"}

_DESIRED = {"1d": 400, "1h": 300, "15m": 260, "5m": 300, "1m": 375}


class Warehouse:
    def __init__(self, market_provider):
        self.market = market_provider
        self.last_ingestion: dict[str, str] = {}

    async def sync_instruments(self) -> int:
        instruments = await self.market.get_instruments()
        if not db.is_up():
            return 0
        rows = [(i["symbol"], i["name"], i.get("exchange", "NSE"),
                 i.get("segment", "EQ"), i.get("instrument_token"),
                 i.get("sector")) for i in instruments]
        await db.executemany(
            """INSERT INTO market.instruments
               (symbol,name,exchange,segment,instrument_token,sector)
               VALUES ($1,$2,$3,$4,$5,$6)
               ON CONFLICT (symbol) DO UPDATE SET name=EXCLUDED.name,
               sector=EXCLUDED.sector""", rows)
        return len(rows)

    async def _ingest(self, symbol: str, interval: str, count: int) -> int:
        """Fetch from provider and upsert missing candles (idempotent)."""
        end = datetime.now(IST)
        minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}[interval]
        start = end - timedelta(minutes=minutes * count)
        candles = await self.market.get_candles(symbol, interval, start, end)
        table = _TABLE[interval]
        if db.is_up():
            rows = [(symbol, datetime.fromisoformat(c["ts"]), c["open"], c["high"],
                     c["low"], c["close"], c["volume"], c.get("open_interest", 0),
                     c.get("source", "mock")) for c in candles]
            await db.executemany(
                f"""INSERT INTO {table}
                    (symbol,ts,open,high,low,close,volume,open_interest,source)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                    ON CONFLICT (symbol,ts) DO NOTHING""", rows)
            await db.execute(
                """INSERT INTO system.job_runs (job,status,detail,finished_at)
                   VALUES ($1,'success',$2,now())""",
                f"ingest:{interval}:{symbol}",
                json.dumps({"candles": len(rows)}))
        self.last_ingestion[interval] = datetime.now(IST).isoformat()
        return len(candles)

    async def get_candles(self, symbol: str, interval: str,
                          count: int | None = None) -> list[dict]:
        count = count or _DESIRED.get(interval, 300)
        if not db.is_up():
            # Fallback: deterministic in-memory generation.
            end = datetime.now(IST)
            minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "1d": 1440}[interval]
            return await self.market.get_candles(
                symbol, interval, end - timedelta(minutes=minutes * count), end)

        table = _TABLE[interval]
        existing = await db.fetchrow(
            f"SELECT count(*) AS n, max(ts) AS latest FROM {table} WHERE symbol=$1", symbol)
        n = existing["n"] if existing else 0
        stale = True
        if existing and existing["latest"]:
            age_min = (datetime.now(IST) - existing["latest"]).total_seconds() / 60
            stale = age_min > (1440 if interval == "1d" else 30)
        if n < count or stale:
            await self._ingest(symbol, interval, count)

        rows = await db.fetch(
            f"""SELECT ts,open,high,low,close,volume,open_interest,source
                FROM {table} WHERE symbol=$1 ORDER BY ts DESC LIMIT $2""",
            symbol, count)
        rows.reverse()
        return [{"ts": r["ts"].isoformat(), "open": float(r["open"]),
                 "high": float(r["high"]), "low": float(r["low"]),
                 "close": float(r["close"]), "volume": int(r["volume"]),
                 "open_interest": int(r["open_interest"] or 0),
                 "source": r["source"]} for r in rows]

    @staticmethod
    def market_data_version(candles: list[dict]) -> str:
        if not candles:
            return "empty"
        last = candles[-1]
        raw = f"{last['ts']}|{last['close']}|{len(candles)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    async def last_ingestion_summary(self) -> dict:
        if db.is_up():
            row = await db.fetchrow(
                "SELECT job, finished_at FROM system.job_runs "
                "WHERE status='success' ORDER BY finished_at DESC LIMIT 1")
            if row:
                return {"job": row["job"],
                        "at": row["finished_at"].isoformat() if row["finished_at"] else None}
        return {"job": None, "at": self.last_ingestion.get("1d")}
