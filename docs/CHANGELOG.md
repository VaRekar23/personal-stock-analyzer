# Changelog

All notable architectural changes. Keep in sync with implementation & version bumps.

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
