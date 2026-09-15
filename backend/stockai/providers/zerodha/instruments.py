"""Zerodha instrument master — symbol -> instrument_token resolution.

Design goals (Cloud Run friendly, cost-conscious, robust):
- Download the current NSE equity instrument master ONCE, not per request.
- Cache it in Redis (shared across stateless Cloud Run instances) + in-memory
  per instance, with TTL-based refresh.
- Match equity rows by ``instrument_type == "EQ"`` (canonical), keyed by NSE
  ``tradingsymbol`` — this does not depend on fragile ``segment`` values.
- A targeted ``ltp("NSE:SYMBOL")`` fallback resolves any valid NSE symbol that
  is missing from the cached master (the Kite API resolves exchange:symbol
  server-side and returns the instrument_token), then caches it.
- Genuinely unknown symbols raise UnknownSymbolError -> HTTP 404 (not 500).

Diagnostics are logged at each step so we can tell apart: master unavailable,
auth failure, symbol-not-found, wrong exchange, or stale cache.
"""
from __future__ import annotations
import asyncio
import time

from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException, TokenException

from ...core import cache
from ...core.config import ZERODHA_API_KEY
from ...core.logging_config import get_logger
from ..base import UnknownSymbolError
from . import session

logger = get_logger("stockai.kite.instruments")

_MASTER_CACHE_KEY = "kite:instrument_master"
_MASTER_REDIS_TTL = 12 * 3600   # seconds the master lives in Redis
_MEM_TTL = 6 * 3600             # seconds the in-memory copy is considered fresh

_mem: dict[str, int] = {}       # tradingsymbol (upper) -> instrument_token
_mem_loaded_at = 0.0
_lock = asyncio.Lock()


def _client() -> KiteConnect:
    k = KiteConnect(api_key=ZERODHA_API_KEY)
    tok = session.get_access_token()
    if not tok:
        raise TokenException("Zerodha Kite not connected; daily login required")
    k.set_access_token(tok)
    return k


async def _download_master() -> dict[str, int]:
    """Download the full NSE dump and keep equity rows only."""
    k = _client()
    rows = await asyncio.to_thread(k.instruments, "NSE")
    master: dict[str, int] = {}
    for r in rows:
        if r.get("instrument_type") == "EQ" and r.get("exchange") == "NSE":
            ts = (r.get("tradingsymbol") or "").upper()
            tok = r.get("instrument_token")
            if ts and tok:
                master[ts] = int(tok)
    if not master:
        raise KiteException("Instrument master download returned no NSE equity rows")
    return master


async def load_master(force: bool = False) -> dict[str, int]:
    """Return the symbol->token master, loading/refreshing only when needed."""
    global _mem, _mem_loaded_at
    if not force and _mem and (time.time() - _mem_loaded_at) < _MEM_TTL:
        return _mem
    async with _lock:
        # re-check inside the lock (another coroutine may have loaded it)
        if not force and _mem and (time.time() - _mem_loaded_at) < _MEM_TTL:
            return _mem
        if not force:
            cached = await cache.get_json(_MASTER_CACHE_KEY)
            if cached:
                _mem = {str(k).upper(): int(v) for k, v in cached.items()}
                _mem_loaded_at = time.time()
                logger.info("Instrument master loaded from Redis (%d symbols)", len(_mem))
                return _mem
        master = await _download_master()
        _mem = master
        _mem_loaded_at = time.time()
        await cache.set_json(_MASTER_CACHE_KEY, master, _MASTER_REDIS_TTL)
        logger.info("Instrument master downloaded from Kite (%d NSE equity symbols)",
                    len(master))
        return _mem


async def _ltp_token(symbol: str) -> int | None:
    """Targeted fallback: Kite resolves 'NSE:SYMBOL' -> instrument_token."""
    key = f"NSE:{symbol}"
    k = _client()
    q = await asyncio.to_thread(k.ltp, [key])
    tok = (q.get(key) or {}).get("instrument_token")
    return int(tok) if tok else None


async def resolve(symbol: str) -> int:
    """Resolve a tradingsymbol to its NSE instrument_token.

    Order: in-memory -> cached/downloaded master -> targeted ltp() fallback.
    Raises TokenException (auth) / UnknownSymbolError (404) on failure.
    """
    sym = (symbol or "").upper().strip()
    if not sym:
        raise UnknownSymbolError(symbol or "", reason="empty_symbol")
    if sym in _mem:
        return _mem[sym]
    try:
        master = await load_master()
    except (TokenException, KiteException):
        raise
    except Exception as e:  # noqa: BLE001 — master unavailable; try targeted lookup
        logger.warning("Instrument master unavailable (%s: %s); targeted lookup for %s",
                       type(e).__name__, e, sym)
        master = {}
    tok = master.get(sym)
    if tok:
        return tok
    try:
        tok = await _ltp_token(sym)
    except (TokenException, KiteException):
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("ltp fallback error for %s: %s: %s", sym, type(e).__name__, e)
        tok = None
    if tok:
        _mem[sym] = tok
        logger.info("Resolved %s via targeted lookup -> token %s", sym, tok)
        return tok
    logger.warning("Unknown/unresolvable NSE symbol: %s", sym)
    raise UnknownSymbolError(sym, reason="not_found")
