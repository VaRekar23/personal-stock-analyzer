"""Yahoo Finance providers via the `yfinance` library (fundamentals + news).

Replaces the pending TrueData integration for V1. Indian NSE symbols are mapped
to Yahoo tickers with the `.NS` suffix. yfinance is synchronous & network-bound,
so calls run in a threadpool with a timeout and are cached in Redis (6h) to avoid
hammering Yahoo / hitting rate limits (important for the 50-stock scanner).

NOTE: Yahoo Finance is a best-effort public source, not a contractual data feed.
Every field is best-effort; missing values are returned as null ('data
unavailable') and NEVER fabricated. Values are labelled source='yfinance'.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone

import yfinance as yf

from ..core import cache
from ..core.logging_config import get_logger
from ..data.nifty50 import NAME_OF, SECTOR_OF

logger = get_logger("stockai.providers.yfinance")

_FUND_TTL = 6 * 3600
_NEWS_TTL = 30 * 60
_TIMEOUT = 12.0


def _yahoo_symbol(symbol: str) -> str:
    return f"{symbol.upper()}.NS"


def _pct(v):
    """Yahoo fractions (0.24) -> percent (24.0). Pass-through if already percent-ish."""
    if v is None:
        return None
    try:
        return round(float(v) * 100, 2)
    except (TypeError, ValueError):
        return None


def _cr(v):
    """Absolute INR -> ₹ crore."""
    if v is None:
        return None
    try:
        return round(float(v) / 1e7, 1)
    except (TypeError, ValueError):
        return None


def _num(v, nd=2):
    if v is None:
        return None
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return None


def _fetch_fundamentals_sync(symbol: str) -> dict:
    info = yf.Ticker(_yahoo_symbol(symbol)).info or {}
    now = datetime.now(timezone.utc).isoformat()
    de_raw = info.get("debtToEquity")  # Yahoo reports as percent (e.g. 36.65)
    de_ratio = round(de_raw / 100, 2) if isinstance(de_raw, (int, float)) else None
    ocf = info.get("operatingCashflow")
    fcf = info.get("freeCashflow")
    capex = (ocf - fcf) if (isinstance(ocf, (int, float)) and isinstance(fcf, (int, float))) else None
    insiders = _pct(info.get("heldPercentInsiders"))
    inst = _pct(info.get("heldPercentInstitutions"))
    public = None
    if insiders is not None or inst is not None:
        public = round(max(0.0, 100 - (insiders or 0) - (inst or 0)), 1)

    corp = []
    if info.get("lastDividendValue"):
        ex = info.get("lastDividendDate")
        ex_date = (datetime.fromtimestamp(ex, tz=timezone.utc).date().isoformat()
                   if isinstance(ex, (int, float)) else None)
        corp.append({"action_type": "dividend", "ex_date": ex_date,
                     "details": {"amount_per_share": _num(info.get("lastDividendValue"))},
                     "source": "yfinance"})

    return {
        "symbol": symbol,
        "company_name": info.get("longName") or NAME_OF.get(symbol, symbol),
        "sector": info.get("sector") or SECTOR_OF.get(symbol),
        "source": "yfinance",
        "retrieved_at": now,
        "period": "TTM / latest (Yahoo Finance)",
        "current_price": _num(info.get("currentPrice")),
        "market_cap_cr": _cr(info.get("marketCap")),
        "income_statement": {
            "revenue": _cr(info.get("totalRevenue")),
            "revenue_growth_pct": _pct(info.get("revenueGrowth")),
            "ebitda_margin_pct": _pct(info.get("ebitdaMargins")),
            "pat": _cr(info.get("netIncomeToCommon")),
            "pat_growth_pct": _pct(info.get("earningsGrowth")),
            "eps": _num(info.get("trailingEps")),
        },
        "balance_sheet": {
            "total_assets": None,
            "equity": None,
            "debt": _cr(info.get("totalDebt")),
            "cash": _cr(info.get("totalCash")),
            "net_debt": (_cr((info.get("totalDebt") or 0) - (info.get("totalCash") or 0))
                         if info.get("totalDebt") is not None else None),
        },
        "cash_flow": {
            "operating_cash_flow": _cr(ocf), "capex": _cr(capex), "free_cash_flow": _cr(fcf),
        },
        "valuation": {
            "pe": _num(info.get("trailingPE"), 1),
            "pb": _num(info.get("priceToBook"), 2),
            "roe_pct": _pct(info.get("returnOnEquity")),
            "roce_pct": None,  # Not provided by Yahoo — data unavailable, not fabricated
            "debt_to_equity": de_ratio,
            "dividend_yield_pct": _num(info.get("dividendYield"), 2),
            "ebitda_margin_pct": _pct(info.get("ebitdaMargins")),
        },
        "shareholding": {
            "promoter_pct": insiders, "fii_pct": inst,
            "dii_pct": None, "public_pct": public,
            "note": "Yahoo reports insider/institutional %; FII/DII split unavailable.",
        },
        "corporate_actions": corp,
    }


def _unavailable(symbol: str, err: str) -> dict:
    return {
        "symbol": symbol, "company_name": NAME_OF.get(symbol, symbol),
        "sector": SECTOR_OF.get(symbol), "source": "yfinance",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "period": None, "error": err,
        "income_statement": {}, "balance_sheet": {}, "cash_flow": {},
        "valuation": {}, "shareholding": {}, "corporate_actions": [],
    }


class YFinanceFundamentalProvider:
    mode = "yfinance"

    async def get_fundamentals(self, symbol: str) -> dict:
        symbol = symbol.upper()
        ck = f"fund:yf:{symbol}"
        cached = await cache.get_json(ck)
        if cached:
            return cached
        try:
            data = await asyncio.wait_for(
                asyncio.to_thread(_fetch_fundamentals_sync, symbol), timeout=_TIMEOUT)
        except Exception as e:  # noqa: BLE001 — never fabricate; mark unavailable
            logger.warning("yfinance fundamentals failed for %s: %s", symbol, type(e).__name__)
            data = _unavailable(symbol, f"{type(e).__name__}: {e}")
            await cache.set_json(ck, data, 300)  # short TTL so it retries soon
            return data
        await cache.set_json(ck, data, _FUND_TTL)
        return data


def _fetch_news_sync(symbol: str, limit: int) -> list[dict]:
    items = yf.Ticker(_yahoo_symbol(symbol)).get_news(count=limit) or []
    out = []
    for it in items:
        c = it.get("content", it) if isinstance(it, dict) else {}
        title = c.get("title") or it.get("title")
        if not title:
            continue
        url = ((c.get("canonicalUrl") or {}).get("url")
               if isinstance(c.get("canonicalUrl"), dict) else it.get("link"))
        published = c.get("pubDate") or c.get("displayTime")
        provider = ((c.get("provider") or {}).get("displayName")
                    if isinstance(c.get("provider"), dict) else it.get("publisher")) or "Yahoo Finance"
        out.append({
            "source": provider, "headline": title, "published_at": published,
            "url": url, "symbol": symbol,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "category": (c.get("contentType") or "news"),
            "sentiment": None,  # never fabricate sentiment
        })
    return out


class YFinanceNewsProvider:
    mode = "yfinance"

    async def get_news(self, symbol: str, limit: int = 10) -> list[dict]:
        symbol = symbol.upper()
        ck = f"news:yf:{symbol}:{limit}"
        cached = await cache.get_json(ck)
        if cached is not None:
            return cached
        try:
            data = await asyncio.wait_for(
                asyncio.to_thread(_fetch_news_sync, symbol, limit), timeout=_TIMEOUT)
        except Exception as e:  # noqa: BLE001
            logger.warning("yfinance news failed for %s: %s", symbol, type(e).__name__)
            return []
        await cache.set_json(ck, data, _NEWS_TTL)
        return data
