-- StockAI V1 PostgreSQL schema. Idempotent (safe to run repeatedly).
-- Market-data tables are Timescale-ready: partition/hypertable target documented
-- in docs/DATABASE_SCHEMA.md. Composite PKs prevent duplicate candles (idempotent ingest).

CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS fundamental;
CREATE SCHEMA IF NOT EXISTS index_data;
CREATE SCHEMA IF NOT EXISTS portfolio;
CREATE SCHEMA IF NOT EXISTS analysis;
CREATE SCHEMA IF NOT EXISTS evaluation;
CREATE SCHEMA IF NOT EXISTS system;

-- ============ MARKET ============
CREATE TABLE IF NOT EXISTS market.instruments (
    symbol TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    exchange TEXT NOT NULL DEFAULT 'NSE',
    segment TEXT NOT NULL DEFAULT 'EQ',
    instrument_token BIGINT,
    sector TEXT,
    lot_size INT DEFAULT 1,
    tick_size NUMERIC DEFAULT 0.05,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- One table per interval (matches spec: candles_1m/5m/15m/1h/1d).
CREATE TABLE IF NOT EXISTS market.candles_1m (
    symbol TEXT NOT NULL, ts TIMESTAMPTZ NOT NULL,
    open NUMERIC, high NUMERIC, low NUMERIC, close NUMERIC,
    volume BIGINT, open_interest BIGINT, source TEXT NOT NULL DEFAULT 'mock',
    PRIMARY KEY (symbol, ts));
CREATE TABLE IF NOT EXISTS market.candles_5m  (LIKE market.candles_1m INCLUDING ALL);
CREATE TABLE IF NOT EXISTS market.candles_15m (LIKE market.candles_1m INCLUDING ALL);
CREATE TABLE IF NOT EXISTS market.candles_1h  (LIKE market.candles_1m INCLUDING ALL);
CREATE TABLE IF NOT EXISTS market.candles_1d  (LIKE market.candles_1m INCLUDING ALL);
CREATE INDEX IF NOT EXISTS idx_candles_1d_ts ON market.candles_1d (symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_candles_15m_ts ON market.candles_15m (symbol, ts DESC);

-- ============ FUNDAMENTAL ============
CREATE TABLE IF NOT EXISTS fundamental.companies (
    symbol TEXT PRIMARY KEY REFERENCES market.instruments(symbol),
    company_name TEXT, industry TEXT, market_cap NUMERIC,
    source TEXT, retrieved_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS fundamental.financial_statements (
    id SERIAL PRIMARY KEY, symbol TEXT NOT NULL, statement_type TEXT NOT NULL,
    period TEXT NOT NULL, data JSONB NOT NULL, source TEXT,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (symbol, statement_type, period));
CREATE TABLE IF NOT EXISTS fundamental.fundamental_ratios (
    symbol TEXT PRIMARY KEY, data JSONB NOT NULL, period TEXT,
    source TEXT, retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS fundamental.shareholding (
    symbol TEXT NOT NULL, period TEXT NOT NULL, data JSONB NOT NULL,
    source TEXT, retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, period));
CREATE TABLE IF NOT EXISTS fundamental.corporate_actions (
    id SERIAL PRIMARY KEY, symbol TEXT NOT NULL, action_type TEXT NOT NULL,
    ex_date DATE, details JSONB, source TEXT);

-- ============ INDEX ============
CREATE TABLE IF NOT EXISTS index_data.indexes (
    index_name TEXT PRIMARY KEY, description TEXT);
CREATE TABLE IF NOT EXISTS index_data.index_memberships (
    id SERIAL PRIMARY KEY, index_name TEXT NOT NULL, symbol TEXT NOT NULL,
    valid_from DATE NOT NULL, valid_to DATE, source TEXT NOT NULL,
    UNIQUE (index_name, symbol, valid_from));

-- ============ PORTFOLIO ============
CREATE TABLE IF NOT EXISTS portfolio.holdings (
    id SERIAL PRIMARY KEY, symbol TEXT NOT NULL, quantity INT NOT NULL,
    average_price NUMERIC NOT NULL, source TEXT, snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS portfolio.positions (
    id SERIAL PRIMARY KEY, symbol TEXT NOT NULL, quantity INT NOT NULL,
    average_price NUMERIC, product TEXT, snapshot_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS portfolio.portfolio_snapshots (
    id SERIAL PRIMARY KEY, taken_at TIMESTAMPTZ NOT NULL DEFAULT now(), data JSONB NOT NULL);

-- ============ ANALYSIS ============
CREATE TABLE IF NOT EXISTS analysis.analysis_runs (
    id UUID PRIMARY KEY, symbol TEXT NOT NULL, analysis_type TEXT NOT NULL,
    strategy_version TEXT, indicator_version TEXT, scoring_version TEXT,
    risk_version TEXT, prompt_version TEXT, provider TEXT, model TEXT,
    market_data_version TEXT, cache_key TEXT, ai_cached BOOLEAN DEFAULT FALSE,
    result JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_runs_symbol ON analysis.analysis_runs (symbol, analysis_type, created_at DESC);
CREATE TABLE IF NOT EXISTS analysis.ai_analyses (
    cache_key TEXT PRIMARY KEY, symbol TEXT, analysis_type TEXT,
    provider TEXT, model TEXT, prompt_version TEXT,
    result JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now());

-- ============ EVALUATION ============
CREATE TABLE IF NOT EXISTS evaluation.eval_datasets (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
    kind TEXT NOT NULL, version TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS evaluation.eval_cases (
    case_id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL, evaluation_type TEXT NOT NULL,
    label TEXT, input JSONB NOT NULL, expected_output JSONB, version TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS evaluation.eval_runs (
    id UUID PRIMARY KEY, dataset_id TEXT, started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    passed INT DEFAULT 0, failed INT DEFAULT 0, total INT DEFAULT 0,
    avg_score NUMERIC, metadata JSONB);
CREATE TABLE IF NOT EXISTS evaluation.eval_results (
    id SERIAL PRIMARY KEY, run_id UUID NOT NULL, case_id TEXT NOT NULL,
    evaluation_type TEXT, passed BOOLEAN, score NUMERIC,
    actual_output JSONB, detail JSONB, created_at TIMESTAMPTZ NOT NULL DEFAULT now());

-- ============ SYSTEM ============
CREATE TABLE IF NOT EXISTS system.api_provider_status (
    provider TEXT PRIMARY KEY, mode TEXT NOT NULL, status TEXT NOT NULL,
    detail TEXT, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS system.job_runs (
    id SERIAL PRIMARY KEY, job TEXT NOT NULL, status TEXT NOT NULL,
    detail JSONB, started_at TIMESTAMPTZ NOT NULL DEFAULT now(), finished_at TIMESTAMPTZ);
CREATE TABLE IF NOT EXISTS system.configuration (
    key TEXT PRIMARY KEY, value JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now());

-- V2: PostgreSQL-backed cache (replaces Redis). Version-aware, TTL via expires_at.
CREATE TABLE IF NOT EXISTS system.cache_entries (
    cache_key TEXT PRIMARY KEY,
    namespace TEXT NOT NULL DEFAULT 'default',
    value_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    provider TEXT, model TEXT, strategy_version TEXT, prompt_version TEXT,
    market_data_version TEXT, metadata_json JSONB);
CREATE INDEX IF NOT EXISTS ix_cache_expires ON system.cache_entries (expires_at);
CREATE INDEX IF NOT EXISTS ix_cache_namespace ON system.cache_entries (namespace);

-- V3: Knowledge research (RAG) — documents + chunks with PostgreSQL full-text search.
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE TABLE IF NOT EXISTS knowledge.documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    symbol TEXT,
    doc_type TEXT NOT NULL DEFAULT 'other',
    source TEXT,
    publication_date DATE,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    extraction_version TEXT NOT NULL DEFAULT 'extract_v1',
    indexing_status TEXT NOT NULL DEFAULT 'pending',
    error_detail TEXT,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    char_count INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_docs_symbol ON knowledge.documents (symbol);
CREATE INDEX IF NOT EXISTS ix_docs_type ON knowledge.documents (doc_type);

CREATE TABLE IF NOT EXISTS knowledge.chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES knowledge.documents(id) ON DELETE CASCADE,
    symbol TEXT,
    seq INTEGER NOT NULL,
    page INTEGER,
    content TEXT NOT NULL,
    ts tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED);
CREATE INDEX IF NOT EXISTS ix_chunks_ts ON knowledge.chunks USING GIN (ts);
CREATE INDEX IF NOT EXISTS ix_chunks_doc ON knowledge.chunks (document_id);
CREATE INDEX IF NOT EXISTS ix_chunks_symbol ON knowledge.chunks (symbol);

-- V3: Historical strategy evaluation (backtest_v1).
CREATE SCHEMA IF NOT EXISTS backtest;
CREATE TABLE IF NOT EXISTS backtest.runs (
    id UUID PRIMARY KEY,
    identity TEXT NOT NULL,
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    interval TEXT NOT NULL,
    symbols TEXT[] NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    request JSONB NOT NULL,
    versions JSONB NOT NULL,
    assumptions JSONB NOT NULL,
    data_versions JSONB,
    coverage JSONB,
    metrics JSONB,
    equity_curve JSONB,
    skipped JSONB,
    open_trades JSONB,
    warnings JSONB,
    synthetic_data BOOLEAN NOT NULL DEFAULT false,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ);
CREATE INDEX IF NOT EXISTS ix_bt_identity ON backtest.runs (identity);
CREATE INDEX IF NOT EXISTS ix_bt_created ON backtest.runs (created_at DESC);
CREATE TABLE IF NOT EXISTS backtest.trades (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES backtest.runs(id) ON DELETE CASCADE,
    seq INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    exit_reason TEXT NOT NULL,
    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,
    net_pnl NUMERIC,
    r_net NUMERIC,
    detail JSONB NOT NULL);
CREATE INDEX IF NOT EXISTS ix_bt_trades_run ON backtest.trades (run_id, seq);

ALTER TABLE index_data.index_memberships ADD COLUMN IF NOT EXISTS retrieved_at TIMESTAMPTZ;
ALTER TABLE index_data.index_memberships ADD COLUMN IF NOT EXISTS verification_status TEXT NOT NULL DEFAULT 'unverified';
