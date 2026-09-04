# AI Architecture

## Abstraction
```
AIService (ai/service.py)
   → AIProvider (Protocol in providers/base.py)
       → MockAIProvider (ai/mock_provider.py)   [V1]
       → OpenAIProvider / Anthropic / Gemini      [future, drop-in]
```
The rest of the app never imports a concrete AI SDK. Adding a provider = implement
`generate(prompt, context, response_schema) -> dict` and register in
`providers/registry.ai_provider()`.

## Responsibilities
- **Deterministic layer (authoritative):** all numbers — indicators, scores, confidence,
  entry/stop/targets, R:R, position size.
- **AI layer:** concise conclusion, bullish/bearish factors, key risks, reasoning,
  trade-setup explanation, invalidation conditions, missing-data warnings.
- If AI ever contradicts a deterministic value, the deterministic value wins (and EVALS
  flags the contradiction).

## Structured output (`ai/schemas.py`)
`AIAnalysis`: `bias(LONG/SHORT/NEUTRAL)`, `confidence(0..1)`, `summary`,
`bullish_factors[]`, `bearish_factors[]`, `risks[]`, `invalidation_conditions[]`,
`setup_commentary`, `missing_data_warnings[]`, provenance (`provider/model/prompt_version/grounded`).
Validated with Pydantic in `AIService` before caching; invalid output is rejected.

## Prompts (`ai/prompts.py`, versioned)
- `SYSTEM_GROUNDING`: forbids inventing prices/indicators/news; requires "data unavailable"
  when a fact is absent; research language only; deterministic levels authoritative.
- Per-type templates: `longterm_analysis_v1`, `swing_analysis_v1`, `intraday_analysis_v1`.
- The MockAIProvider is grounded **by construction**: it only re-states numbers already in
  the supplied context (score, factor contributions, Risk Engine levels), so factual
  consistency holds without spending credits.

## Model/provider configuration
Centralized in `core/config.py` (`AI_PROVIDER`, `AI_MODEL`). Never hard-coded across the
codebase. Stored per analysis in `analysis.analysis_runs` (`provider`, `model`, `prompt_version`).

## Cache keys (`ai/service.make_cache_key`)
Hash of: `symbol | analysis_type | date_context | market_data_version | strategy_version
| prompt_version | provider | model`. Guarantees swing/intraday/long-term cache separately
and that unchanged effective input is never re-billed. Backed by Redis + `ai_analyses` table.

## Cost control
AI is never the first stage. Scanner runs AI only on top-N finalists above a score
threshold (Settings-tunable). Single-stock analysis calls AI once and caches aggressively.
