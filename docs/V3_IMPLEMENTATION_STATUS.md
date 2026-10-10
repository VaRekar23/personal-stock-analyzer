# V3 Implementation Status

Last updated: 2026-10-10. Legend: COMPLETED · PARTIAL · BLOCKED · DEFERRED.

## PART A — Knowledge-based company research
| Item | Status | Notes |
|---|---|---|
| KnowledgeProvider implemented (`PgKnowledgeProvider`) | COMPLETED | `providers/knowledge.py`, registry wired |
| Upload (UI + endpoint), PDF/txt/md/csv, ≤15 MB | COMPLETED | Scanned PDFs rejected with explicit error (no OCR) |
| Chunking with provenance, content-hash dedupe | COMPLETED | 1100/150 chars; page numbers for PDFs |
| PostgreSQL FTS retrieval (bounded ≤8) | COMPLETED | OR-of-terms tsquery + ts_rank, symbol filter |
| pgvector / embeddings | DEFERRED (user decision) | No extra cost or deps |
| Grounded research with real citations, "not established" handling | COMPLETED | `knowledge/research.py`, `POST /api/research` |
| Prompt-injection guard | COMPLETED | Verified with a planted instruction |
| Delete document cascades chunks | COMPLETED | FK ON DELETE CASCADE |
| Retry failed ingestion | PARTIAL | Failure + `error_detail` are visible; retry means re-upload |
| Research combined with deterministic analysis context | DEFERRED | Documents only; RAG never touches trade levels |
| Persisted research history | DEFERRED | Answers cached (PG cache), not listed |

## PART B — Historical strategy evaluation
| Item | Status | Notes |
|---|---|---|
| Deterministic replay engine reusing indicators/strategies/Risk Engine | COMPLETED | `backtest/engine.py` (backtest_v1) |
| Swing (1d) | COMPLETED | |
| Intraday (15m/5m) | COMPLETED (code) | Needs stored intraday history (Zerodha); session exits, no overnight |
| Long-term ranking mode | DEFERRED | No point-in-time fundamentals |
| No look-ahead (bar-close signal, next-bar limit entry) | COMPLETED | Fixture-proven (`no_lookahead`, `next_candle_execution`) |
| Conservative same-bar rule, gap rules, limit-fill bar rule | COMPLETED | Stop-first; ambiguity flagged per trade |
| Full exit at T1 + T2 counterfactual | COMPLETED | User decision |
| Costs/slippage, gross vs net, zero-cost warning | COMPLETED | |
| Metrics (all spec metrics, zero-denominator safe, sample warnings) | COMPLETED | `backtest/metrics.py`, defined in STRATEGY_EVALUATION.md |
| Data coverage/quality checks (gaps, dups, discontinuities, partial sessions, synthetic) | COMPLETED | `backtest/quality.py` |
| "Prepare data" — chunked Zerodha fetch of missing ranges | COMPLETED (code) | **Live validation needs a Zerodha login**. Refuses MOCK mode |
| PG job records, polling, identity-based reuse, stale-run recovery | COMPLETED | `backtest.runs/trades` |
| Point-in-time membership: schema + CSV importer + engine eligibility | PARTIAL | Index-wide runs disabled (user decision) |
| Verified historical NIFTY 50 data | BLOCKED | No permitted automated source; needs user-supplied official records |
| Backtesting UI (inputs, coverage, metrics, equity curve, trades, skipped, versions, SYNTHETIC banner) | COMPLETED | `/backtesting` |
| Strategy EVALS (21 synthetic fixtures) | COMPLETED | `backtest/fixtures.py`, `GET /api/evals/strategy` |
| Optimization / walk-forward | DEFERRED (out of scope) | |

## PART C — Storage / API / cost
PostgreSQL only (new schemas `knowledge`, `backtest`). No Redis, queue, vector DB or paid API was added.
Uploads are validated and size-limited, errors are structured, secrets stay server-side.

## Migrations (idempotent, auto-applied from `core/schema.sql`)
`knowledge.documents`, `knowledge.chunks`, `backtest.runs`, `backtest.trades`;
`index_data.index_memberships` + `retrieved_at`, `verification_status`.

## Configuration changes
`requirements.txt`: `pypdf==4.3.1`. `versions.py`: `BACKTEST_VERSION="backtest_v1"`. No new env vars.
Cloud Run: `--no-cpu-throttling` is recommended for background backtests (DEPLOYMENT.md).

## Tests run
`pytest tests/` gives **70 passed** (engines, instruments, cache, API, knowledge 4, backtest 30 incl. 21 fixtures).
End-to-end in preview: upload → research answered by Gemini with citations. Swing backtest on stored candles completed
(flagged SYNTHETIC because preview runs in MOCK market mode). Duplicate run reused. Validation errors return 422.

## Needs live credentials / data (not validated here)
- Zerodha: "Prepare data" against real history, and intraday backtests on real 15m/5m candles.
- OpenAI as primary AI: the configured key still returns `credit_balance_exhausted` (Gemini fallback works).

## Known limitations
Lexical retrieval only. No OCR. Prices are unadjusted (discontinuities are flagged). The sector factor is excluded in backtests.
The shared-capital constraint across symbols is not modelled. In-process jobs are per instance.

## Additional costs
None (pypdf is OSS. FTS and backtests run in the existing PostgreSQL and FastAPI. AI calls use existing keys).
