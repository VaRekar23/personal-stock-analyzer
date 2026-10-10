# API Integrations

> Only facts verified in code/tests are listed. Provider classes existing ≠ live validation;
> credential-dependent checks are called out explicitly.

## Status summary (V3)
| Provider | Role | Implementation | Validation status |
|---|---|---|---|
| Zerodha / Kite Connect | Instruments, historical OHLCV, holdings, positions, quotes | `providers/zerodha/{live,client,session,instruments}.py` | Code complete. Needs the user's API key/secret plus a **daily** login token. Without a token the registry uses the MOCK provider (labelled). Backtest "Prepare data" refuses MOCK mode. |
| yfinance | Fundamentals + news | `providers/yfinance_*` | Live, no key. Current snapshot only (no point-in-time). Personal use; no redistribution. Symbol-specific news precision is limited. |
| OpenAI | AI explanation / research synthesis | `ai/openai_provider.py` | Needs `OPENAI_API_KEY` with credit. As of 2026-10-10 the configured key returned `credit_balance_exhausted`. |
| Gemini | AI fallback | `ai/gemini_provider.py` | Live, verified end-to-end for research answers. |
| PostgreSQL FTS | Document retrieval | `providers/knowledge.py` | Local, no external API, no cost. |
| Mock | Development fallback | `providers/mock/*` | Always labelled `source=mock` / SYNTHETIC. |

## Zerodha historical limits used by backtest data preparation
Chunked requests per call: `day` 2000 days, `15minute` 200 days, `5minute` 100 days, about 3 requests/s
(`backtest/service.py: KITE_CHUNK_DAYS`). Only missing leading/trailing ranges are fetched. Candles are **unadjusted**.
No WebSocket streaming, no continuous polling, no order placement.

## AI usage policy
- AI is never called for indicators, scores, trade levels or inside backtest loops.
- Research: one AI call per uncached question, on bounded evidence (≤8 chunks).
- Retrieved document text is treated as untrusted evidence (prompt-injection guard).

## Credentials (server-side env only)
`ZERODHA_API_KEY`, `ZERODHA_API_SECRET` (+ daily token via UI), `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`.

## Data provenance / licensing
- NIFTY 50 membership seed (`source='seed:nse_current'`) is **unverified** current membership, not point-in-time history.
  `verification_status` is stored per row. Verified records can be imported via `POST /api/index-memberships/import`
  (CSV + mandatory source). Automated scraping of NSE archives is **not** implemented (access restrictions).
- Uploaded documents are stored only in your PostgreSQL. No third-party document sources are scraped.
