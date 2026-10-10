# Configuration

## Environment variables (`backend/.env`; secrets never sent to frontend)
| Var | Purpose | Notes |
|---|---|---|
| `DATABASE_URL` | PostgreSQL DSN | source of truth |
| `DATA_PROVIDER` | market data provider | `zerodha` (falls back to mock without a daily token) |
| `FUNDAMENTAL_PROVIDER` | fundamentals provider | `yfinance` |
| `NEWS_PROVIDER` | news provider | `mock` (V1) |
| `AI_PROVIDER` | AI provider | `mock` (V1) |
| `AI_MODEL` | model id | `mock-analyst-v1` |
| `CORS_ORIGINS` | CORS | `*` in dev |
| `MONGO_URL`, `DB_NAME` | (platform template) | not used by StockAI domain |
| *(future)* `ZERODHA_API_KEY/SECRET/ACCESS_TOKEN`, `FUNDAMENTAL_API_KEY`, `NEWS_API_KEY`, `OPENAI_API_KEY` | live providers | see `.env.example`, API_INTEGRATIONS.md |

Frontend: `REACT_APP_BACKEND_URL` (only). All API calls use `${REACT_APP_BACKEND_URL}/api`.

## Strategy weights (`backend/stockai/config/weights.yaml`)
Configurable per strategy (see SCORING_AND_RISK.md). Change file for defaults; bump the
strategy version if scoring logic changes.

## Runtime settings (`DEFAULT_SETTINGS` in `core/config.py`, overridable via Settings page → `system.configuration`)
- `risk`: `account_capital`, `risk_per_trade_pct`, ATR stop/target multipliers (swing & intraday).
- `cache`: `analysis_ttl_seconds`, `scanner_ttl_seconds`, `market_data_ttl_seconds`, `ai_ttl_seconds`.
- `thresholds`: `shortlist_min_score`, `shortlist_top_n`, `stale_market_minutes`, `stale_fundamental_days`.
- `providers`: selected data/fundamental/news/ai providers + `ai_model` (read-only display in V1).

Editable sections via `PUT /api/settings/{risk|cache|thresholds|providers}`. Sensitive
credentials are **never** exposed or editable through the UI/API.

## Versions (`core/versions.py`)
`INDICATOR_VERSION`, `STRATEGY_VERSIONS`, `SCORING_VERSION`, `RISK_VERSION`, `PROMPT_VERSIONS`.

## Supervisor programs
`backend` (:8001), `frontend` (:3000), `postgresql` (:5432), `mongodb`.
`postgresql` added via `/etc/supervisor/conf.d/datastores.conf`.

## V3 settings (code constants)
- Research: `MAX_UPLOAD_MB=15` (api.py), `CHUNK_CHARS=1100`, `CHUNK_OVERLAP=150`, `MAX_RETRIEVE=8` (providers/knowledge.py).
- Backtest: `MAX_SYMBOLS=10`, `MAX_RANGE_DAYS`, `KITE_CHUNK_DAYS`, `STALE_MINUTES=10` (backtest/service.py);
  `DEFAULT_ASSUMPTIONS`, `WINDOW`, `WARMUP` (backtest/engine.py). Capital, risk %, slippage and cost are per-run inputs.
