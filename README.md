# StockAI — Personal AI-Powered Indian Stock Analysis Platform (V1)

A personal, single-user quantitative research and portfolio-intelligence platform for
Indian equities (NSE / NIFTY 50). It combines **deterministic** technical/fundamental
analysis, quantitative scoring and a **deterministic Risk Engine** with an **AI
explanation layer**. It is **not** an automated trading / order-placement system.

> **Core principle:** Python calculates facts (indicators, scores, trade levels);
> AI explains and synthesizes structured facts. The AI never invents prices,
> indicators or trade levels.

## Status of this build
This is a **working end-to-end V1 vertical slice**. All external providers
(Zerodha/Kite, TrueData fundamentals/news, OpenAI) run through **provider
interfaces** with **deterministic MOCK implementations** that are clearly labelled
`DEMO / MOCK DATA` in the UI and `source=mock` in the data. No credentials are
required to run it.

## Tech stack (as deployed here)
| Layer | Chosen | Notes |
|---|---|---|
| Frontend | React + Tailwind + shadcn/ui + Recharts (JS) | Dark "terminal" dashboard. (Spec's MUI/TS deferred — see docs/V1_SCOPE.md.) |
| Backend | Python + FastAPI + Pydantic + Pandas/NumPy | Domain logic decoupled from routes |
| Database | **PostgreSQL 15** (Timescale-ready schema) | Source of truth. TimescaleDB extension unavailable on this arch — hypertables documented as target |
| Cache | **Redis 7** | Graceful in-memory fallback |
| AI | AIProvider abstraction → MockAIProvider | OpenAI/Anthropic/Gemini addable without touching business logic |

## Run
Services are managed by supervisor (`backend`, `frontend`, `postgresql`, `redis`, `mongodb`).
- Backend: FastAPI on `:8001` (all routes under `/api`).
- Frontend: React on `:3000` (uses `REACT_APP_BACKEND_URL`).

```
sudo supervisorctl status
curl $REACT_APP_BACKEND_URL/api/health
```

## Read the docs first (for V2 / future agents)
Start here, in order:
1. `docs/V1_SCOPE.md`
2. `docs/ARCHITECTURE.md`
3. `docs/CODE_STRUCTURE.md`
4. `docs/DATABASE_SCHEMA.md`
5. `docs/API_INTEGRATIONS.md`
6. `docs/CHANGELOG.md`

Then: `DATA_PIPELINES`, `ANALYSIS_ENGINE`, `SCORING_AND_RISK`, `AI_ARCHITECTURE`,
`EVALS`, `CACHE_STRATEGY`, `CONFIGURATION`, `V2_ROADMAP`.

## Acceptance workflows (all supported)
- Search RELIANCE → run Long-term / Swing / Intraday analysis (score, confidence, factors, risks, AI explanation).
- NIFTY 50 → Swing / Intraday scan → ranked candidates (AI only on finalists).
- Portfolio → mock Zerodha holdings analysed with documented health rules.
- Re-run same analysis → served from cache, no repeat AI call.
- EVALS → synthetic hallucination cases + live-pipeline grounding checks with pass/fail/scores/versions.
- Mock-only mode → app fully functional, clearly labelled demo data.

**Disclaimer:** Research & decision-support only. Not investment advice. No orders are placed.
