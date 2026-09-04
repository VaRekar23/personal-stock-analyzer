# Data Pipelines

```
source (provider) → ingestion (warehouse) → storage (PostgreSQL)
→ features (indicators) → context (market/sector) → strategy → scoring
→ risk → AI explanation → cache (Redis + ai_analyses) → API → UI
```

## Ingestion (market data)
File: `stockai/data/warehouse.py`.
- **Fetch once, store, reuse.** `get_candles(symbol, interval, count)`:
  1. If Postgres up: check stored count + latest ts for `(symbol, interval)`.
  2. Determine staleness (>1 day for daily, >30 min for intraday) or insufficient rows.
  3. If needed, `_ingest()` fetches from the provider and upserts
     `INSERT ... ON CONFLICT (symbol,ts) DO NOTHING` (**idempotent**; running twice
     creates no duplicates). A row is written to `system.job_runs`.
  4. Read back latest `count` candles ordered by time.
- **Fallback:** if Postgres is down, candles are generated deterministically in-memory
  (still reproducible) and Data Health reports DB DOWN.
- **Incremental:** only missing/stale intervals are re-fetched; entire ranges are not
  re-downloaded per analysis.
- **Instruments** are synced at startup (`sync_instruments`, upsert on `symbol`).

### Backfill vs incremental
- *Initial backfill*: first `get_candles` for a symbol/interval fetches the full desired
  window and stores it.
- *Incremental update*: subsequent calls only refresh when stale; otherwise served from DB.
- The live Zerodha adapter must additionally respect provider historical-range caps per
  interval (documented in API_INTEGRATIONS.md) and resume after failure.

## Feature pipeline
- `indicators/engine.compute_features(symbol, candles, timeframe)` → structured features
  (`technical_v1`). Pure function; no I/O.
- Market/sector context computed from warehouse candles (indices proxied in mock:
  RELIANCE→NIFTY, HDFCBANK→BANKNIFTY; sector direction from peer constituents).

## Strategy → scoring → risk
- Mode selects strategy (`long_term`/`swing`/`intraday`); each returns a `ScoreResult`.
- Risk Engine builds a hypothetical setup for swing/intraday (ATR + structure + config).

## AI + cache
- `AIService.explain` builds a cache key from symbol, type, date, market_data_version,
  strategy_version, prompt_version, provider, model. Checks Redis → `ai_analyses` → calls
  provider → validates schema → writes both caches.
- Analysis results are cached in Redis (`analysis:<mode>:<symbol>`) and persisted to
  `analysis.analysis_runs` with full version provenance.

## Scanner pipeline (cost-controlled)
```
50 symbols → analyze_stock(run_ai=False) [deterministic] → rank by score
→ top-N finalists above threshold → analyze_stock(run_ai=True) [AI only here]
→ cache scanner result (scanner:<mode>:<n>)
```

## Market-data version
`Warehouse.market_data_version(candles)` = short hash of last ts + last close + length.
Used in AI cache keys so results invalidate when underlying data materially changes.
