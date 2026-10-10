"""Backtest service: stored-data loading, data preparation, run identity,
PostgreSQL job records and bounded background execution (no queue/Redis).
"""
from __future__ import annotations
import asyncio
import csv
import hashlib
import io
import json
import uuid
from datetime import date, datetime, time, timedelta, timezone

from ..core import db
from ..core import versions as V
from ..core.config import load_weights
from ..core.logging_config import get_logger
from ..data.warehouse import _TABLE
from ..providers import registry
from ..settings_store import get_settings
from . import engine as E
from .metrics import compute_metrics
from .quality import assess

logger = get_logger("stockai.backtest")
IST = timezone(timedelta(hours=5, minutes=30))
CTX_SYMBOL = "RELIANCE"  # same NIFTY proxy the live MarketContextEngine uses
KITE_CHUNK_DAYS = {"1d": 2000, "15m": 200, "5m": 100}
MAX_RANGE_DAYS = {"1d": 3650, "15m": 365, "5m": 180}
MAX_SYMBOLS = 10
STALE_MINUTES = 10
_TASKS: dict[str, asyncio.Task] = {}


class BacktestError(ValueError):
    pass


def _j(v):
    return json.loads(v) if isinstance(v, str) else v


def validate_request(req: dict) -> dict:
    mode, interval = req.get("mode"), req.get("interval")
    if mode not in E.MODE_INTERVALS:
        raise BacktestError("mode must be 'swing' or 'intraday' (long-term backtests are deferred: "
                            "no point-in-time fundamentals available).")
    if interval not in E.MODE_INTERVALS[mode]:
        raise BacktestError(f"interval for {mode} must be one of {E.MODE_INTERVALS[mode]}")
    if req.get("universe"):
        raise BacktestError("Index-wide backtests are disabled: point-in-time index membership is "
                            "not verified. Use single symbols or your own symbol list.")
    syms = sorted({s.strip().upper() for s in req.get("symbols") or [] if s and s.strip()})
    if not syms or len(syms) > MAX_SYMBOLS:
        raise BacktestError(f"Provide 1..{MAX_SYMBOLS} symbols.")
    start, end = date.fromisoformat(str(req["start"])), date.fromisoformat(str(req["end"]))
    if start >= end:
        raise BacktestError("start must be before end")
    if end > datetime.now(IST).date():
        raise BacktestError("end cannot be in the future")
    if (end - start).days > MAX_RANGE_DAYS[interval]:
        raise BacktestError(f"Range too long for {interval} (max {MAX_RANGE_DAYS[interval]} days).")
    cap = float(req.get("capital") or 1_000_000)
    risk_pct = float(req.get("risk_per_trade_pct") or 1.0)
    slip = float(req.get("slippage_bps") or 0)
    cost = float(req.get("cost_bps_per_side") or 0)
    if cap <= 0 or not (0 < risk_pct <= 5) or not (0 <= slip <= 100) or not (0 <= cost <= 100):
        raise BacktestError("capital>0, 0<risk%<=5, 0<=slippage/cost bps<=100")
    return {"mode": mode, "interval": interval, "symbols": syms, "start": start.isoformat(),
            "end": end.isoformat(), "capital": cap, "risk_per_trade_pct": risk_pct,
            "slippage_bps": slip, "cost_bps_per_side": cost}


def _bounds(start: str, end: str):
    s = datetime.combine(date.fromisoformat(start), time(0, 0), IST)
    e = datetime.combine(date.fromisoformat(end), time(23, 59, 59), IST)
    return s, e


def _row(r):
    return {"ts": r["ts"].astimezone(IST).isoformat(), "open": float(r["open"]),
            "high": float(r["high"]), "low": float(r["low"]), "close": float(r["close"]),
            "volume": int(r["volume"]), "source": r["source"]}


async def pick_source(symbol, interval, start, end) -> str:
    """Real Zerodha candles if any are stored for the range, else mock. Never mixed.
    Independent of today's Kite token — backtests use stored data only."""
    s, e = _bounds(start, end)
    row = await db.fetchrow(f"SELECT count(*) AS n FROM {_TABLE[interval]} WHERE symbol=$1 "
                            f"AND source='zerodha' AND ts >= $2 AND ts <= $3", symbol, s, e)
    return "zerodha" if row and row["n"] else "mock"


