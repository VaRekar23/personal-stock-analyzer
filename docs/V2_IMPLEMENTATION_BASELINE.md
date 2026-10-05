# V2 Implementation Baseline

Snapshot of the repository BEFORE/at the start of V2, so future agents know what
already existed vs. what V2 changed. (Audit per V2 spec §2.)

## What V1 already contains (COMPLETE, verified by code + tests)
- **Provider abstractions** (`providers/base.py`): MarketData, Fundamental, News,
  Portfolio, AI, Knowledge — business logic depends only on these.
- **Live Zerodha/Kite adapter** (`providers/zerodha/live.py`) + daily login flow
  (`api.py` `/kite/*`, `session.py`) + **robust instrument-master resolution**
  (`providers/zerodha/instruments.py`: Redis/Postgres-cached master + `ltp()` fallback;
  resolves any NSE symbol incl. LTIM; unknown → 404).
- **yfinance fundamentals + news** (`providers/yfinance_provider.py`) — live, cached.
- **OpenAI AI provider** + **Gemini fallback** (`ai/openai_provider.py`,
  `ai/gemini_provider.py`, chained in `ai/service.py`); deterministic bias/confidence/
  trade-levels stay authoritative.
- **Deterministic engines**: indicators, market/sector context, 3 strategies
  (long_term/swing/intraday), central scoring, risk engine. Versioned (`core/versions.py`).
- **Warehouse** (`data/warehouse.py`): fetch-once/store/reuse, idempotent, incremental,
  in-memory fallback when DB down.
- **EVALS** (`evals/`): AI grounding + synthetic hallucination cases + strategy-eval schema.
- **Historical NIFTY 50 membership** (`index_data.index_memberships`).
- **PostgreSQL 15** source of truth (Timescale-ready schema); graceful degrade when down.
- **Error handling**: UnknownSymbolError→404, TokenException→503, KiteException→502,
  global 500 handler with CORS headers; no hidden mock fallback when a live provider is selected.

## What was PARTIAL / changed in V2
- **Cache was Redis-backed** (`core/cache.py` + Redis service). V2 replaces it with a
  **PostgreSQL-backed cache** (`system.cache_entries`), same public API. Redis removed from
  runtime, requirements, supervisor, docker-compose, env.

## What V2 deliberately leaves UNCHANGED
- Scoring weights/logic, risk logic, strategy framework (no silent changes; any change ⇒ new version).
- Frontend design/screens (only labels/health reflect live vs mock dynamically).
- Provider selection model (`DATA_PROVIDER`/`FUNDAMENTAL_PROVIDER`/`NEWS_PROVIDER`/`AI_PROVIDER`).
- EVAL datasets and framework (preserved; synthetic cases remain).
- No WebSocket, no continuous polling, no order placement, no RAG stack, no backtester.
