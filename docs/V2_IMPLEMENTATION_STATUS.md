# V2 Implementation Status

| Feature | Status | Location | Provider | Configuration | Tests | Known limitations |
|---|---|---|---|---|---|---|
| **PostgreSQL cache (Redis removed)** | ✅ COMPLETED | `core/cache.py`, `core/schema.sql` (`system.cache_entries`) | PostgreSQL 15 | none (uses `DATABASE_URL`) | `tests/test_cache.py` (set/get, TTL expiry, prefix delete, namespace) | 5-min opportunistic expiry sweep; in-memory fallback only if DB down |
| **Zerodha live market data** | ✅ COMPLETED | `providers/zerodha/live.py`, `instruments.py`, `session.py` | Zerodha Kite | `DATA_PROVIDER=zerodha` + `ZERODHA_API_KEY/SECRET` + daily login | `tests/test_instruments.py` | Daily interactive login (token expires ~06:00 IST); live path not unit-run without token |
| **Zerodha portfolio** | ✅ COMPLETED | `providers/zerodha/live.py` `KitePortfolioProvider` | Zerodha Kite | `DATA_PROVIDER=zerodha` | via API tests (mock) | needs live token |
| **Fundamentals** | ✅ COMPLETED | `providers/yfinance_provider.py` | Yahoo Finance (yfinance) | `FUNDAMENTAL_PROVIDER=yfinance` | `tests/test_api.py::test_fundamentals` | ROCE / FII-DII split not provided by Yahoo (NULL); best-effort source |
| **News** | ✅ COMPLETED | `providers/yfinance_provider.py` | Yahoo Finance (yfinance) | `NEWS_PROVIDER=yfinance` | `tests/test_api.py::test_news` | Yahoo relevance for NSE tickers is weak/transient; context only |
| **OpenAI AI** | ✅ COMPLETED | `ai/openai_provider.py`, `ai/service.py` | OpenAI | `AI_PROVIDER=openai`, `AI_MODEL`, `AI_TEMPERATURE`, `AI_MAX_TOKENS` + `OPENAI_API_KEY` | API/eval tests | needs OpenAI billing credits |
| **Gemini fallback** | ✅ COMPLETED | `ai/gemini_provider.py` | Google Gemini | `AI_FALLBACK_PROVIDER=gemini`, `GEMINI_MODEL` + `GEMINI_API_KEY` | API/eval tests | — |
| **EVALS** | ✅ COMPLETED | `evals/framework.py`, `evals/datasets.py` | vendor-independent | — | `tests/test_api.py::TestEvals` | strategy-eval (post-trade R) schema present, runner is V3 |
| **Historical ingestion (incremental/idempotent)** | ✅ COMPLETED | `data/warehouse.py` | provider-agnostic | — | engine tests | on-demand; Timescale hypertables pending env support |
| **TimescaleDB hypertables** | ⛔ BLOCKED | `core/schema.sql` | — | — | — | extension unavailable on this arch; schema is Timescale-ready |

## Required environment variables (V2)
`DATABASE_URL` (Postgres). Optional per provider: `DATA_PROVIDER`, `FUNDAMENTAL_PROVIDER`,
`NEWS_PROVIDER`, `AI_PROVIDER`, `AI_FALLBACK_PROVIDER`, `AI_MODEL`, `GEMINI_MODEL`,
`AI_TEMPERATURE`, `AI_MAX_TOKENS`, `OPENAI_API_KEY`, `GEMINI_API_KEY`,
`ZERODHA_API_KEY`, `ZERODHA_API_SECRET`. **`REDIS_URL` is no longer used.**

## Database migrations required
`system.cache_entries` table + indexes — auto-created on startup via `core/schema.sql`
(`CREATE TABLE IF NOT EXISTS`). No manual migration step.

## Tests executed
`pytest tests/` — engines (8), instruments (5), cache (4), API/EVALS (20). Cache + Redis-removal
acceptance verified (health reports `PostgreSQL Cache`, app starts with `REDIS_URL` absent and no
Redis service).

## Remaining V2 work / future
- Verify & integrate a licensed fundamental provider (TrueData/Stoxim) if Yahoo's terms are
  insufficient for the use case (abstraction already supports swap).
- TimescaleDB hypertables once the extension is available in the target environment.
- Strategy-evaluation runner (post-trade R) — schema exists; runner is V3.
