# Cache Strategy

Redis is the performance layer; **PostgreSQL/TimescaleDB is the source of truth**.
Cache failures never break functionality.

## Backend (`core/cache.py`)
- Redis (`REDIS_URL`) with a bounded **in-memory fallback** dict if Redis is unavailable.
- `get_json / set_json(ttl) / delete(prefix)`; tracks hits/misses → `stats()` (hit rate +
  backend) shown on Data Health.
- On Redis error mid-request, falls back silently; Data Health shows Redis DEGRADED/DOWN.

## What is cached & keys
| Data | Key | Default TTL |
|---|---|---|
| Single-stock analysis | `analysis:<mode>:<symbol>` | `analysis_ttl_seconds` = 3600 |
| Scanner result | `scanner:<mode>:<count>` | `scanner_ttl_seconds` = 1800 |
| AI explanation | `ai:<type>:<symbol>:<hash>` (see AI_ARCHITECTURE.md) | `ai_ttl_seconds` = 86400 |
| (Market-data response) | reserved | `market_data_ttl_seconds` = 300 |

AI results are also persisted to `analysis.ai_analyses` so they survive cache flushes.

## Invalidation
- TTL-based expiry (all keys).
- On Settings change, `analysis:` and `scanner:` prefixes are cleared so new config takes effect.
- AI cache keys embed `market_data_version`, strategy/prompt/provider/model versions, so
  they self-invalidate when the effective input changes (no manual purge needed).

## Read-through pattern
`analysis` and `scan` check cache first; on miss they compute and populate. A cached
single-stock analysis that lacks AI (produced by a `run_ai=False` scan pass) is
transparently recomputed when AI is requested.

## Cost implications
Caching + deterministic-first shortlisting are the primary AI-cost controls (see
COST_CONTROL section of the spec and AI_ARCHITECTURE.md).
