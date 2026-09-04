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
- Replace `NullKnowledgeProvider` with a vector-store-backed retriever over annual/
  quarterly reports, transcripts, filings, investor notes. **Never** for computing
  price/indicators/trade levels. Justify any vector-DB cost in docs.

## Analysis & strategy
- **Historical strategy evaluation / backtesting** using `index_memberships` (point-in-time,
  survivorship-bias-free) + the `evaluation` schema (expected vs realized outcomes).
- Strategy optimization / weight tuning; additional strategies (versioned `*_v2`).
- Richer market/sector context from real index feeds; more fundamental sources.
- Advanced alerts; scheduled scans; deeper news sentiment analysis.

## Historical membership import
- Documented importer from NSE archives to replace the current labelled current-list seed.

## Explicitly still NOT planned
Automated order execution, autonomous trading agents, multi-tenant SaaS/billing, mobile app.
