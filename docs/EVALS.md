# EVALS

Vendor-independent evaluation framework. Files: `evals/framework.py` (graders),
`evals/datasets.py` (datasets + runner). Data model in `evaluation` schema.

## Two categories
### A. AI EVALS
Graders in `framework.grade_ai_output(ai, context)`:
- **schema_validity** — output validates against `AIAnalysis`.
- **deterministic_consistency** — AI bias == mapped deterministic bias; AI confidence ==
  score confidence (±0.01).
- **factual_consistency** — any trade-level numbers the AI states must match the Risk
  Engine's authoritative values. (E.g. AI "Entry 1400" vs engine 1432 → fail.)
- **grounding** — if the score has missing factors, the AI must surface missing-data warnings.
- **completeness** — required sections present (summary, bias, at least one factor list).

### B. Strategy EVALS (V3 — implemented, separate from AI EVALS)
Deterministic checks of the backtester's accounting on **SYNTHETIC** hand-built OHLC fixtures
(`backtest/fixtures.py`, 21 cases with mathematically defined expectations). Run via
`GET /api/evals/strategy`, the Backtesting page "Strategy EVALS" panel, and `tests/test_backtest.py`.
Covers entry/stop/target outcomes, same-bar ambiguity, gaps, costs, unresolved trades, T2 counterfactual,
next-candle execution, no look-ahead, determinism, Risk-Engine level parity, warm-up, missing data,
membership eligibility and small-sample metrics. Details: `STRATEGY_EVALUATION.md`.
AI quality scores and trading results are never mixed.

## Datasets (seeded at startup)
- `ai_synthetic_v1` — synthetic hallucination-detection cases (labelled **synthetic**):
  - `syn_rsi_consistency_pass` — AI restates RSI 67.2 correctly → grader passes → suite pass.
  - `syn_rsi_consistency_fail` — AI claims RSI 42 vs deterministic 67.2 → grader fails →
    suite **passes** (it correctly caught the hallucination).
  - `syn_entry_override_fail` — AI entry 1400 vs Risk Engine 1432 → caught.
- `ai_live_pipeline_v1` — runs the real deterministic pipeline for a sample of symbols and
  grades the (grounded) AI output.

> A synthetic case "passes the suite" when the grader's verdict matches the case's
> `expected_output.passed`. This validates that the grader detects hallucinations.

## Runner (`run_evals(sample_size)`)
Executes synthetic + live cases, writes an `eval_runs` row and per-case `eval_results`,
returns pass/fail/total/pass_rate/avg_score. Exposed at `POST /api/evals/run`;
latest run + datasets + cases at `GET /api/evals/latest`. UI: EVALS page.

## Every eval case records
`case_id, input, expected_output, evaluation_type, created_at, version`. Synthetic data is
clearly labelled and never treated as real-world truth.

## Adding a new EVAL case
Add to `SYNTHETIC_AI_CASES` (or create a new dataset) in `evals/datasets.py`, extend
`seed_datasets()`, and (if needed) add a grader in `framework.py`. Bump dataset `version`.
