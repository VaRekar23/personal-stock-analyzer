"""Unit tests for Zerodha instrument resolution (symbol -> instrument_token).

The Kite client internals are monkeypatched so these run without a live token.
They verify the resolution order (memory -> master -> targeted ltp fallback)
and that genuinely unknown symbols raise UnknownSymbolError (-> HTTP 404).
"""
import asyncio
import pytest

from stockai.providers.zerodha import instruments
from stockai.providers.base import UnknownSymbolError


@pytest.fixture(autouse=True)
def _reset_cache():
    instruments._mem.clear()
    instruments._mem_loaded_at = 0.0
    yield
    instruments._mem.clear()
    instruments._mem_loaded_at = 0.0


def test_resolve_case_insensitive_from_memory():
    instruments._mem["RELIANCE"] = 738561
    instruments._mem_loaded_at = float("inf")  # treat as fresh
    assert asyncio.run(instruments.resolve("reliance")) == 738561


def test_resolve_from_master(monkeypatch):
    async def fake_master(force=False):
        return {"LTIM": 2939649, "RELIANCE": 738561}
    monkeypatch.setattr(instruments, "load_master", fake_master)

    async def fake_ltp(sym):  # must NOT be called when master has the symbol
        raise AssertionError("ltp fallback should not run when master resolves")
    monkeypatch.setattr(instruments, "_ltp_token", fake_ltp)

    assert asyncio.run(instruments.resolve("LTIM")) == 2939649


def test_resolve_ltp_fallback_and_cache(monkeypatch):
    async def fake_master(force=False):
        return {"RELIANCE": 738561}  # LTIM missing from master
    monkeypatch.setattr(instruments, "load_master", fake_master)

    async def fake_ltp(sym):
        assert sym == "LTIM"
        return 2939649
    monkeypatch.setattr(instruments, "_ltp_token", fake_ltp)

    assert asyncio.run(instruments.resolve("LTIM")) == 2939649
    assert instruments._mem["LTIM"] == 2939649  # cached after fallback


def test_unknown_symbol_raises_404_error(monkeypatch):
    async def fake_master(force=False):
        return {"RELIANCE": 738561}
    monkeypatch.setattr(instruments, "load_master", fake_master)

    async def fake_ltp(sym):
        return None
    monkeypatch.setattr(instruments, "_ltp_token", fake_ltp)

    with pytest.raises(UnknownSymbolError) as ei:
        asyncio.run(instruments.resolve("NOTASTOCK"))
    assert ei.value.symbol == "NOTASTOCK"
    assert ei.value.reason == "not_found"


def test_empty_symbol_raises():
    with pytest.raises(UnknownSymbolError):
        asyncio.run(instruments.resolve(""))
