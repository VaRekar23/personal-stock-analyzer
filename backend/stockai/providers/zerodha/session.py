"""Kite (Zerodha) session store.

The daily access_token is exchanged server-side (login flow in api.py) and kept
in `system.configuration` (JSONB) + an in-memory cache. Kite tokens expire daily
(~06:00 IST), so a fresh login is required each trading day. Never exposed to the
frontend. `has_token()` is a cheap sync check used by the provider registry.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

from ...core import db
from ...core.logging_config import get_logger

logger = get_logger("stockai.kite.session")

_mem: dict = {"access_token": None, "login_time": None, "stored_at": None}


def has_token() -> bool:
    return bool(_mem.get("access_token"))


def get_access_token() -> str | None:
    return _mem.get("access_token")


def status() -> dict:
    return {"connected": has_token(),
            "login_time": _mem.get("login_time"),
            "stored_at": _mem.get("stored_at")}


async def load_from_db() -> None:
    if not db.is_up():
        return
    row = await db.fetchrow(
        "SELECT value FROM system.configuration WHERE key='kite_session'")
    if row and row["value"]:
        val = row["value"] if isinstance(row["value"], dict) else json.loads(row["value"])
        _mem.update(val)


async def persist(access_token: str, login_time: str | None) -> None:
    _mem["access_token"] = access_token
    _mem["login_time"] = login_time
    _mem["stored_at"] = datetime.now(timezone.utc).isoformat()
    if db.is_up():
        await db.execute(
            """INSERT INTO system.configuration (key, value)
               VALUES ('kite_session', $1)
               ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""",
            json.dumps(_mem))


async def clear() -> None:
    _mem.update({"access_token": None, "login_time": None, "stored_at": None})
    if db.is_up():
        await db.execute("DELETE FROM system.configuration WHERE key='kite_session'")
