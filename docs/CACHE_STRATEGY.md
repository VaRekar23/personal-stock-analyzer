# Cache Strategy (V2 — PostgreSQL-backed)

**Redis has been removed.** The cache now lives in PostgreSQL (`system.cache_entries`),
so this single-user app needs no separate Redis service (lower Cloud cost). PostgreSQL
remains the single source of truth; the cache is a derived, TTL-bounded table.

## Backend
`CacheService` API (`core/cache.py`) is unchanged for callers:
`get_json(key)`, `set_json(key, value, ttl, **meta)`, `delete(prefix)`, `stats()`, `health()`,
`connect()`, `disconnect()`. Implementation = `PostgresCacheBackend` using UPSERT
(`ON CONFLICT (cache_key) DO UPDATE`), concurrency-safe. Expired rows are never returned
(filtered by `expires_at > now()`) and are swept opportunistically (≤ every 5 min) and on
`delete`. If Postgres itself is down, a small bounded in-memory dict is used so a cache
outage never breaks functionality (Data Health then shows DEGRADED).

## Table
`system.cache_entries(cache_key PK, namespace, value_json JSONB, created_at, expires_at,
provider, model, strategy_version, prompt_version, market_data_version, metadata_json)`
with indexes on `expires_at` and `namespace`. `namespace` is derived from the key prefix.

## Categories (key prefixes → namespace)
`market:` · `analysis:` · `scanner:` · `ai:` · `fund:` (fundamentals) · news. Keys are
**version-aware**; the AI cache key includes symbol, analysis_type, market_data_version,
strategy_version, prompt_version, provider, model — never symbol alone.

## TTLs (configurable in `settings`/`core/config.py` `DEFAULT_SETTINGS["cache"]`)
| Category | TTL | Why |
|---|---|---|
| analysis | ~15 min | re-use within a trading session; cheap to recompute deterministically |
| scanner | ~15 min | 50-stock scan is expensive (AI finalists); session-stable |
| market-data | short | freshness matters; warehouse is the durable store |
| fundamentals | ~6 h | fundamentals change slowly; avoids hammering Yahoo |
| news | ~30 min | context refreshes periodically |
| AI | ~24 h | identical grounded input ⇒ identical explanation; key is version-aware; biggest cost saver |

## Acceptance (zero-Redis)
App starts with `REDIS_URL` absent and no Redis service; Data Health reports cache as
**PostgreSQL Cache** (`backend: postgresql`); no endpoint fails because Redis is unavailable.

## V3 additions
- **Research answers**: key `research:<sha>` over query + retrieved chunk ids + prompt_version + provider + model
  (TTL = `ai_ttl_seconds`). New, changed or deleted documents change the retrieved chunk ids, which changes the key, so stale answers are never served.
  Fallback/no-evidence responses are not cached.
- **Backtests** are not stored in the TTL cache. Completed runs are permanent rows in `backtest.runs`, reused when the
  full identity (request, assumptions, strategy/indicator/scoring/risk/backtest versions, risk-config and weights hashes,
  per-symbol data versions) matches exactly. Any change produces a new run.
