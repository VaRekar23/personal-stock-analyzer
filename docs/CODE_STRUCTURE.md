# Code Structure

## Backend (`/app/backend`)
```
server.py                     FastAPI entrypoint: lifespan (db/cache connect, schema,
                              seed instruments/index-membership/eval-datasets), CORS, router
stockai/
  core/
    config.py                 Env + provider selection + DEFAULT_SETTINGS + load_weights()
    versions.py               Version registry (indicator/strategy/scoring/risk/prompt)
    logging_config.py         Structured logging + secret redaction
    db.py                     asyncpg pool, schema init, fetch/execute helpers, health
    schema.sql                Full DDL (7 schemas). Idempotent.
    cache.py                  Redis client + in-memory fallback + stats + health
  config/weights.yaml         Configurable strategy weights (long_term/swing/intraday)
  providers/
    base.py                   Interfaces: MarketData/Fundamental/News/Portfolio/AI/Knowledge
    registry.py               Selects providers from config (all mock in V1)
    knowledge.py              NullKnowledgeProvider (RAG seam, V2)
    mock/market.py            Deterministic OHLCV generator + market_status()
    mock/fundamental.py       Deterministic fundamentals
    mock/news.py              Deterministic news
    mock/portfolio.py         Deterministic Zerodha-style holdings
    zerodha/client.py         Live adapter shell — ProviderPendingError (pending verification)
  ai/
    base? (in providers)      AIProvider Protocol lives in providers/base.py
    schemas.py                AIAnalysis Pydantic schema (structured output)
    prompts.py                Versioned prompt templates + grounding system instruction
    mock_provider.py          MockAIProvider (grounded; echoes only supplied numbers)
    service.py                AIService: cache-key, Redis+DB cache, schema validation
  indicators/engine.py        Deterministic indicators (technical_v1)
  context/engines.py          MarketContextEngine, SectorContextEngine
  strategies/
    base.py                   Normalization helpers (linear/band/inverse/direction)
    long_term.py swing.py intraday.py   Three separate strategies
  scoring/engine.py           Factor / ScoreResult / score_factors (scoring_v1)
  risk/engine.py              build_setup() hypothetical trade setups (risk_v1)
  data/
    nifty50.py                Constituents, sector map, sector→index map
    warehouse.py              Ingestion + get_candles + market_data_version
  analysis/
    orchestrator.py           analyze_stock(), scan() — the pipeline
    portfolio.py              analyze_portfolio() + health rules
  evals/
    framework.py              Graders (schema/consistency/factual/grounding/completeness)
    datasets.py               Synthetic cases + seed + run_evals()
  settings_store.py           DEFAULT_SETTINGS merged with DB overrides
  api.py                      All /api routes (thin handlers)
tests/                        pytest unit tests (indicators/scoring/risk/cache-key)
```

## Frontend (`/app/frontend/src`)
```
App.js                        Router + Layout (10 routes)
index.js                      QueryClientProvider + Sonner Toaster
index.css                     Dark "terminal" theme, fonts, panel/badge utilities
lib/api.js                    Axios client + all endpoint wrappers
lib/format.js                 Formatters (inr/pct/signClass/timeIST/isStale), MODES
components/
  Layout.jsx                  Sidebar + top ticker bar + global search
  common.jsx                  Panel, MockBadge, StaleBadge, StatusPill, BiasBadge,
                              ScoreBar, ConfidenceGauge, FactorBars, Metric, Spinner
  charts.jsx                  CandleChart, Sparkline, RsiLine (dependency-free SVG)
pages/
  Dashboard.jsx Portfolio.jsx StockAnalysis.jsx ScannerView.jsx
  Evals.jsx DataHealth.jsx Settings.jsx
```

## Where to add things (extension points)
- **New indicator** → `indicators/engine.py` (add fn + include in `compute_features`). Bump `INDICATOR_VERSION`.
- **New strategy** → `strategies/<name>.py` + weights in `config/weights.yaml` + wire in `orchestrator.analyze_stock`. Add to `STRATEGY_VERSIONS`.
- **New AI provider** → implement `AIProvider` (see `ai/mock_provider.py`), register in `providers/registry.ai_provider()`. Nothing else changes.
- **Live data provider** → implement interface in `providers/<vendor>/`, flip `registry` + `LIVE_PROVIDERS`, document in API_INTEGRATIONS.md.
- **New API route** → `api.py` (keep handlers thin; logic in domain layer).
- **New EVAL case** → `evals/datasets.py` (`SYNTHETIC_AI_CASES` or a new dataset) + seed.
- **RAG** → implement `KnowledgeProvider` (replace `NullKnowledgeProvider`).
