# V1 Scope

## In scope (implemented)
- **Provider abstractions**: MarketData, Fundamental, News, Portfolio, AI, Knowledge.
- **Deterministic MOCK providers** for all external vendors (reproducible, seeded).
- **Market-data warehouse** (PostgreSQL): fetch-once/store/reuse, idempotent ingestion,
  incremental update, per-interval tables (1m/5m/15m/1h/1d).
- **Technical indicator engine** (`technical_v1`): SMA, EMA(20/50/200), RSI, MACD, ATR,
  VWAP, Supertrend, Bollinger, pivots, rel-volume, S/R, 52-week, trend classification.
- **Market & Sector context engines** (explicit sector→index mapping).
- **Three separate strategy engines**: `long_term_v1`, `swing_v1`, `intraday_v1`
  (configurable weights in `config/weights.yaml`).
- **Central scoring engine** (`scoring_v1`): 0–100 score + separate confidence,
  factor contributions, missing-data handling (no-data ≠ negative).
- **Deterministic Risk Engine** (`risk_v1`): entry/zone, stop, targets, R:R, position size.
  Configurable risk assumptions. No orders placed.
- **AI explanation layer**: AIService → AIProvider → MockAIProvider, structured Pydantic
  output, versioned prompts, aggressive caching (Redis + `analysis.ai_analyses`).
- **AI cost control**: deterministic scan first, AI only for top-N finalists above threshold.
- **Portfolio module**: mock Zerodha holdings, P&L, documented Healthy/Watch/Review rules.
- **NIFTY 50 scanner**: current universe, ranked, sortable/filterable UI.
- **Historical NIFTY 50 membership**: point-in-time `index_memberships` (labelled seed source).
- **EVALS (V1)**: AI evals (schema/consistency/grounding/completeness) + synthetic
  hallucination-detection cases + strategy-eval data model foundation.
- **Data Health / observability**: provider status, cache hit-rate, versions, freshness.
- **Settings**: editable non-sensitive config (risk, thresholds, cache TTLs).
- **10 UI screens** + data-freshness / STALE / DEMO-MOCK badges.
- **Full docs/** set + backend unit tests.

## Explicitly NOT in scope for V1
- Automatic order placement / broker execution.
- Live WebSocket market streaming; continuous intraday polling.
- Live Zerodha / TrueData / OpenAI integrations (interfaces + mocks only; **pending credential verification**).
- Multi-tenant SaaS, billing, auth/RBAC, social/collaboration, mobile native app.
- Vector database / full RAG implementation (only a `KnowledgeProvider` seam).
- Backtesting engine, strategy optimization, automatic strategy evolution, scheduled scans, alerts.

## Deviations from the original spec (and why)
- **Frontend is React + Tailwind + shadcn (JS), not MUI + TypeScript.** Chosen by the
  user to match the native Emergent environment for speed/reliability. The component
  structure keeps a clean migration path.
- **TimescaleDB extension is not installed** (unavailable for this CPU arch/repo here).
  We use **plain PostgreSQL 15** with a Timescale-ready schema (composite PKs,
  per-interval tables, time-desc indexes). Converting the candle tables to hypertables
  is a one-line `create_hypertable` per table when the extension is available.
- **Background jobs**: ingestion runs synchronously on demand (within request) and is
  recorded in `system.job_runs`. A heavier queue is deferred to V2 (see V2_ROADMAP).
