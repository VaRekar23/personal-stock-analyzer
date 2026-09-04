"""Provider interfaces (Protocols). Mandatory abstraction layer.

The rest of the application depends ONLY on these interfaces. Concrete vendors
(Zerodha, TrueData, OpenAI, ...) implement them. This is required so providers
can be replaced without rewriting analysis/business logic.
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from datetime import datetime


@runtime_checkable
class MarketDataProvider(Protocol):
    mode: str  # "mock" | "live"

    async def get_instruments(self) -> list[dict]: ...

    async def get_candles(self, symbol: str, interval: str,
                          start: datetime, end: datetime) -> list[dict]: ...

    async def get_quote(self, symbol: str) -> dict: ...


@runtime_checkable
class FundamentalDataProvider(Protocol):
    mode: str

    async def get_fundamentals(self, symbol: str) -> dict: ...


@runtime_checkable
class NewsProvider(Protocol):
    mode: str

    async def get_news(self, symbol: str, limit: int = 10) -> list[dict]: ...


@runtime_checkable
class PortfolioProvider(Protocol):
    mode: str

    async def get_holdings(self) -> list[dict]: ...

    async def get_positions(self) -> list[dict]: ...


@runtime_checkable
class AIProvider(Protocol):
    """AI is an explanation/reasoning layer over structured facts.

    It must NOT calculate indicators or invent trade levels; it consumes the
    deterministic context and returns a structured, grounded explanation.
    """
    name: str
    model: str

    async def generate(self, prompt: str, context: dict,
                       response_schema: dict | None = None) -> dict: ...


@runtime_checkable
class KnowledgeProvider(Protocol):
    """RAG integration point (V2). V1 ships a no-op stub; document retrieval
    (annual reports, transcripts, filings) plugs in here later. Never used for
    computing RSI/EMA/ATR/VWAP/price/stop/target — those are deterministic.
    """
    mode: str

    async def retrieve(self, query: str, symbol: str | None = None,
                       k: int = 5) -> list[dict]: ...
