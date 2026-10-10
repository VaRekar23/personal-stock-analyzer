# PRD — StockAI: Personal AI-Powered Indian Stock Analysis Platform (V1)

## Original problem statement
Personal (single-user) quantitative research + portfolio-intelligence web app for Indian
equities (NIFTY 50). Combines Zerodha/Kite market+portfolio data, historical market-data
warehouse, fundamentals, market/sector context, deterministic technical indicators &
quantitative scoring, a deterministic Risk Engine (hypothetical trade setups), an AI
explanation layer, and an EVALS framework. NOT an order-placement system. Modes:
long-term, swing, intraday. Hard rule: **Python computes facts; AI only explains them.**

## User & choices
- Single power-user (owner). No auth/multi-tenant.
- DB: PostgreSQL 15 + Redis 7 in-container (TimescaleDB unavailable on arch → Timescale-ready plain PG).
- All external providers = deterministic MOCK (Zerodha/TrueData/OpenAI), labelled DEMO/MOCK.
- Frontend: React + Tailwind + shadcn (JS). AI: MockAIProvider.

## Architecture (implemented)
Provider interfaces → Warehouse (PostgreSQL) → Indicator engine → Market/Sector context →
Strategy engines (long_term/swing/intraday) → Scoring engine → Risk engine → AIService
(AIProvider→Mock) → Redis cache + analysis_runs. EVALS framework grades AI vs deterministic.
FastAPI (`/api`) + React Query dashboard. Full versioning/provenance. Docs in `/app/docs`.

## Core requirements (static)
- Deterministic-first, auditable, reproducible; AI never invents numbers.
- Vendor-swappable provider abstractions; runnable fully on mocks.
- Aggressive AI caching + deterministic shortlisting for cost control.
- Clear data provenance / freshness / STALE / DEMO badges. No order placement.

## Implemented (2026-09-04, v1.0.0)
- Backend: 15 API surfaces (health, market overview, analyze, scan, portfolio,
  fundamentals, news, candles, evals run/latest, settings get/put, instruments, quote,
  analysis history). All 3 modes; deterministic indicators/scoring/risk; grounded mock AI;
  EVALS (AI graders + synthetic hallucination cases + strategy-eval data model).
- Data: PostgreSQL 7-schema model, idempotent warehouse ingestion, point-in-time NIFTY 50
  membership seed, Redis cache w/ in-memory fallback.
- Frontend: 10 screens (Dashboard, Portfolio, Stock Analysis w/ 8 tabs + candlestick charts,
  NIFTY 50 Scanner, Long/Swing/Intraday mode scanners, EVALS, Data Health, Settings).
- Docs: README + 14 docs/*.md + .env.example. Backend unit tests (8) + API regression (20) pass.
- Verified: testing agent 100% backend (20/20) + frontend (all pages/tabs), zero bugs.

## Backlog (V2 — see docs/V2_ROADMAP.md)
- P1: Live Zerodha + TrueData integrations (pending credential verification); OpenAIProvider.
- P1: TimescaleDB hypertables + compression/retention.
- P2: RAG (KnowledgeProvider + vector store) for reports/transcripts.
- P2: Historical backtesting/strategy evaluation using point-in-time membership.
- P2: Background job queue for scheduled ingestion; alerts; scheduled scans.
- P3: Strategy optimization; richer news sentiment; additional AI providers.

## Explicitly out of scope (all versions unless changed)
Automated order execution, autonomous trading agents, multi-tenant SaaS/billing, mobile app.


# V3 (2026-10-10)
## Implemented: Part A — Knowledge Research (RAG)
- PgKnowledgeProvider: PostgreSQL FTS ingestion/retrieval, content-hash dedupe, pypdf PDF extraction, bounded chunks with page provenance.
- Grounded research (stockai/knowledge/research.py) via existing AIProvider chain; citations resolve to stored chunks; prompt-injection guard verified; explicit "not established" when no evidence.
- API: POST /api/knowledge/upload, GET/DELETE /api/knowledge/documents, GET /api/knowledge/search, POST /api/research. UI: /research page.
- Tests: tests/test_knowledge.py (4). Full suite 41/41. Docs: KNOWLEDGE_RESEARCH.md, V3_IMPLEMENTATION_BASELINE.md, V3_IMPLEMENTATION_STATUS.md.
## Decisions
- FTS-only (no pgvector/embeddings) per user; swing+intraday backtester (swing first) approved for Part B follow-up.
## Next: Part B — deterministic backtester (next-open entry, conservative same-candle rule, no look-ahead, synthetic EVAL fixtures, PG run records, Backtesting UI).

## V3 Part B DONE (2026-10-10)
- backtest_v1: swing 1d + intraday 15m/5m; user decisions: full exit at T1 (T2 counterfactual), limit at zone edge next bar only, index-wide runs refused, Prepare-data button (Zerodha chunked).
- Endpoints: GET /api/backtests/options, POST /api/backtests/coverage, POST /api/backtests/prepare, POST /api/backtests, GET /api/backtests, GET /api/backtests/{id}, GET /api/evals/strategy, POST /api/index-memberships/import.
- Remaining: live Zerodha validation of prepare + intraday; verified membership data (BLOCKED); OpenAI key still credit_balance_exhausted.