async def load_stored(symbol, interval, start, end) -> list[dict]:
    """Stored candles only (single source): WINDOW bars before start (warm-up) + the range."""
    table = _TABLE[interval]
    s, e = _bounds(start, end)
    src = await pick_source(symbol, interval, start, end)
    pre = await db.fetch(f"SELECT ts,open,high,low,close,volume,source FROM {table} "
                         f"WHERE symbol=$1 AND source=$4 AND ts < $2 ORDER BY ts DESC LIMIT $3",
                         symbol, s, E.WINDOW[interval], src)
    rng = await db.fetch(f"SELECT ts,open,high,low,close,volume,source FROM {table} "
                         f"WHERE symbol=$1 AND source=$4 AND ts >= $2 AND ts <= $3 ORDER BY ts",
                         symbol, s, e, src)
    return [_row(r) for r in reversed(pre)] + [_row(r) for r in rng]


def data_version(candles) -> str:
    raw = f"{len(candles)}|{candles[0]['ts'] if candles else ''}|{candles[-1]['ts'] if candles else ''}|" \
          f"{round(sum(c['close'] for c in candles), 4)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def coverage(req: dict) -> dict:
    r = validate_request(req)
    out = []
    for sym in r["symbols"]:
        c = await load_stored(sym, r["interval"], r["start"], r["end"])
        out.append(assess(sym, c, r["interval"], date.fromisoformat(r["start"]),
                          date.fromisoformat(r["end"]), E.WARMUP[r["interval"]]))
    return {"request": r, "coverage": out, "data_source": registry.data_source(),
            "warnings": [w for c in out for w in c["warnings"]]}


async def prepare(req: dict) -> dict:
    """Fetch ONLY missing leading/trailing ranges from the market provider, chunked."""
    r = validate_request(req)
    market = registry.market_provider()
    if registry.data_source() != "zerodha":
        raise BacktestError("Market data provider is in MOCK mode. Connect Zerodha "
                            "(Settings → Broker Connection) to fetch real history.")
    interval, table = r["interval"], _TABLE[r["interval"]]
    want_s, want_e = _bounds(r["start"], r["end"])
    want_s -= timedelta(days=E.WINDOW[interval] * (1.6 if interval == "1d" else 0.06) + 5)
    report = []
    for sym in r["symbols"]:
        row = await db.fetchrow(f"SELECT min(ts) lo, max(ts) hi FROM {table} WHERE symbol=$1 "
                                f"AND source='zerodha' AND ts >= $2 AND ts <= $3", sym, want_s, want_e)
        lo, hi = (row or {}).get("lo"), (row or {}).get("hi")
        ranges = [(want_s, want_e)] if not lo else \
            [x for x in ((want_s, lo - timedelta(minutes=1)), (hi + timedelta(minutes=1), want_e)) if x[0] < x[1]]
        fetched, errors = 0, []
        for a, b in ranges:
            cur = a
            while cur < b:
                nxt = min(b, cur + timedelta(days=KITE_CHUNK_DAYS[interval]))
                try:
                    candles = await market.get_candles(sym, interval, cur, nxt)
                    rows = [(sym, datetime.fromisoformat(c["ts"]), c["open"], c["high"], c["low"],
                             c["close"], c["volume"], c.get("open_interest", 0), c.get("source", "zerodha"))
                            for c in candles]
                    await db.executemany(
                        f"""INSERT INTO {table} (symbol,ts,open,high,low,close,volume,open_interest,source)
                            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9) ON CONFLICT (symbol,ts) DO NOTHING""", rows)
                    fetched += len(rows)
                except Exception as e:  # noqa: BLE001 — report, never fabricate
                    errors.append(f"{cur.date()}..{nxt.date()}: {type(e).__name__}: {str(e)[:120]}")
                await asyncio.sleep(0.35)  # Kite historical API: ~3 req/s
                cur = nxt
        report.append({"symbol": sym, "ranges_requested": len(ranges), "candles_fetched": fetched,
                       "errors": errors, "note": "interior gaps are not back-filled; see coverage"})
    return {"prepared": report}


