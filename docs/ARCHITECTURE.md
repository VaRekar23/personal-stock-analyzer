# Architecture

## Non-negotiable principle
> **Python calculates facts; AI explains them.**
> `Zerodha/Providers → Data Layer → Indicator Engine → Strategy Engine → Scoring
> Engine → Risk Engine → AI Explanation`. AI consumes structured evidence and never
> computes indicators or invents trade levels. Deterministic outputs are authoritative.

## High-level flow
```mermaid
flowchart LR
  subgraph Providers[Provider Interfaces (mock in V1)]
    MD[MarketDataProvider]
    FD[FundamentalDataProvider]
    NW[NewsProvider]
    PF[PortfolioProvider]
    KN[KnowledgeProvider (RAG seam)]
  end
  MD --> WH[Warehouse / Ingestion\nPostgreSQL]
  WH --> IND[Indicator Engine\ntechnical_v1]
  IND --> CTX[Market & Sector Context]
  IND --> STR[Strategy Engines\nlong_term / swing / intraday]
  FD --> STR
  CTX --> STR
  STR --> SCORE[Scoring Engine\nscoring_v1]
  SCORE --> RISK[Risk Engine\nrisk_v1]
  SCORE --> AISVC[AIService]
  RISK --> AISVC
  AISVC --> AIP[AIProvider -> MockAIProvider]
  AISVC --> CACHE[(Redis + ai_analyses)]
  STR --> RUNS[(analysis.analysis_runs)]
  SCORE --> EV[EVALS framework]
  AISVC --> EV
```

## Layers
- **Providers** (`stockai/providers`, `stockai/ai`): vendor-agnostic interfaces
  (`providers/base.py`) + concrete implementations. `registry.py` selects providers
  from config; business logic never imports a vendor directly.
- **Data layer** (`stockai/core/db.py`, `stockai/data/warehouse.py`): PostgreSQL is the
  source of truth. Warehouse implements fetch-once/store/reuse + idempotent ingestion.
- **Compute** (`indicators`, `context`, `strategies`, `scoring`, `risk`): pure,
  deterministic, versioned. No I/O to vendors, no AI.
- **AI** (`stockai/ai`): `AIService` orchestrates prompt build → provider call → schema
  validation → cache. `MockAIProvider` is grounded (echoes only supplied numbers).
- **Orchestration** (`stockai/analysis`): `orchestrator.py` ties the pipeline together
  and persists runs with full version provenance; `portfolio.py` for holdings analysis.
- **EVALS** (`stockai/evals`): vendor-independent graders + datasets + runner.
- **API** (`stockai/api.py`, `server.py`): thin FastAPI handlers under `/api`.
- **Frontend** (`frontend/src`): React Query for server state; pages per screen;
  charts are dependency-free SVG (candlestick/RSI) + Recharts available.

## Frontend ↔ Backend
- Frontend calls `${REACT_APP_BACKEND_URL}/api/...` (see `frontend/src/lib/api.js`).
- All backend routes are prefixed `/api` for the Kubernetes ingress.
- No secrets ever reach the browser; only non-sensitive settings are exposed via `/api/settings`.

## Cache flow
- Read-through cache on analysis/scan/AI. Redis primary; **in-memory fallback** if Redis
  is down (functionality preserved, Data Health shows DEGRADED). See CACHE_STRATEGY.md.

## AI flow (cost-controlled)
- Scanner scores all 50 deterministically, then calls AI only for the top-N finalists
  above a score threshold. Single-stock analysis calls AI once (cached by effective input).

## Error handling
- Providers return structured errors; the live Zerodha/TrueData adapters raise
  `ProviderPendingError` ("pending verification") instead of fabricating data.
- DB/Redis outages degrade gracefully; nothing returns fabricated "success".

## Why these technologies
- **FastAPI/Pydantic**: async, typed request/response, schema validation for AI output.
- **PostgreSQL**: relational integrity for the multi-schema model; Timescale-ready for
  time-series scale-out.
- **Redis**: cheap, fast cache to satisfy the cost-control requirement.
- **Provider abstraction**: hard requirement to swap vendors without rewrites.
