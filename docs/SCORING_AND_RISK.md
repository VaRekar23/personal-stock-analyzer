# Scoring and Risk

## Scoring engine (`scoring/engine.py`, `scoring_v1`)
Input: list of `Factor(key, label, weight, value|None, detail)` where `value` is
normalized 0..100. Output: `ScoreResult`:
- **score** 0..100 — weighted average over **available** factors, with weights
  re-normalized across available factors so missing data neither inflates nor deflates.
- **confidence** 0..1 — fraction of intended total weight that had data.
  *Score and confidence are independent.* A stock can be `score=82, confidence=0.55`.
- **bias** — bullish (≥60) / neutral / bearish (≤40).
- **factors** — per-factor **centered contribution** (relative to neutral 50) for display.
- **missing** — labels of factors with no data. **No-data is never treated as a negative
  signal.**

## Strategy weights (`config/weights.yaml`)
- `long_term.group_weights`: fundamentals .30, growth .15, profitability .15, valuation .10,
  balance_sheet .10, cash_flow .05, technical_trend .10, sector_strength .03, market_context .02.
- `swing.factor_weights`: price_structure .18, market_trend .15, momentum .15, sector_trend .12,
  volume .12, support_resistance .10, relative_strength .10, volatility .08.
- `intraday.factor_weights`: vwap_position .18, nifty_direction .18, momentum .15,
  relative_volume .13, sector_direction .12, ema_alignment .12, opening_range .07, relative_strength .05.
These are **initial, documented, configurable** values — tune via file (defaults) or the
Settings page (thresholds/risk). Bump strategy version when changing scoring logic.

## Risk engine (`risk/engine.py`, `risk_v1`)
Deterministic hypothetical setups. **AI never sets prices.** Inputs: bias, current price,
ATR, support/resistance, risk config, mode. Output:
`direction, entry, entry_zone[lo,hi], stop_loss, target_1, target_2, risk_per_share,
reward_per_share_1/2, risk_reward_1/2, position_size, capital_required, risk_amount,
setup_validity, assumptions{...}`.

### Entry / stop / target logic
- Entry = current price; entry zone = price ± 0.25·ATR.
- LONG stop = price − stop_mult·ATR, clamped **below** nearby support (support − 0.1·ATR).
  SHORT stop = price + stop_mult·ATR, clamped above nearby resistance.
- Targets = price ± target_mult·ATR (T1, T2). All rounded to a 0.05 tick.
- R:R = reward/risk per share.

### Position sizing (configurable, no orders)
- `risk_amount = account_capital · risk_per_trade_pct/100`;
  `position_size = floor(risk_amount / risk_per_share)`; `capital_required = size · entry`.

### Default multipliers (Settings-editable)
- Swing: stop 1.5·ATR, T1 2.0·ATR, T2 3.5·ATR.
- Intraday: stop 1.0·ATR, T1 1.2·ATR, T2 2.0·ATR.
- Capital ₹10,00,000; risk 1.0%/trade (defaults; not personal advice).

`setup_validity`: `valid` (bias bullish/bearish + ATR present) or `no_setup` (neutral /
insufficient volatility) — never a fabricated setup.

## Versioning
`SCORING_VERSION`, `RISK_VERSION` in `core/versions.py`, persisted on each analysis run.
