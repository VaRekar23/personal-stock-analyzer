"""Provider registry — selects concrete providers based on configuration.

Business logic asks the registry for a provider by role; it never instantiates
a vendor directly. Live vendors (Zerodha/TrueData/OpenAI) are wired here when
credentials are verified. In V1 everything resolves to mock providers.
"""
from __future__ import annotations

from ..core.config import (DATA_PROVIDER, FUNDAMENTAL_PROVIDER, NEWS_PROVIDER,
                           AI_PROVIDER)
from .mock.market import MockMarketDataProvider
from .mock.fundamental import MockFundamentalDataProvider
from .mock.news import MockNewsProvider
from .mock.portfolio import MockPortfolioProvider
from .knowledge import NullKnowledgeProvider
from ..ai.mock_provider import MockAIProvider

_market = MockMarketDataProvider()
_fundamental = MockFundamentalDataProvider()
_news = MockNewsProvider()
_portfolio = MockPortfolioProvider(_market)
_knowledge = NullKnowledgeProvider()
_ai = MockAIProvider()


def market_provider():
    return _market  # only 'mock' available in V1


def fundamental_provider():
    return _fundamental


def news_provider():
    return _news


def portfolio_provider():
    return _portfolio


def ai_provider():
    return _ai


def knowledge_provider():
    return _knowledge


def provider_modes() -> dict:
    return {
        "data": {"selected": DATA_PROVIDER, "mode": _market.mode, "live": False},
        "fundamental": {"selected": FUNDAMENTAL_PROVIDER, "mode": _fundamental.mode, "live": False},
        "news": {"selected": NEWS_PROVIDER, "mode": _news.mode, "live": False},
        "ai": {"selected": AI_PROVIDER, "mode": "mock", "live": False},
        "knowledge": {"selected": "null", "mode": _knowledge.mode, "live": False},
    }
