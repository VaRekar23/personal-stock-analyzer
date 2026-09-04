"""MockNewsProvider — deterministic synthetic news headlines.

Clearly labelled source='mock'. News is a separate evidence source, NOT an
automatic trading signal. The AI layer may only reference news items that exist
in supplied context; it must never invent news.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timedelta, timezone

from ...data.nifty50 import NAME_OF, SECTOR_OF

_TEMPLATES = [
    ("{name} reports quarterly update in line with sector trend", "neutral", "results"),
    ("Brokerage maintains constructive view on {name}", "positive", "analyst"),
    ("{name} announces capacity expansion in {sector} segment", "positive", "corporate"),
    ("{sector} sector sees rotation; {name} among watchlist names", "neutral", "sector"),
    ("Margin pressure flagged for parts of the {sector} space", "negative", "sector"),
]


class MockNewsProvider:
    mode = "mock"

    async def get_news(self, symbol: str, limit: int = 10) -> list[dict]:
        name = NAME_OF.get(symbol, symbol)
        sector = SECTOR_OF.get(symbol, "market")
        seed = int(hashlib.sha256(symbol.encode()).hexdigest(), 16)
        out = []
        for i in range(min(limit, len(_TEMPLATES))):
            tpl, sentiment, cat = _TEMPLATES[(seed + i) % len(_TEMPLATES)]
            published = datetime.now(timezone.utc) - timedelta(hours=6 * (i + 1))
            out.append({
                "source": "mock",
                "headline": tpl.format(name=name, sector=sector),
                "published_at": published.isoformat(),
                "url": None,
                "symbol": symbol,
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "category": cat,
                "sentiment": sentiment,
            })
        return out
