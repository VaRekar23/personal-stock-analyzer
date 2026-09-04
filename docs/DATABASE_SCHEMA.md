# Database Schema (PostgreSQL 15)

DDL source of truth: `backend/stockai/core/schema.sql` (idempotent). Seven schemas.
Market-data tables are **Timescale-ready**: composite PK `(symbol, ts)` guarantees
idempotent ingestion (no duplicate candles) and per-interval tables allow
`create_hypertable('market.candles_1d','ts')` when TimescaleDB is available.

## `market`
| Table | Key columns | Notes |
|---|---|---|
| `instruments` | `symbol` PK | name, exchange, segment, instrument_token, sector, lot/tick size |
| `candles_1m/5m/15m/1h/1d` | PK `(symbol, ts)` | open/high/low/close, volume, open_interest, source. Index `(symbol, ts DESC)` on 1d/15m |

## `fundamental`
| Table | Key | Notes |
|---|---|---|
| `companies` | `symbol` PK→instruments | company_name, industry, market_cap, source, retrieved_at |
| `financial_statements` | serial PK, UNIQUE `(symbol,statement_type,period)` | JSONB `data`, source, retrieved_at |
| `fundamental_ratios` | `symbol` PK | JSONB ratios, period, source, retrieved_at |
| `shareholding` | PK `(symbol,period)` | promoter/FII/DII/public in JSONB |
| `corporate_actions` | serial PK | action_type, ex_date, JSONB details |

Every fundamental row records **source + retrieved_at + period** for provenance.

## `index_data`
| Table | Key | Notes |
|---|---|---|
| `indexes` | `index_name` PK | e.g. NIFTY 50 |
| `index_memberships` | serial PK, UNIQUE `(index_name,symbol,valid_from)` | **point-in-time** membership (`valid_from`,`valid_to`,`source`). Answers "who was in NIFTY 50 on date D". Avoids survivorship bias |

## `portfolio`
| Table | Key | Notes |
|---|---|---|
| `holdings` | serial PK | symbol, quantity, average_price, source, snapshot_at |
| `positions` | serial PK | intraday positions (empty in V1 mock) |
| `portfolio_snapshots` | serial PK | JSONB snapshot |

## `analysis`
| Table | Key | Notes |
|---|---|---|
| `analysis_runs` | `id` UUID PK | full provenance: strategy/indicator/scoring/risk/prompt versions, provider, model, market_data_version, cache_key, ai_cached, JSONB result. Index `(symbol,analysis_type,created_at DESC)` |
| `ai_analyses` | `cache_key` PK | persisted AI cache (symbol, type, provider, model, prompt_version, JSONB result) |

## `evaluation`
| Table | Key | Notes |
|---|---|---|
| `eval_datasets` | `id` PK | name, description, kind, version |
| `eval_cases` | `case_id` PK | dataset_id, evaluation_type, label, JSONB input, JSONB expected_output, version, created_at |
| `eval_runs` | `id` UUID PK | passed/failed/total/avg_score, JSONB metadata |
| `eval_results` | serial PK | run_id, case_id, evaluation_type, passed, score, JSONB actual_output/detail |

## `system`
| Table | Key | Notes |
|---|---|---|
| `api_provider_status` | `provider` PK | mode/status/detail |
| `job_runs` | serial PK | ingestion & background job audit (job, status, detail, timestamps) |
| `configuration` | `key` PK | JSONB runtime settings overrides (Settings page) |

## Common query patterns
- Latest N candles: `SELECT ... FROM market.candles_1d WHERE symbol=$1 ORDER BY ts DESC LIMIT $2`.
- Idempotent ingest: `INSERT ... ON CONFLICT (symbol,ts) DO NOTHING`.
- Latest analysis: order `analysis_runs` by `created_at DESC`.
- Membership as-of date D: `WHERE valid_from<=D AND (valid_to IS NULL OR valid_to>D)`.

## Retention (future)
No retention policy in V1. With TimescaleDB, add compression + `drop_chunks` for
intraday tables (see V2_ROADMAP.md).
