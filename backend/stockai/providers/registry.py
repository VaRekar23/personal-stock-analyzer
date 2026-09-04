"""Provider registry — selects concrete providers based on configuration.

Business logic asks the registry for a provider by role; it never instantiates
a vendor directly. Selection is DYNAMIC so switching to a live provider (e.g.
after a Kite login) takes effect without code changes:
  - market/portfolio -> Kite when DATA_PROVIDER=zerodha AND a Kite session exists,
    else the deterministic mock (clearly labelled).
  - fundamental/news -> Yahoo Finance (yfinance) when selected, else mock.
  - ai -> OpenAI when configured; Gemini as a configurable FALLBACK; else mock.
"""
from __future__ import annotations

from ..core.config import (DATA_PROVIDER, FUNDAMENTAL_PROVIDER, NEWS_PROVIDER,
                           AI_PROVIDER, AI_FALLBACK_PROVIDER, OPENAI_API_KEY,
                           GEMINI_API_KEY)
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
_mock_fundamental = MockFundamentalDataProvider()
_mock_news = MockNewsProvider()
_mock_portfolio = MockPortfolioProvider(_mock_market)
_knowledge = NullKnowledgeProvider()

_kite_market = None
_kite_portfolio = None
_yf_fundamental = None
_yf_news = None
_ai_singleton = None
_ai_fallbacks = None


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
    global _yf_fundamental
    if FUNDAMENTAL_PROVIDER == "yfinance":
        if _yf_fundamental is None:
            from .yfinance_provider import YFinanceFundamentalProvider
            _yf_fundamental = YFinanceFundamentalProvider()
        return _yf_fundamental
    return _mock_fundamental


def news_provider():
    global _yf_news
    if NEWS_PROVIDER == "yfinance":
        if _yf_news is None:
            from .yfinance_provider import YFinanceNewsProvider
            _yf_news = YFinanceNewsProvider()
        return _yf_news
    return _mock_news


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
    if AI_PROVIDER == "gemini" and GEMINI_API_KEY:
        try:
            from ..ai.gemini_provider import GeminiProvider
            _ai_singleton = GeminiProvider()
            return _ai_singleton
        except Exception as e:  # noqa: BLE001
            logger.warning("Gemini init failed, falling back to mock: %s", e)
    _ai_singleton = MockAIProvider()
    return _ai_singleton


def ai_fallback_providers() -> list:
    """Ordered fallback providers tried when the primary AI provider fails."""
    global _ai_fallbacks
    if _ai_fallbacks is not None:
        return _ai_fallbacks
    out = []
    if AI_FALLBACK_PROVIDER == "gemini" and GEMINI_API_KEY and getattr(
            ai_provider(), "name", "mock") != "gemini":
        try:
            from ..ai.gemini_provider import GeminiProvider
            out.append(GeminiProvider())
            logger.info("AI fallback provider: gemini (%s)", out[-1].model)
        except Exception as e:  # noqa: BLE001
            logger.warning("Gemini fallback init failed: %s", e)
    _ai_fallbacks = out
    return out


def knowledge_provider():
    return _knowledge


def data_source() -> str:
    return "zerodha" if _kite_enabled() else "mock"


def provider_modes() -> dict:
    ai = ai_provider()
    fb = ai_fallback_providers()
    fund = fundamental_provider()
    news = news_provider()
    return {
        "data": {"selected": DATA_PROVIDER, "mode": data_source(),
                 "live": _kite_enabled()},
        "fundamental": {"selected": FUNDAMENTAL_PROVIDER, "mode": fund.mode,
                        "live": fund.mode == "yfinance"},
        "news": {"selected": NEWS_PROVIDER, "mode": news.mode,
                 "live": news.mode == "yfinance"},
        "ai": {"selected": AI_PROVIDER, "mode": getattr(ai, "name", "mock"),
               "model": getattr(ai, "model", "mock"),
               "fallback": [getattr(p, "name", "?") for p in fb],
               "live": getattr(ai, "name", "mock") in ("openai", "gemini")},
        "knowledge": {"selected": "null", "mode": _knowledge.mode, "live": False},
    }
