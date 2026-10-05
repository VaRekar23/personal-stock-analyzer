"""Tests for the PostgreSQL-backed cache (V2 — Redis removed).

Each test connects inside its own event loop (pytest-xdist runs a fresh loop per
asyncio.run, and an asyncpg pool is bound to the loop that created it).
"""
import asyncio
from pathlib import Path
import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
from stockai.core import db, cache  # noqa: E402


async def _with_db(coro_fn):
    await db.disconnect()
    await db.connect()
    if not db.is_up():
        return "SKIP"
    await cache.connect()
    try:
        return await coro_fn()
    finally:
        await db.disconnect()


def _run(coro_fn):
    r = asyncio.run(_with_db(coro_fn))
    if r == "SKIP":
        pytest.skip("PostgreSQL not available")
    return r


def test_set_get_roundtrip():
    async def go():
        await cache.set_json("analysis:TESTSYM:x", {"a": 1, "b": [2, 3]}, ttl=60)
        return await cache.get_json("analysis:TESTSYM:x")
    assert _run(go) == {"a": 1, "b": [2, 3]}


def test_namespace_and_backend():
    assert cache._ns("scanner:swing:50") == "scanner"
    assert cache._ns("nokey") == "default"


def test_ttl_expiry():
    async def go():
        await cache.set_json("ai:EXPIRE:1", {"x": 1}, ttl=1)
        await asyncio.sleep(1.3)
        return await cache.get_json("ai:EXPIRE:1")
    assert _run(go) is None


def test_prefix_delete():
    async def go():
        await cache.set_json("market:DEL:1", {"n": 1}, ttl=60)
        await cache.set_json("market:DEL:2", {"n": 2}, ttl=60)
        removed = await cache.delete("market:DEL:")
        return removed, await cache.get_json("market:DEL:1")
    removed, after = _run(go)
    assert removed >= 2 and after is None
