"""Zerodha / Kite Connect adapter — PENDING VERIFICATION.

Credentials (ZERODHA_API_KEY / API_SECRET / ACCESS_TOKEN) remain server-side
and are NOT configured in V1. This adapter implements the provider interface
shape but raises ProviderPendingError until credentials + exact API behaviour
are verified. Do not fabricate successful API responses.

When enabling live mode, verify against official Kite Connect docs:
https://kite.trade/docs/connect/v3/ and populate historical.py/portfolio.py/
quotes.py/mapper.py accordingly (see docs/API_INTEGRATIONS.md).
"""
from __future__ import annotations


class ProviderPendingError(RuntimeError):
    """Raised when a live provider is requested but not yet configured/verified."""


class ZerodhaMarketDataProvider:
    mode = "live"
    STATUS = "pending_verification"

    def __init__(self, *_, **__):
        pass

    async def _pending(self, *_, **__):
        raise ProviderPendingError(
            "Zerodha/Kite adapter pending verification — no credentials configured."
        )

    get_instruments = _pending
    get_candles = _pending
    get_quote = _pending
    get_holdings = _pending
    get_positions = _pending
