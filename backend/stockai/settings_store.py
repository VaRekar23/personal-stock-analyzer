"""Runtime settings store — defaults merged with DB overrides (Settings page).

Only non-sensitive, tunable config lives here (risk assumptions, cache TTLs,
thresholds, provider/model selection). Secrets never pass through here.
"""
from __future__ import annotations
import copy
import json

from .core import db
from .core.config import DEFAULT_SETTINGS


async def get_settings() -> dict:
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    rows = await db.fetch("SELECT key, value FROM system.configuration")
    for row in rows:
        val = row["value"]
        if isinstance(val, str):
            val = json.loads(val)
        if row["key"] in merged and isinstance(merged[row["key"]], dict):
            merged[row["key"]].update(val)
        else:
            merged[row["key"]] = val
    return merged


async def update_settings(section: str, values: dict) -> dict:
    if not db.is_up():
        raise RuntimeError("Database unavailable — cannot persist settings")
    current = await get_settings()
    base = current.get(section, {})
    if isinstance(base, dict):
        base.update(values)
    else:
        base = values
    await db.execute(
        """INSERT INTO system.configuration (key,value,updated_at)
           VALUES ($1,$2,now())
           ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=now()""",
        section, json.dumps(base))
    return await get_settings()
