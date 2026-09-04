"""Live Zerodha / Kite Connect adapters (market data + portfolio).

pykiteconnect is synchronous; calls are wrapped with asyncio.to_thread. Symbols
are mapped to instrument_token via a cached NSE instruments dump (refreshed
daily). Historical intervals map 1m→minute, 5m→5minute, 15m→15minute,
1h→60minute, 1d→day. Sector is attached from our documented NIFTY 50 mapping
(Kite does not provide sector). Read-only: NO order placement.
"""
from __future__ import annotations
import asyncio
from datetime import datetime

from kiteconnect import KiteConnect
from kiteconnect.exceptions import TokenException, KiteException

from ...core.config import ZERODHA_API_KEY
from ...core.logging_config import get_logger
from ...data.nifty50 import SYMBOLS, SECTOR_OF, NAME_OF
from . import session

logger = get_logger("stockai.kite")

_INTERVAL = {"1m": "minute", "5m": "5minute", "15m": "15minute",
             "1h": "60minute", "1d": "day"}
_token_cache: dict[str, int] = {}   # symbol -> instrument_token


def _client() -> KiteConnect:
    k = KiteConnect(api_key=ZERODHA_API_KEY)
    tok = session.get_access_token()
    if not tok:
        raise TokenException("Kite not connected; login required")
    k.set_access_token(tok)
    return k


async def _run(fn, *args, **kwargs):
    return await asyncio.to_thread(fn, *args, **kwargs)


async def _ensure_instruments() -> None:
    if _token_cache:
        return
    k = _client()
    rows = await _run(k.instruments, "NSE")
    wanted = set(SYMBOLS)
    for r in rows:
        if r.get("segment") == "NSE" and r.get("tradingsymbol") in wanted:
            _token_cache[r["tradingsymbol"]] = r["instrument_token"]


class KiteMarketDataProvider:
    name = "zerodha"
    mode = "live"

    async def get_instruments(self) -> list[dict]:
        try:
            await _ensure_instruments()
        except (TokenException, KiteException) as e:
            logger.warning("kite instruments failed: %s", e)
        return [{"symbol": s, "name": NAME_OF.get(s, s), "exchange": "NSE",
                 "segment": "EQ", "instrument_token": _token_cache.get(s),
                 "sector": SECTOR_OF.get(s)} for s in SYMBOLS]

    async def get_candles(self, symbol: str, interval: str,
                          start: datetime, end: datetime) -> list[dict]:
        await _ensure_instruments()
        token = _token_cache.get(symbol.upper())
        if not token:
            raise KiteException(f"No instrument_token for {symbol}")
        k = _client()
        kint = _INTERVAL[interval]
        raw = await _run(k.historical_data, token,
                         start.strftime("%Y-%m-%d %H:%M:%S"),
                         end.strftime("%Y-%m-%d %H:%M:%S"), kint, False,
                         interval != "1d")  # oi for intraday/derivatives only
        out = []
        for c in raw:
            d = c["date"]
            out.append({"ts": d.isoformat() if hasattr(d, "isoformat") else str(d),
                        "open": float(c["open"]), "high": float(c["high"]),
                        "low": float(c["low"]), "close": float(c["close"]),
                        "volume": int(c.get("volume", 0)),
                        "open_interest": int(c.get("oi", 0) or 0),
                        "source": "zerodha"})
        return out

    async def get_quote(self, symbol: str) -> dict:
        k = _client()
        key = f"NSE:{symbol.upper()}"
        q = await _run(k.quote, [key])
        d = q.get(key, {})
        return {"symbol": symbol.upper(), "last_price": d.get("last_price"),
                "source": "zerodha"}


class KitePortfolioProvider:
    name = "zerodha"
    mode = "live"

    async def get_holdings(self) -> list[dict]:
        k = _client()
        rows = await _run(k.holdings)
        out = []
        for h in rows:
            sym = h.get("tradingsymbol")
            out.append({
                "symbol": sym, "name": NAME_OF.get(sym, sym),
                "sector": SECTOR_OF.get(sym, "market"),
                "quantity": h.get("quantity", 0),
                "average_price": h.get("average_price", 0.0),
                "last_price": h.get("last_price", 0.0),
                "source": "zerodha"})
        return out

    async def get_positions(self) -> list[dict]:
        k = _client()
        pos = await _run(k.positions)
        return pos.get("net", []) if isinstance(pos, dict) else []
