# V2 Roadmap

Foundations for these exist in V1; do not build them until needed.

## Data & infrastructure
- **TimescaleDB hypertables** on `market.candles_*` (+ compression, `drop_chunks`
  retention for intraday). One `create_hypertable` per table.
- **Live provider integrations** (verified): Zerodha/Kite (historical, holdings, quotes),
  TrueData (fundamentals + news). Replace mocks; keep interfaces. See API_INTEGRATIONS.md.
- **Background job queue** for scheduled/incremental ingestion (currently on-demand,
  audited in `system.job_runs`).

## AI
- **OpenAIProvider** (and Anthropic/Gemini) implementing `AIProvider`. Add `OPENAI_API_KEY`.
- Prompt version bumps as prompts evolve; keep old versions for EVAL comparability.

## RAG (KnowledgeProvider)
- **DONE in V3** with PostgreSQL full-text search (`PgKnowledgeProvider`); no vector DB. See KNOWLEDGE_RESEARCH.md.
  Future: optional pgvector + local embeddings.

## Analysis & strategy
- **DONE in V3 (single symbols / user lists)**: deterministic backtester `backtest_v1`, see STRATEGY_EVALUATION.md.
  Index-wide point-in-time universes remain blocked on verified membership data.
- Strategy optimization / weight tuning; additional strategies (versioned `*_v2`).
- Richer market/sector context from real index feeds; more fundamental sources.
- Advanced alerts; scheduled scans; deeper news sentiment analysis.

## Historical membership import
- V3 added a CSV importer with mandatory source + `verification_status` (`POST /api/index-memberships/import`).
  Automated NSE archive download is not implemented (access restrictions); verified data must be supplied by the user.

## Explicitly still NOT planned
Automated order execution, autonomous trading agents, multi-tenant SaaS/billing, mobile app.