def _identity(r: dict, assumptions: dict, versions: dict, dvs: dict) -> str:
    raw = json.dumps({"r": r, "a": assumptions, "v": versions, "d": dvs}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _versions(mode):
    return {"backtest": V.BACKTEST_VERSION, "strategy": V.STRATEGY_VERSIONS[mode],
            "indicator": V.INDICATOR_VERSION, "scoring": V.SCORING_VERSION, "risk": V.RISK_VERSION}


async def _mark_stale():
    await db.execute(
        "UPDATE backtest.runs SET status='failed', error='Interrupted (worker restarted or timed out)', "
        "finished_at=now() WHERE status IN ('queued','running') AND "
        f"coalesce(heartbeat_at, created_at) < now() - interval '{STALE_MINUTES} minutes'")


async def create_run(req: dict) -> dict:
    if not db.is_up():
        raise BacktestError("Database unavailable — backtests require PostgreSQL.")
    await _mark_stale()
    r = validate_request(req)
    settings = await get_settings()
    assumptions = {**E.DEFAULT_ASSUMPTIONS, "slippage_bps": r["slippage_bps"],
                   "cost_bps_per_side": r["cost_bps_per_side"]}
    dvs = {}
    for sym in r["symbols"] + [CTX_SYMBOL]:
        iv = "1d" if sym == CTX_SYMBOL and sym not in r["symbols"] else r["interval"]
        dvs[f"{sym}:{iv}"] = data_version(await load_stored(sym, iv, r["start"], r["end"]))
    versions = _versions(r["mode"])
    risk_cfg = {**settings["risk"], "account_capital": r["capital"],
                "risk_per_trade_pct": r["risk_per_trade_pct"]}
    versions["risk_config"] = hashlib.sha256(json.dumps(risk_cfg, sort_keys=True).encode()).hexdigest()[:12]
    versions["weights"] = hashlib.sha256(json.dumps(load_weights(), sort_keys=True).encode()).hexdigest()[:12]
    ident = _identity(r, assumptions, versions, dvs)
    existing = await db.fetchrow(
        "SELECT id,status FROM backtest.runs WHERE identity=$1 AND status IN ('queued','running','completed') "
        "ORDER BY created_at DESC LIMIT 1", ident)
    if existing:
        return {"id": str(existing["id"]), "status": existing["status"], "reused": True}
    run_id = uuid.uuid4()
    await db.execute(
        """INSERT INTO backtest.runs (id,identity,status,mode,interval,symbols,start_date,end_date,
           request,versions,assumptions,data_versions,heartbeat_at)
           VALUES ($1,$2,'queued',$3,$4,$5,$6,$7,$8,$9,$10,$11,now())""",
        run_id, ident, r["mode"], r["interval"], r["symbols"], date.fromisoformat(r["start"]),
        date.fromisoformat(r["end"]), json.dumps(r), json.dumps(versions), json.dumps(assumptions),
        json.dumps(dvs))
    task = asyncio.create_task(_execute(run_id, r, assumptions, risk_cfg))
    _TASKS[str(run_id)] = task
    task.add_done_callback(lambda _t, k=str(run_id): _TASKS.pop(k, None))
    return {"id": str(run_id), "status": "queued", "reused": False}


async def _execute(run_id, r, assumptions, risk_cfg):
    try:
        await db.execute("UPDATE backtest.runs SET status='running', started_at=now(), heartbeat_at=now() "
                         "WHERE id=$1", run_id)
        weights = load_weights()
        ctx = await load_stored(CTX_SYMBOL, "1d", r["start"], r["end"])
        bench = await load_stored(CTX_SYMBOL, r["interval"], r["start"], r["end"])
        trades, opens, skipped, cov, warns = [], [], [], [], []
        no_setup = decisions = 0
        start_ts = f"{r['start']}T00:00:00"
        for sym in r["symbols"]:
            candles = await load_stored(sym, r["interval"], r["start"], r["end"])
            q = assess(sym, candles, r["interval"], date.fromisoformat(r["start"]),
                       date.fromisoformat(r["end"]), E.WARMUP[r["interval"]])
            cov.append(q)
            warns += q["warnings"]
            if not candles:
                continue
            res = await asyncio.to_thread(
                E.replay_symbol, sym, candles, mode=r["mode"], interval=r["interval"],
                risk_cfg=risk_cfg, weights=weights, assumptions=assumptions, capital=r["capital"],
                start_ts=start_ts, ctx_candles=ctx, bench_candles=bench if sym != CTX_SYMBOL else None)
            trades += res["trades"]
            opens += res["open_trades"]
            skipped += res["skipped"]
            no_setup += res["no_setup"]
            decisions += res["decisions"]
            warns += res["warnings"]
            await db.execute("UPDATE backtest.runs SET heartbeat_at=now() WHERE id=$1", run_id)
        if not ctx:
            warns.append(f"Market-context proxy ({CTX_SYMBOL} 1d) has no stored data: market factor excluded.")
        if r["slippage_bps"] == 0 and r["cost_bps_per_side"] == 0:
            warns.append("Zero costs and zero slippage assumed: results are GROSS, not net tradable performance.")
        trades.sort(key=lambda t: t["exit_ts"])
        metrics, curve = compute_metrics(trades, opens, skipped, r["capital"], no_setup, decisions)
        warns += metrics["sample_warnings"]
        synthetic = any(c.get("synthetic") for c in cov)
        await db.executemany(
            """INSERT INTO backtest.trades (run_id,seq,symbol,direction,exit_reason,entry_ts,exit_ts,
               net_pnl,r_net,detail) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            [(run_id, k, t["symbol"], t["direction"], t["exit_reason"],
              datetime.fromisoformat(t["entry_ts"]), datetime.fromisoformat(t["exit_ts"]),
              t["net_pnl"], t["r_net"], json.dumps(t)) for k, t in enumerate(trades)])
        await db.execute(
            """UPDATE backtest.runs SET status='completed', finished_at=now(), heartbeat_at=now(),
               coverage=$2, metrics=$3, equity_curve=$4, skipped=$5, open_trades=$6, warnings=$7,
               synthetic_data=$8 WHERE id=$1""",
            run_id, json.dumps(cov), json.dumps(metrics), json.dumps(curve), json.dumps(skipped[:2000]),
            json.dumps(opens), json.dumps(list(dict.fromkeys(warns))), synthetic)
    except Exception as e:  # noqa: BLE001 — record failure on the run
        logger.exception("backtest %s failed", run_id)
        await db.execute("UPDATE backtest.runs SET status='failed', finished_at=now(), error=$2 WHERE id=$1",
                         run_id, f"{type(e).__name__}: {str(e)[:300]}")


_LIST_COLS = ("id,status,mode,interval,symbols,start_date,end_date,created_at,finished_at,"
              "synthetic_data,error,metrics")


def _ser(r: dict) -> dict:
    out = {}
    for k, v in r.items():
        if isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        elif isinstance(v, uuid.UUID):
            out[k] = str(v)
        elif k in ("request", "versions", "assumptions", "data_versions", "coverage", "metrics",
                   "equity_curve", "skipped", "open_trades", "warnings", "detail"):
            out[k] = _j(v)
        else:
            out[k] = v
    return out


async def list_runs(limit=50):
    await _mark_stale()
    rows = await db.fetch(f"SELECT {_LIST_COLS} FROM backtest.runs ORDER BY created_at DESC LIMIT $1", limit)
    out = []
    for r in rows:
        s = _ser(r)
        m = s.pop("metrics") or {}
        s["summary"] = {k: m.get(k) for k in ("total_trades", "win_rate", "expectancy_r", "net_pnl")}
        out.append(s)
    return out


async def get_run(run_id: str):
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        return None
    row = await db.fetchrow("SELECT * FROM backtest.runs WHERE id=$1", rid)
    if not row:
        return None
    run = _ser(row)
    run.pop("identity", None)
    trades = await db.fetch("SELECT detail FROM backtest.trades WHERE run_id=$1 ORDER BY seq", rid)
    run["trades"] = [_j(t["detail"]) for t in trades]
    return run


async def import_memberships(data: bytes, source: str, verified: bool) -> dict:
    """CSV: index_name,symbol,valid_from,valid_to. Source is mandatory provenance."""
    if not source.strip():
        raise BacktestError("source is required (e.g. official NSE Indices document reference).")
    rows, bad = [], 0
    for rec in csv.DictReader(io.StringIO(data.decode("utf-8", errors="replace"))):
        try:
            rows.append((rec["index_name"].strip(), rec["symbol"].strip().upper(),
                         date.fromisoformat(rec["valid_from"].strip()),
                         date.fromisoformat(rec["valid_to"].strip()) if (rec.get("valid_to") or "").strip() else None,
                         source.strip(), "verified" if verified else "unverified"))
        except (KeyError, ValueError):
            bad += 1
    await db.executemany(
        """INSERT INTO index_data.index_memberships
           (index_name,symbol,valid_from,valid_to,source,verification_status,retrieved_at)
           VALUES ($1,$2,$3,$4,$5,$6,now())
           ON CONFLICT (index_name,symbol,valid_from) DO UPDATE SET valid_to=EXCLUDED.valid_to,
           source=EXCLUDED.source, verification_status=EXCLUDED.verification_status, retrieved_at=now()""",
        rows)
    return {"imported": len(rows), "rejected_rows": bad,
            "verification_status": "verified" if verified else "unverified"}
