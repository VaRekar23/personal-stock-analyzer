"""Provider registry — selects concrete providers based on configuration.

Business logic asks the registry for a provider by role; it never instantiates
a vendor directly. Selection is DYNAMIC so switching to a live provider (e.g.
after a Kite login) takes effect without code changes:
  - market/portfolio -> Kite when DATA_PROVIDER=zerodha AND a Kite session exists,
    else the deterministic mock (clearly labelled).
  - ai -> OpenAI when AI_PROVIDER=openai and a key is configured, else mock.
"""
from __future__ import annotations

from ..core.config import (DATA_PROVIDER, FUNDAMENTAL_PROVIDER, NEWS_PROVIDER,
                           AI_PROVIDER, OPENAI_API_KEY)
from ..core.logging_config import get_logger
from .mock.market import MockMarketDataProvider
from .mock.fundamental import MockFundamentalDataProvider
from .mock.news import MockNewsProvider
from .mock.portfolio import MockPortfolioProvider
from .knowledge import NullKnowledgeProvider
from .zerodha import session as kite_session
from ..ai.mock_provider import MockAIProvider

logger = get_logger("stockai.registry")

_mock_market = MockMarketDataProvider()
_fundamental = MockFundamentalDataProvider()
_news = MockNewsProvider()
_mock_portfolio = MockPortfolioProvider(_mock_market)
_knowledge = NullKnowledgeProvider()

_kite_market = None
_kite_portfolio = None
_ai_singleton = None


def _kite_enabled() -> bool:
    return DATA_PROVIDER == "zerodha" and kite_session.has_token()


def market_provider():
    global _kite_market
    if _kite_enabled():
        if _kite_market is None:
            from .zerodha.live import KiteMarketDataProvider
            _kite_market = KiteMarketDataProvider()
        return _kite_market
    return _mock_market


def portfolio_provider():
    global _kite_portfolio
    if _kite_enabled():
        if _kite_portfolio is None:
            from .zerodha.live import KitePortfolioProvider
            _kite_portfolio = KitePortfolioProvider()
        return _kite_portfolio
    return _mock_portfolio


def fundamental_provider():
    return _fundamental


def news_provider():
    return _news


def ai_provider():
    global _ai_singleton
    if _ai_singleton is not None:
        return _ai_singleton
    if AI_PROVIDER == "openai" and OPENAI_API_KEY:
        try:
            from ..ai.openai_provider import OpenAIProvider
            _ai_singleton = OpenAIProvider()
            logger.info("AI provider: openai (%s)", _ai_singleton.model)
            return _ai_singleton
        except Exception as e:  # noqa: BLE001
            logger.warning("OpenAI init failed, falling back to mock: %s", e)
    _ai_singleton = MockAIProvider()
    return _ai_singleton


def knowledge_provider():
    return _knowledge


def data_source() -> str:
    return "zerodha" if _kite_enabled() else "mock"


def provider_modes() -> dict:
    ai = ai_provider()
    return {
        "data": {"selected": DATA_PROVIDER, "mode": data_source(),
                 "live": _kite_enabled()},
        "fundamental": {"selected": FUNDAMENTAL_PROVIDER, "mode": _fundamental.mode, "live": False},
        "news": {"selected": NEWS_PROVIDER, "mode": _news.mode, "live": False},
        "ai": {"selected": AI_PROVIDER, "mode": getattr(ai, "name", "mock"),
               "model": getattr(ai, "model", "mock"),
               "live": getattr(ai, "name", "mock") == "openai"},
        "knowledge": {"selected": "null", "mode": _knowledge.mode, "live": False},
    }
