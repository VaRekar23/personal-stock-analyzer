# Strategy Evaluation (Backtesting) — `backtest_v1`

Deterministic historical replay of the **existing** swing/intraday strategies and Risk Engine.
It measures how setups would have played out. It is **not** an optimizer and not proof that a strategy works.
Strategy evaluation is kept **separate from AI EVALS**: a profitable backtest says nothing about AI explanation quality, and the reverse is also true.

Code: `backend/stockai/backtest/` — `engine.py` (replay + fills/exits), `metrics.py`, `quality.py` (coverage),
`service.py` (data, identity, jobs), `fixtures.py` (synthetic strategy EVALS). UI: `/backtesting`.

## Scope (V3)
| Mode | Intervals | Status |
|---|---|---|
| Swing (`swing_v1`) | `1d` | Supported |
| Intraday (`intraday_v1`) | `15m`, `5m` (only where stored intraday candles exist; daily data is never interpolated) | Supported |
| Long-term | — | DEFERRED: no point-in-time fundamentals (yfinance is current-only) |
| Index-wide universe | — | DISABLED until verified point-in-time membership is imported |

Limits: ≤10 symbols per run. Max range: 1d 3650 days, 15m 365 days, 5m 180 days.

## Execution model (stored with every run as `assumptions`)
1. **Signal timing**: the decision at bar *i* is computed at bar *i*'s **close**, using only `candles[:i+1]`
   (a rolling window equal to the live engine's: 1d 400, 15m 260, 5m 300 bars). Warm-up: 60 bars.
2. **Levels**: `risk.engine.build_setup` (risk_v1) produces direction, entry, entry zone, stop, T1, T2.
   The backtester never invents levels. The setup must satisfy `stop < entry < T1 ≤ T2` (LONG; mirrored for SHORT),
   otherwise `invalid_setup`. A neutral bias means `no_setup` (counted, not a trade).
3. **Entry conversion (limit at zone edge, next bar only)**: LONG buy-limit at `zone_high`:
   if next open ≤ zone_high, fill at **open**; else if next low ≤ zone_high, fill at **zone_high** (`limit`);
   otherwise `entry_not_triggered`. If the fill is at or beyond the stop, `opened_beyond_stop` (skipped). SHORT mirrors this at `zone_low`.
4. **Exit**: full exit at **Target 1**. Target 2 is a **counterfactual only**: after a T1 exit, "would T2 have been hit
   before the stop within the holding horizon?" (stop-first on the same bar).
5. **Conservative intra-bar rules**:
   - Stop and T1 both inside one bar: **stop first** (`ambiguous=true` is recorded).
   - On a `limit`-fill entry bar the order of events is unknown, so targets on that bar are ignored. A stop on that bar counts (ambiguous).
   - Later bar opens through the stop: exit at the **open** (`stop_gap`, worse than stop).
   - Later bar opens through T1: exit at the **T1 price** (`target_1_gap`, no gap bonus).
6. **Time exits**: swing has max 20 bars held (`time_exit` at that bar's close). Intraday exits at the session's last bar close
   (`session_end`). There are no intraday entries in the last 2 bars of a session and no overnight holds.
7. **Unresolved**: a trade still open at the end of the data is marked to the last close and reported as **open**. It is excluded from all metrics.
8. **One position per symbol** at a time. After an exit, the next decision is evaluated at the exit bar's close.
9. **Sizing**: fixed-fractional on **initial** capital (no compounding): `qty = min(floor(capital·risk%/risk_per_share), floor(capital/entry))`.
   `qty = 0` gives `position_size_zero`. Positions across symbols are independent; the shared-capital constraint is **not modelled**.
10. **Costs/slippage**: `slippage_bps` is applied adversely to entry and exit. `cost_bps_per_side` is charged on entry and exit notional.
    If both are 0 the run carries the warning *"results are GROSS, not net tradable performance"*.
11. **Context**: the market factor uses the same RELIANCE proxy the live engine uses, sliced point-in-time
    (swing: daily candles ≤ T; intraday: only fully completed prior days). The **sector factor is excluded**
    (weights renormalise over available factors, the same as live missing-data handling). So backtest scores can differ from live scores.

## Data integrity
- Backtests run on **stored candles only**. "Prepare data" fetches only the missing leading/trailing ranges from Zerodha,
  chunked (1d 2000 days, 15m 200 days, 5m 100 days per request, about 3 requests/s). It refuses to run in MOCK mode. Interior gaps are reported, not back-filled.
- Pre-run coverage (`POST /api/backtests/coverage`) reports, per symbol: `bars`, `warmup_bars`, `first`/`last`, `duplicates`,
  `gap_count`/`gaps`, `partial_sessions`, `invalid_ohlc`, `discontinuities` (>20% open vs prior close, i.e. possible unadjusted split/bonus),
  `sources`, `synthetic`, `price_adjustment`, `warnings`.
- **Prices are unadjusted.** Zerodha historical candles are not split/bonus adjusted, and the system never assumes they are.
- **Synthetic/mock candles** (`source` = mock/synthetic) make the run `synthetic_data=true`, shown with a red
  "NOT a real historical backtest" banner.
- **Membership**: `index_data.index_memberships` has `verification_status` + `retrieved_at`. The existing seed is
  *unverified*. `POST /api/index-memberships/import` (CSV `index_name,symbol,valid_from,valid_to` + mandatory `source`)
  records user-supplied official records. Index-wide runs stay disabled in V3. The engine supports `eligible(T)` for point-in-time
  membership filtering (fixture-tested).

## Metrics (closed trades only; `net` includes slippage + costs)
| Metric | Definition |
|---|---|
| total_trades | Closed (resolved) trades |
| winning / losing / breakeven | net_pnl > 0 / < 0 / = 0 |
| win_rate | winning / total (null if 0 trades) |
| gross_pnl | Σ direction·(exit − entry)·qty at raw fill prices |
| net_pnl | Σ direction·(exit_eff − entry_eff)·qty − costs |
| avg_return_pct | mean(net_pnl / (entry·qty)) × 100 |
| R (per trade) | r_gross = direction·(exit − entry)/risk_per_share; r_net = net_pnl/(qty·risk_per_share), with risk_per_share = abs(fill − stop) |
| avg_r / expectancy_r | mean(r_net). Expectancy in R = average net R per closed trade |
| profit_factor | Σ net wins / abs(Σ net losses); **null** with note when there are no losing trades |
| max_drawdown (₹, %) | Largest peak-to-trough fall of the closed-trade equity curve (initial capital + cumulative net P&L, in exit-time order) |
| avg_holding_bars | Mean bars from the entry bar to the exit bar inclusive |
| target_1_hit_rate | Share of trades exiting via target_1 / target_1_gap |
| target_2_hit_rate | Share of trades whose T2 counterfactual was reached |
| stop_loss_hit_rate | Share exiting via stop_loss / stop_gap |
| open_trades | Unresolved at the end of the window (excluded above) |
| skipped_trades / skipped_by_reason | entry_not_triggered, opened_beyond_stop, invalid_setup, position_size_zero |
| no_setup_decisions, decisions_evaluated | Bars evaluated / bars with neutral or no setup |
| sample_warnings | 0 trades: "no statistics". Fewer than 30 trades: "Insufficient sample — not statistically reliable" |

## Jobs, reproducibility, caching
- `backtest.runs` (status queued→running→completed|failed, heartbeat) + `backtest.trades`. Execution is an in-process
  `asyncio` task (CPU work in a thread). There is no queue, no Redis and no always-on worker. Runs with no heartbeat for 10 min are marked failed.
- **Identity** = sha256(normalised request + assumptions + versions {backtest, strategy, indicator, scoring, risk, risk-config
  hash, weights hash} + per-symbol data versions {count, first/last ts, Σclose}). An identical identity reuses the stored run
  (`reused: true`). Any change to data, versions, config or assumptions creates a new run.
- Cloud Run note: background CPU after the response requires **CPU always allocated** (`--no-cpu-throttling`), otherwise runs crawl.

## Strategy EVALS (synthetic fixtures)
`GET /api/evals/strategy` and `tests/test_backtest.py` run 21 labelled-SYNTHETIC cases with exact expected outcomes:
entry → T1, entry → stop, same-bar stop+target, entry never triggered, opened beyond stop, invalid/neutral setup, stop
gap, costs reduce net (exact formula), unresolved at end, T2 counterfactual (and stop-first), limit-fill bar ignores
target, time exit, SHORT target, next-candle execution, **no look-ahead** (changing future candles leaves all earlier
trades identical), determinism, levels identical to Risk Engine output, insufficient warm-up, missing-candle detection,
membership eligibility, zero/small-sample metrics.

## Explicitly not done
No weight optimization, parameter search, walk-forward or "validated" labels. One period's result is not validation.
