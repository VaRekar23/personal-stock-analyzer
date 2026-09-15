"""MarketContextEngine & SectorContextEngine.

Compute broad-market (NIFTY/BANKNIFTY) and sector direction/strength from
warehouse candles. Sector index mapping is explicit/documented (nifty50.py).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone

from ..indicators import engine as ind
from ..data.nifty50 import SECTOR_OF, SECTOR_INDEX, SYMBOLS
from ..core.logging_config import get_logger

logger = get_logger("stockai.context")

IST = timezone(timedelta(hours=5, minutes=30))


def _direction_from_trend(trend: str, rsi: float | None) -> str:
    if trend == "uptrend":
        return "bullish"
    if trend == "downtrend":
        return "bearish"
    if rsi is not None:
        if rsi >= 55:
            return "bullish"
        if rsi <= 45:
            return "bearish"
    return "neutral"


class MarketContextEngine:
    def __init__(self, market_provider):
        self.market = market_provider

    async def _index_view(self, proxy_symbol: str, label: str) -> dict:
        try:
            candles = await self.market.get_candles(proxy_symbol, "1d", 400)
            feats = ind.compute_features(proxy_symbol, candles, "1d")
        except Exception as e:  # noqa: BLE001 — degrade gracefully, never 500
            logger.warning("index view %s (%s) unavailable: %s: %s",
                           label, proxy_symbol, type(e).__name__, e)
            return {"index": label, "direction": "neutral", "trend": None,
                    "rsi": None, "last": None, "unavailable": True,
                    "reason": f"{type(e).__name__}"}
        rsi = feats.get("rsi")
        return {
            "index": label,
            "direction": _direction_from_trend(feats.get("trend"), rsi),
            "trend": feats.get("trend"),
            "rsi": rsi,
            "last": feats.get("last_price"),
        }

    async def compute(self) -> dict:
        # RELIANCE proxies NIFTY, HDFCBANK proxies BANKNIFTY (mock warehouse).
        nifty = await self._index_view("RELIANCE", "NIFTY 50")
        banknifty = await self._index_view("HDFCBANK", "BANK NIFTY")
        bull = sum(1 for x in (nifty, banknifty) if x["direction"] == "bullish")
        breadth = "risk-on" if bull == 2 else ("mixed" if bull == 1 else "risk-off")
        return {
            "nifty": nifty, "banknifty": banknifty,
            "breadth": breadth,
            "as_of": datetime.now(IST).isoformat(),
            "note": "Indices proxied from mock warehouse (DEMO DATA).",
        }


class SectorContextEngine:
    def __init__(self, market_provider):
        self.market = market_provider

    async def compute(self, sector: str) -> dict:
        peers = [s for s in SYMBOLS if SECTOR_OF.get(s) == sector][:6]
        dirs = []
        for s in peers:
            try:
                candles = await self.market.get_candles(s, "1d", 120)
                feats = ind.compute_features(s, candles, "1d")
                dirs.append(_direction_from_trend(feats.get("trend"), feats.get("rsi")))
            except Exception as e:  # noqa: BLE001 — skip unresolvable peers
                logger.warning("sector %s peer %s skipped: %s: %s",
                               sector, s, type(e).__name__, e)
                continue
        if not dirs:
            return {"sector": sector,
                    "mapped_index": SECTOR_INDEX.get(sector, "NIFTY 500 (proxy)"),
                    "direction": "neutral", "constituents_bullish": 0,
                    "constituents_bearish": 0, "sample_size": 0,
                    "unavailable": True}
        bull = dirs.count("bullish")
        bear = dirs.count("bearish")
        direction = "bullish" if bull > bear else ("bearish" if bear > bull else "neutral")
        return {
            "sector": sector,
            "mapped_index": SECTOR_INDEX.get(sector, "NIFTY 500 (proxy)"),
            "direction": direction,
            "constituents_bullish": bull,
            "constituents_bearish": bear,
            "sample_size": len(dirs),
        }

    async def all_sectors(self) -> list[dict]:
        seen = []
        out = []
        for s in SYMBOLS:
            sec = SECTOR_OF.get(s)
            if sec and sec not in seen:
                seen.append(sec)
                out.append(await self.compute(sec))
        return out
