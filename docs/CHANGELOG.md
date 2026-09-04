# Changelog

All notable architectural changes. Keep in sync with implementation & version bumps.

## [1.2.0] — 2026-09-04 — Gemini fallback AI + Yahoo Finance fundamentals/news
### Added
- **GeminiProvider** (`ai/gemini_provider.py`) via `google-genai` async client, behind the
  same `AIProvider` interface — used as a configurable **fallback** (`AI_FALLBACK_PROVIDER=gemini`)
  when the primary (OpenAI) provider fails. JSON output mode; deterministic bias/confidence
  override preserved (AI never changes numbers). Model configurable via `GEMINI_MODEL`
  (default `gemini-3.1-flash-lite`).
- **AIService provider chain**: tries primary → fallbacks → graceful deterministic fallback.
  The actual answering provider/model is recorded in the analysis + AI cache.
- **YFinanceFundamentalProvider** + **YFinanceNewsProvider** (`providers/yfinance_provider.py`)
  replace the pending TrueData integration. NSE symbols mapped to `.NS`; blocking calls run in a
  threadpool with a timeout and are Redis-cached (fundamentals 6h, news 30m). Missing fields are
  returned as null ("data unavailable"), never fabricated. `roce` and FII/DII split are not
  provided by Yahoo → explicitly null.
- **Scanner**: long-term scan concurrently prefetches fundamentals (semaphore=8) so 50 live
  Yahoo calls don't dominate wall-time; results cached.
- **Registry**: dynamic fundamental/news = yfinance when selected; AI primary + fallback wiring;
  `provider_modes()` now reports fallback chain and per-role live status.
### Notes
- OpenAI account currently has no credits, so the **Gemini fallback is actively serving** live
  AI explanations (verified: `ai.provider=gemini`).
- Yahoo Finance `get_news` relevance for NSE tickers is weak (often returns unrelated market
  headlines). Real data, but symbol relevance is not guaranteed — documented limitation.
- Yahoo is a best-effort public source, not a contractual feed; values are labelled
  `source=yfinance` with a retrieval timestamp.

## [1.1.0] — 2026-09-04 — Live providers (OpenAI + Zerodha Kite)
### Added
- **OpenAIProvider** (`ai/openai_provider.py`) behind the existing `AIProvider` interface —
  BYOK (`OPENAI_API_KEY`), model via `AI_MODEL`, `json_object` structured output, deterministic
  bias/confidence override (deterministic values stay authoritative), full error mapping
  (auth/rate-limit/timeout/bad-request), `max_retries=0` fail-fast.
- **Zerodha Kite live adapter** (`providers/zerodha/live.py`): `KiteMarketDataProvider`
  (instruments→token map, historical OHLCV, quote) + `KitePortfolioProvider`
  (holdings/positions). Sync SDK wrapped with `asyncio.to_thread`. Read-only (no orders).
- **Kite server-side login flow**: `GET /api/kite/login-url`, `POST /api/kite/session`
  (exchanges request_token → daily access_token via `generate_session`), `POST /api/kite/logout`,
  `GET /api/kite/status`. Token stored in `system.configuration` + in-memory (`zerodha/session.py`).
- **Dynamic provider registry**: market/portfolio resolve to Kite when `DATA_PROVIDER=zerodha`
  and a Kite session exists, else mock; AI resolves to OpenAI when configured, else mock.
  `reset_orchestrator()` re-wires providers after a Kite login without restart.
- **AIService** now degrades gracefully: on any AI provider error it returns a grounded
  fallback (deterministic bias/confidence, `error` field) instead of failing the analysis.
- **Settings UI**: "Broker Connection · Zerodha Kite" panel (login URL, request_token paste,
  connect/disconnect, live status). Providers panel shows selected vs active mode.
- **Docker/GCP**: `backend/Dockerfile`, `frontend/Dockerfile` + `nginx.conf`,
  `docker-compose.yml`, `.dockerignore`, `docs/DEPLOYMENT.md`.
### Notes
- OpenAI key provided is valid but the account currently has **no credits**
  (`insufficient_quota`); live AI activates automatically once credits are added — no code change.
- Kite requires an interactive daily login (Zerodha 2FA) to mint the access token; until then
  the app transparently uses labelled DEMO/MOCK data.
- Fundamental & News remain mock (no verified provider/credentials yet).

## [1.0.0] — 2026-09-04 — V1 vertical slice
### Added
- Provider abstractions (MarketData/Fundamental/News/Portfolio/AI/Knowledge) + deterministic
  MOCK implementations; `registry` selection; Zerodha adapter shell (pending verification).
- PostgreSQL 15 data layer (7 schemas, idempotent DDL, Timescale-ready candle tables);
  Redis cache with in-memory fallback.
- Market-data warehouse: fetch-once/store/reuse, idempotent + incremental ingestion,
  `market_data_version`, `job_runs` audit.
- Indicator engine `technical_v1`; Market & Sector context engines.
- Three strategies (`long_term_v1`, `swing_v1`, `intraday_v1`) with configurable weights.
- Central scoring engine `scoring_v1` (score + independent confidence + factor contributions
  + missing-data handling); deterministic Risk Engine `risk_v1` (hypothetical setups).
- AI layer: `AIService` → `AIProvider` → `MockAIProvider`; Pydantic-validated structured
  output; versioned prompts; Redis + `ai_analyses` caching; deterministic-first cost control.
- Portfolio module with documented Healthy/Watch/Review rules (mock Zerodha holdings).
- NIFTY 50 scanner (ranked, AI on finalists only); historical NIFTY 50 membership seed.
- EVALS: AI graders + synthetic hallucination cases + strategy-eval data model; EVALS API + UI.
- FastAPI routes under `/api`; startup seeding (instruments, membership, eval datasets).
- React + Tailwind + shadcn dashboard: 10 screens, dependency-free candlestick/RSI charts,
  DEMO-MOCK / STALE / freshness badges, Settings, Data Health observability.
- Full `docs/` set + backend unit tests.

### Notes / deviations
- Frontend uses React+Tailwind+shadcn (JS) instead of MUI+TypeScript (user choice).
- TimescaleDB extension unavailable on this arch → plain PostgreSQL 15 with Timescale-ready
  schema (documented). All external providers are MOCK (no credentials configured).
