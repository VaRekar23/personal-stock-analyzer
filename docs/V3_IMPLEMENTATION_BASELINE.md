# StockAI V3 Implementation Baseline

Audit of the repository **before** V3 changes (carried out at the start of V3 work, Sept/Oct 2026).

## Verified pre-V3 state (from source + tests, not stale docs)

| Area | State |
|---|---|
| Deterministic engines | Working: indicators, scoring, strategy, risk, context, warehouse. 37/37 tests passed pre-V3. |
| Providers | Zerodha (live market/portfolio via daily Kite token), yfinance (fundamentals/news), OpenAI + Gemini AI chain (OpenAI key out of quota → Gemini fallback active). |
| Cache | PostgreSQL-backed (`system.cache_entries`) via `stockai/core/cache.py`. **No Redis anywhere.** |
| Knowledge seam | `NullKnowledgeProvider` no-op stub in `stockai/providers/knowledge.py`; `KnowledgeProvider` Protocol in `providers/base.py`. No ingestion, retrieval, or UI existed. |
| EVALS | Vendor-independent AI-quality EVALS working (`evaluation.eval_runs`). Historical post-trade R runner **deferred/absent** — no backtester existed. |
| DB | `system.*`, `analysis.*`, `index_data.*`, `evaluation.*` schemas live. No `knowledge.*` schema. |
| Frontend | React + JS + Tailwind + shadcn/ui. Pages: Dashboard, Portfolio, StockAnalysis, Scanner, Modes, EVALS, DataHealth, Settings. No Research/Backtesting pages. |
| Deployment | Docker + `cloudbuild.yaml` for GCP Cloud Run. Frontend needs `REACT_APP_BACKEND_URL` baked at build time. |

## Gaps identified for V3
1. No document ingestion/retrieval (Part A).
2. No grounded research Q&A with citations.
3. No deterministic historical strategy evaluation/backtester (Part B).
4. No point-in-time NIFTY 50 membership verification (docs flagged this already).

## Intended V3 changes (approved by user)
- **Part A first**: PostgreSQL full-text search RAG (no pgvector, no paid embeddings, no vector DB — user decision).
- **Part B follow-up**: swing + intraday backtester (swing first): daily candles, next-open entry, conservative same-candle stop/target rule. No optimizer.
