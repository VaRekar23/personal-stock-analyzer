# API Integrations

> **Rule:** Only document facts verified from official/current provider docs. Never
> invent endpoints, parameters, auth or response fields. Until verified, an adapter is
> marked **"Provider adapter pending verification"** and a MOCK provider is used.

## Status summary (this build)
| Provider | Role | Status | Implementation |
|---|---|---|---|
| Zerodha / Kite Connect | Instruments, historical OHLCV, holdings, positions, quotes | **PENDING VERIFICATION** | `providers/zerodha/client.py` raises `ProviderPendingError`; MOCK used |
| TrueData | Fundamentals + News | **PENDING VERIFICATION** | interface only; MOCK used |
| OpenAI | AI explanation | **NOT CONFIGURED** | `AIProvider` abstraction; MockAIProvider used |
| Internal Mock | All of the above | ACTIVE | Deterministic, `source=mock`, labelled DEMO/MOCK in UI |

No live external calls are made in this build. All data is deterministic mock data.

## Zerodha / Kite Connect (to verify before going live)
- Official docs: https://kite.trade/docs/connect/v3/
- Auth: API key + secret → request token (login flow) → **access token** (daily). Server-side only.
- Endpoints we intend to use (verify exact paths/params/limits against docs before coding):
  instruments dump; historical candles (per instrument_token + interval + from/to, with
  provider-imposed range limits per interval); holdings; positions; quotes/LTP.
- Rate limits, historical-range caps and interval availability **must be read from the
  live docs** and encoded in the adapter. Implement retries (transient), timeouts,
  rate-limit backoff, structured errors, incremental fetch, duplicate protection.
- **Do NOT** implement WebSocket streaming or continuous polling in V1. Intraday data is
  fetched only on explicit user request.

## TrueData (Fundamentals + News — to verify)
- Confirm subscription, base URL, auth mechanism, exact endpoints, response schema, and
  which requested fields are actually available BEFORE implementing. Record findings here.
- Required fundamental fields (target): income statement (revenue, growth, EBITDA/EBIT,
  PAT, EPS, margins), balance sheet (assets, equity, debt, cash, net debt, WC), cash flow
  (OCF, capex, FCF), valuation (P/E, P/B, ROE, ROCE, D/E, dividend yield, margins),
  ownership (promoter/FII/DII/public), corporate actions (dividend/bonus/split/rights).
- News fields (target): source, headline, published time, url, symbol, retrieved time,
  category/sentiment (only if reliably provided).

## OpenAI (AI provider — to configure)
- Add `OPENAI_API_KEY` (server-side). Implement an `OpenAIProvider` conforming to the
  `AIProvider` Protocol (`generate(prompt, context, response_schema)`), register in
  `providers/registry.ai_provider()`. Model/temperature/token settings centralized in
  config. Nothing else in the app changes.

## Credentials required (env, never in frontend)
`ZERODHA_API_KEY`, `ZERODHA_API_SECRET`, `ZERODHA_ACCESS_TOKEN`,
`FUNDAMENTAL_API_KEY`, `NEWS_API_KEY`, `OPENAI_API_KEY`. See `.env.example`.

## Data provenance
- Historical NIFTY 50 membership: seeded from the current NSE constituent list with
  `source='seed:nse_current'` and `valid_from=2024-01-01`. **This is a labelled seed, not
  verified point-in-time history.** Replace via a documented import (NSE archives) in V2.
