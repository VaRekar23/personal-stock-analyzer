# Analysis Engine

## Technical indicators (`indicators/engine.py`, `technical_v1`)
All deterministic (NumPy). `compute_features()` returns a structured dict:
`last_price, sma50, sma200, ema20/50/200, rsi(14), macd{macd,signal,histogram},
atr(14), vwap (intraday), supertrend, bollinger{upper,middle,lower}, pivots{p,r1,s1,r2,s2},
relative_volume, support_resistance{support,resistance}, week52{high,low,position_pct},
trend (uptrend/downtrend/sideways)`. Missing inputs → `None` (never fabricated).

## Context engines (`context/engines.py`)
- **MarketContextEngine**: NIFTY & BANKNIFTY direction/trend/RSI (index proxies in mock),
  breadth (risk-on/mixed/risk-off).
- **SectorContextEngine**: per-sector direction from peer constituents; explicit
  sector→index mapping (`data/nifty50.SECTOR_INDEX`).

## Strategies (three separate engines)
Weights are configurable in `config/weights.yaml` (not hard-coded in strategy code).

### Long term (`long_term_v1`)
Group-weighted blend of fundamentals, growth, profitability, valuation, balance sheet,
cash flow, long-term technical trend (50/200 DMA + 52-week position), sector strength,
market context. Fundamentals-heavy. No trade setup (investing horizon).

### Swing (`swing_v1`)
Factor-weighted: market trend, sector trend, price structure / EMA alignment,
momentum (RSI band + MACD histogram), relative volume, S/R position, volatility (ATR%),
relative strength. Produces score + bias; Risk Engine builds swing setup.

### Intraday (`intraday_v1`)
Separate factor set: NIFTY direction, sector direction, VWAP position, EMA alignment,
momentum (RSI band), relative volume, opening range, relative strength. Uses 15m candles;
Risk Engine builds intraday setup with tighter ATR multipliers.

## Feature normalization (`strategies/base.py`)
- `linear(v, low, high)` → 0..100; `inverse_linear` (lower is better, e.g. valuation/debt);
  `band(v, ideal_lo, ideal_hi, hard_lo, hard_hi)` (e.g. RSI sweet spot);
  `direction_score` (bullish/neutral/bearish → 100/50/0). `None` propagates (missing data).

## Portfolio health rules (`analysis/portfolio.py`)
Documented, deterministic (not AI):
- P&L% < −8% → **Review**; −8%..−3% → **Watch**.
- Swing bias bearish & score < 45 → **Review**; neutral structure → **Watch**.
- Otherwise **Healthy**. Reasons are surfaced in the UI (tooltip).

## Versioning
All versions live in `core/versions.py`. Changing logic materially → bump version
(e.g. `swing_v1`→`swing_v2`), never silently replace. Stored on every `analysis_run`.
