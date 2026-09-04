"""Redis cache layer with graceful in-memory fallback.

PostgreSQL remains the source of truth. Cache failures must never destroy
application functionality — if Redis is down we transparently use a bounded
in-memory dict and Data Health reports Redis as DOWN.
"""
from __future__ import annotations
import json
import time
import redis.asyncio as aioredis
from .config import REDIS_URL
from .logging_config import get_logger

logger = get_logger("stockai.cache")

_client: aioredis.Redis | None = None
_mem: dict[str, tuple[float, str]] = {}  # key -> (expires_at, json)
_stats = {"hits": 0, "misses": 0}


async def connect() -> None:
    global _client
    if not REDIS_URL:
        return
    try:
        _client = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await _client.ping()
        logger.info("Redis connected")
    except Exception as e:  # noqa: BLE001
        _client = None
        logger.error("Redis unavailable, using in-memory cache: %s", e)


async def disconnect() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None


def is_up() -> bool:
    return _client is not None


def stats() -> dict:
    total = _stats["hits"] + _stats["misses"]
    rate = round(_stats["hits"] / total, 3) if total else 0.0
    return {**_stats, "hit_rate": rate, "backend": "redis" if _client else "memory"}


async def get_json(key: str):
    raw = None
    if _client:
        try:
            raw = await _client.get(key)
        except Exception:  # noqa: BLE001
            raw = None
    if raw is None:
        entry = _mem.get(key)
        if entry and entry[0] > time.time():
            raw = entry[1]
    if raw is None:
        _stats["misses"] += 1
        return None
    _stats["hits"] += 1
    return json.loads(raw)


async def set_json(key: str, value, ttl: int = 3600) -> None:
    raw = json.dumps(value, default=str)
    if _client:
        try:
            await _client.set(key, raw, ex=ttl)
            return
        except Exception:  # noqa: BLE001
            pass
    _mem[key] = (time.time() + ttl, raw)
    if len(_mem) > 5000:  # bound memory
        _mem.pop(next(iter(_mem)))


async def delete(pattern_prefix: str) -> int:
    n = 0
    if _client:
        try:
            async for k in _client.scan_iter(match=f"{pattern_prefix}*"):
                await _client.delete(k)
                n += 1
        except Exception:  # noqa: BLE001
            pass
    for k in [k for k in _mem if k.startswith(pattern_prefix)]:
        _mem.pop(k, None)
        n += 1
    return n


async def health() -> dict:
    if not _client:
        return {"status": "degraded", "detail": "in-memory fallback active"}
    try:
        await _client.ping()
        return {"status": "operational", "detail": "Redis 7"}
    except Exception as e:  # noqa: BLE001
        return {"status": "down", "detail": str(e)}
