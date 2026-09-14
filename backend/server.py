"""StockAI FastAPI entrypoint.

Wires the domain layer to HTTP. On startup it connects to PostgreSQL and Redis
(both degrade gracefully), initialises the schema, seeds NIFTY 50 instruments,
index membership and EVAL datasets. See docs/ARCHITECTURE.md.
"""
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path
import os
from datetime import date

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from stockai.core.logging_config import setup_logging, get_logger
from stockai.core import db, cache
from stockai.api import api_router
from stockai.analysis.orchestrator import get_orchestrator
from stockai.evals.datasets import seed_datasets
from stockai.data.nifty50 import NIFTY50

setup_logging()
logger = get_logger("stockai.server")

app = FastAPI(title="StockAI — Indian Stock Analysis Platform (V1)")


async def _seed_index_membership():
    if not db.is_up():
        return
    await db.execute(
        """INSERT INTO index_data.indexes (index_name, description)
           VALUES ('NIFTY 50','NSE NIFTY 50 index (seed)')
           ON CONFLICT (index_name) DO NOTHING""")
    for sym, _, _ in NIFTY50:
        await db.execute(
            """INSERT INTO index_data.index_memberships
               (index_name,symbol,valid_from,valid_to,source)
               VALUES ('NIFTY 50',$1,$2,NULL,'seed:nse_current')
               ON CONFLICT (index_name,symbol,valid_from) DO NOTHING""",
            sym, date(2024, 1, 1))


@app.on_event("startup")
async def startup():
    await db.connect()
    await cache.connect()
    from stockai.providers.zerodha import session as kite_session
    await kite_session.load_from_db()
    from stockai.analysis.orchestrator import reset_orchestrator
    reset_orchestrator()  # pick up live providers if a Kite session was restored
    orch = get_orchestrator()
    try:
        await orch.warehouse.sync_instruments()
        await _seed_index_membership()
        await seed_datasets()
        logger.info("Startup seeding complete")
    except Exception as e:  # noqa: BLE001
        logger.error("Startup seeding issue (non-fatal): %s", e)


@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()
    await cache.disconnect()


app.include_router(api_router)

# CORS — bulletproof default for this personal single-user app (no cookie auth).
# If CORS_ORIGINS is set to a valid http(s) origin list -> restrict to those.
# Otherwise (unset / "*" / garbled) -> allow ALL origins with a literal "*"
# (allow_credentials=False so "*" is CORS-spec-compliant and always works).
_cors_raw = os.environ.get("CORS_ORIGINS", "").strip()
_cors_list = [o.strip().rstrip("/") for o in _cors_raw.split(",") if o.strip().startswith("http")]
if _cors_list:
    _cors_kwargs = {"allow_origins": _cors_list, "allow_credentials": True}
else:
    _cors_kwargs = {"allow_origins": ["*"], "allow_credentials": False}
app.add_middleware(
    CORSMiddleware,
    allow_methods=["*"],
    allow_headers=["*"],
    **_cors_kwargs,
)
