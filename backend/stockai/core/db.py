"""PostgreSQL data layer (source of truth).

Uses asyncpg. The market-data tables are Timescale-ready (documented in
docs/DATABASE_SCHEMA.md); TimescaleDB hypertables are the target when the
extension is available in the environment. The app degrades gracefully:
if Postgres is unavailable the analysis pipeline falls back to deterministic
in-memory generation and Data Health reports the DB as DOWN.
"""
from __future__ import annotations
import asyncpg
from pathlib import Path
from .config import DATABASE_URL
from .logging_config import get_logger

logger = get_logger("stockai.db")
SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"

_pool: asyncpg.Pool | None = None


async def connect() -> None:
    global _pool
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set; running without Postgres")
        return
    try:
        _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=8,
                                          command_timeout=30)
        await init_schema()
        logger.info("PostgreSQL connected and schema initialised")
    except Exception as e:  # noqa: BLE001
        _pool = None
        logger.error("PostgreSQL unavailable: %s", e)


async def disconnect() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def is_up() -> bool:
    return _pool is not None


async def init_schema() -> None:
    if not _pool:
        return
    sql = SCHEMA_FILE.read_text()
    async with _pool.acquire() as conn:
        await conn.execute(sql)


async def execute(query: str, *args):
    if not _pool:
        return None
    async with _pool.acquire() as conn:
        return await conn.execute(query, *args)


async def fetch(query: str, *args) -> list[dict]:
    if not _pool:
        return []
    async with _pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(r) for r in rows]


async def fetchrow(query: str, *args) -> dict | None:
    if not _pool:
        return None
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(query, *args)
        return dict(row) if row else None


async def executemany(query: str, args_list: list[tuple]) -> None:
    if not _pool or not args_list:
        return
    async with _pool.acquire() as conn:
        await conn.executemany(query, args_list)


async def health() -> dict:
    if not _pool:
        return {"status": "down", "detail": "not connected"}
    try:
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "operational", "detail": "PostgreSQL 15"}
    except Exception as e:  # noqa: BLE001
        return {"status": "degraded", "detail": str(e)}
