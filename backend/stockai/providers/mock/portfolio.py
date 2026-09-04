"""MockPortfolioProvider — deterministic sample Zerodha-style holdings.

Represents a hypothetical personal portfolio. source='mock'. The live Zerodha
adapter (pending credential verification) will implement the same interface.
"""
from __future__ import annotations
import hashlib

from .market import MockMarketDataProvider

# Hypothetical holdings (symbol, qty). Average price derived deterministically.
_HOLDINGS = [
    ("RELIANCE", 40), ("TCS", 15), ("HDFCBANK", 60), ("INFY", 50),
    ("ITC", 200), ("TATAMOTORS", 120), ("SBIN", 90), ("LT", 25),
    ("SUNPHARMA", 45), ("TATASTEEL", 300),
]


class MockPortfolioProvider:
    mode = "mock"

    def __init__(self, market: MockMarketDataProvider | None = None):
        self.market = market or MockMarketDataProvider()

    async def get_holdings(self) -> list[dict]:
        out = []
        for symbol, qty in _HOLDINGS:
            quote = await self.market.get_quote(symbol)
            ltp = quote["last_price"]
            # deterministic entry offset -12%..+12% around ltp
            d = int(hashlib.sha256((symbol + "avg").encode()).hexdigest(), 16)
            offset = ((d % 240) - 120) / 1000.0
            avg = round(ltp * (1 - offset), 2)
            out.append({
                "symbol": symbol, "quantity": qty, "average_price": avg,
                "last_price": ltp, "source": "mock",
            })
        return out

    async def get_positions(self) -> list[dict]:
        return []  # No intraday positions in the sample portfolio.
