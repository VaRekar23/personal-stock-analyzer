"""PostgreSQL-backed cache (V2 — Redis removed).

Single-source-of-truth design: the cache lives in Postgres (`system.cache_entries`),
so this single-user app needs no separate Redis service. The public API is kept
identical to the former Redis layer so the rest of the app is unchanged:
    connect() / disconnect() / is_up() / stats()
    get_json(key) / set_json(key, value, ttl) / delete(prefix) / health()

Namespace is derived from the key prefix (e.g. "analysis:RELIANCE" -> "analysis")
to support the required cache categories (market/analysis/scanner/ai/fundamentals/news).
Expired rows are never returned and are cleaned opportunistically + on demand.
A small bounded in-memory fallback is used ONLY if Postgres itself is down, so a
cache outage never breaks functionality (Data Health then shows DEGRADED).
"""
from __future__ import annotations
import json
import time
from datetime import datetime, timedelta, timezone

from . import db
from .logging_config import get_logger

logger = get_logger("stockai.cache")

_stats = {"hits": 0, "misses": 0}
_mem: dict[str, tuple[float, str]] = {}  # key -> (expires_at_epoch, json) — DB-down fallback
_last_cleanup = 0.0


def _ns(key: str) -> str:
    return key.split(":", 1)[0] if ":" in key else "default"


async def connect() -> None:
    """No dedicated connection — reuses the shared Postgres pool (db.connect())."""
    if db.is_up():
        logger.info("Cache backend: PostgreSQL (system.cache_entries)")
    else:
        logger.warning("Cache: Postgres pool not up at connect; in-memory fallback until it is")


async def disconnect() -> None:
    _mem.clear()


def is_up() -> bool:
    return db.is_up()


def stats() -> dict:
    total = _stats["hits"] + _stats["misses"]
    rate = round(_stats["hits"] / total, 3) if total else 0.0
    return {**_stats, "hit_rate": rate,
            "backend": "postgresql" if db.is_up() else "memory"}


async def _cleanup_if_due() -> None:
    global _last_cleanup
    now = time.time()
    if now - _last_cleanup < 300:  # at most every 5 min
        return
    _last_cleanup = now
    try:
        await db.execute("DELETE FROM system.cache_entries WHERE expires_at < now()")
    except Exception:  # noqa: BLE001
        pass


async def get_json(key: str):
    if db.is_up():
        try:
            row = await db.fetchrow(
                "SELECT value_json FROM system.cache_entries "
                "WHERE cache_key=$1 AND expires_at > now()", key)
            if row is not None:
                _stats["hits"] += 1
                v = row["value_json"]
                return v if isinstance(v, (dict, list)) else json.loads(v)
            _stats["misses"] += 1
            return None
        except Exception as e:  # noqa: BLE001 — degrade to memory, never raise
            logger.warning("cache get failed (%s); using memory", e)
    entry = _mem.get(key)
    if entry and entry[0] > time.time():
        _stats["hits"] += 1
        return json.loads(entry[1])
    _stats["misses"] += 1
    return None


async def set_json(key: str, value, ttl: int = 3600, **meta) -> None:
    raw = json.dumps(value, default=str)
    if db.is_up():
        try:
            expires = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            await db.execute(
                """INSERT INTO system.cache_entries
                   (cache_key, namespace, value_json, created_at, expires_at,
                    provider, model, strategy_version, prompt_version,
                    market_data_version, metadata_json)
                   VALUES ($1,$2,$3,now(),$4,$5,$6,$7,$8,$9,$10)
                   ON CONFLICT (cache_key) DO UPDATE SET
                     value_json=EXCLUDED.value_json, created_at=now(),
                     expires_at=EXCLUDED.expires_at, namespace=EXCLUDED.namespace,
                     provider=EXCLUDED.provider, model=EXCLUDED.model,
                     strategy_version=EXCLUDED.strategy_version,
                     prompt_version=EXCLUDED.prompt_version,
                     market_data_version=EXCLUDED.market_data_version,
                     metadata_json=EXCLUDED.metadata_json""",
                key, _ns(key), raw, expires,
                meta.get("provider"), meta.get("model"),
                meta.get("strategy_version"), meta.get("prompt_version"),
                meta.get("market_data_version"),
                json.dumps(meta.get("metadata")) if meta.get("metadata") else None)
            await _cleanup_if_due()
            return
        except Exception as e:  # noqa: BLE001
            logger.warning("cache set failed (%s); using memory", e)
    _mem[key] = (time.time() + ttl, raw)
    if len(_mem) > 5000:
        _mem.pop(next(iter(_mem)))


async def delete(pattern_prefix: str) -> int:
    n = 0
    if db.is_up():
        try:
            res = await db.execute(
                "DELETE FROM system.cache_entries WHERE cache_key LIKE $1",
                f"{pattern_prefix}%")
            # asyncpg returns e.g. "DELETE 4"
            if isinstance(res, str) and res.startswith("DELETE"):
                n += int(res.split()[-1])
        except Exception as e:  # noqa: BLE001
            logger.warning("cache delete failed: %s", e)
    for k in [k for k in _mem if k.startswith(pattern_prefix)]:
        _mem.pop(k, None)
        n += 1
    return n


async def health() -> dict:
    if not db.is_up():
        return {"status": "degraded", "detail": "PostgreSQL cache unavailable; in-memory fallback active",
                "backend": "memory"}
    try:
        row = await db.fetchrow(
            "SELECT count(*) AS n FROM system.cache_entries WHERE expires_at > now()")
        live = row["n"] if row else 0
        return {"status": "operational", "detail": "PostgreSQL Cache",
                "backend": "postgresql", "live_entries": live}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "detail": str(e), "backend": "postgresql"}
