# Changelog

All notable architectural changes. Keep in sync with implementation & version bumps.

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
