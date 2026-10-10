# StockAI — Personal AI-Powered Indian Stock Analysis Platform (V3)

A personal, single-user research and portfolio-intelligence platform for Indian equities (NSE).
It combines **deterministic** technical/fundamental analysis, quantitative scoring and a
**deterministic Risk Engine** with an **AI explanation layer**. V3 adds **document-grounded company research (RAG)**
and **deterministic historical strategy evaluation (backtesting)**. It is **not** a trading or order-placement system.

> **Core principle:** Python calculates facts (indicators, scores, trade levels, backtest results).
> AI explains and synthesizes supplied facts and cited documents. The AI never invents prices,
> indicators, trade levels or sources.

## Status of this build
| Capability | Provider / implementation | Notes |
|---|---|---|
| Market data + portfolio | Zerodha Kite Connect (`DATA_PROVIDER=zerodha`) | Live only after the daily login (Settings → Broker Connection). Without a token it falls back to a clearly labelled **MOCK** provider. |
| Fundamentals + news | yfinance (`FUNDAMENTAL_PROVIDER/NEWS_PROVIDER=yfinance`) | Free, current-snapshot only (no point-in-time history). Personal use. |
| AI | OpenAI (`AI_MODEL`, e.g. gpt-4o-mini) → Gemini fallback (`GEMINI_MODEL`) | Gemini answers automatically when OpenAI fails (e.g. quota). |
| Cache | **PostgreSQL** `system.cache_entries` | Redis was removed in V2. |
| Knowledge research (V3) | PostgreSQL full-text search | See `docs/KNOWLEDGE_RESEARCH.md` |
| Backtesting (V3) | Deterministic replay, PostgreSQL job records | See `docs/STRATEGY_EVALUATION.md` |

## Tech stack
| Layer | Chosen |
|---|---|
| Frontend | React (JavaScript) + Tailwind + shadcn/ui + Recharts |
| Backend | Python + FastAPI + Pydantic + NumPy |
| Database / cache | PostgreSQL 15 (standard; TimescaleDB not required) |
| Documents | pypdf (text PDFs; no OCR) |

## Run
Supervisor programs: `backend` (:8001, routes under `/api`), `frontend` (:3000), `postgresql`.
```
sudo supervisorctl status
curl $REACT_APP_BACKEND_URL/api/health
cd backend && python -m pytest tests/ -q
```
Deployment (GCP Cloud Run): `docs/DEPLOYMENT.md`.

## Docs (read in order)
`docs/V3_IMPLEMENTATION_STATUS.md`, `ARCHITECTURE`, `CODE_STRUCTURE`, `DATABASE_SCHEMA`, `API_INTEGRATIONS`,
`KNOWLEDGE_RESEARCH`, `STRATEGY_EVALUATION`, `EVALS`, `CACHE_STRATEGY`, `CONFIGURATION`, `CHANGELOG`.

## Workflows
- Stock Analysis: Long-term / Swing / Intraday (score, factors, risk setup, AI explanation).
- NIFTY 50 scanner (deterministic ranking; AI only on finalists). Portfolio analysis from Zerodha holdings.
- Research: upload annual reports/transcripts/notes → ask questions → cited answers with inspectable excerpts.
- Backtesting: check coverage → prepare data (Zerodha) → run → metrics, equity curve, per-trade table. Runs are stored and reproducible.
- EVALS: AI EVALS (grounding/hallucination) and, separately, Strategy EVALS (synthetic backtest accounting fixtures).

**Disclaimer:** Research & decision-support only. Not investment advice. No orders are placed.
