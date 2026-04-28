# StocksBrain v2

**Decision support for a diversified, halal-compliant portfolio. Not a money printer.**

This system analyses 13 data signals across 9 institutional frameworks to produce daily BUY / HOLD / TRIM / SELL signals for Adil's personal portfolio. Signals are decision aids — every trade still requires human judgment.

---

## What this system does NOT do

- It does not day-trade, scalp, or leverage.
- It does not follow YouTube analysts or social-media hype.
- It does not predict short-term price movements — no one can.
- It does not override halal compliance for any reason.
- It does not guarantee alpha. The backtest hit rate is published below, unfiltered.

---

## Iron Rules

1. **Halal first.** Tickers not in the AAOIFI/SPUS/HLAL whitelist cannot receive a BUY signal, regardless of other indicators.
2. **Kelly ≤ 25% of full Kelly, capped at 5%.** Never size up past 5% of portfolio on any single signal.
3. **Earnings freeze.** No new trades 7 days before any held ticker reports.
4. **Cash buffer ≥ 5%.** No new positions when cash < 5% of portfolio.
5. **Core ETFs never SELL/TRIM.** SPUS, HLAL, URTH are forever-hold positions.

---

## Backtest Results

> Auto-updated every Sunday by `weekly_backtest.yml`.

<!-- BACKTEST_TABLE_START -->
| Metric | Value |
|--------|-------|
| Hit Rate | — |
| Avg 30d return per BUY signal | — |
| SPUS buy-and-hold (same period) | — |
| Max drawdown | — |
| Signals evaluated | — |
<!-- BACKTEST_TABLE_END -->

**If hit rate < 52% or strategy underperforms SPUS, the system prints a warning in the workflow logs and in `backtest/results.json`.** We do not hide underperformance.

---

## Signal Accuracy (Journal)

> Auto-updated weekly from `logs/accuracy.jsonl`.

<!-- ACCURACY_TABLE_START -->
| Metric | Value |
|--------|-------|
| Entries evaluated | — |
| 30d accuracy | — |
<!-- ACCURACY_TABLE_END -->

---

## Data Sources (13 factors)

| # | Source | Signal type |
|---|--------|-------------|
| 1 | yfinance RSI + 200MA | Technical momentum |
| 2 | Analyst consensus + upside | Price target |
| 3 | Insider transactions | Smart money |
| 4 | News sentiment | Market narrative |
| 5 | Options flow (put/call) | Derivatives signal |
| 6 | Macro (VIX, DXY, 10Y yield) | Risk environment |
| 7 | Sector rotation | Macro allocation |
| 8 | Earnings calendar | Event risk |
| 9 | GDELT geopolitics | Tail risk tone |
| 10 | FRED (yield curve, CPI, FFR) | Rate environment |
| 11 | USAspending.gov | Government tailwind |
| 12 | Insider cluster detection | Conviction signal |
| 13 | EWMA/Kronos volatility | Position sizing |

---

## Institutional Frameworks

AQR Value-Momentum · Berkshire Moat · BlackRock Factor · Bridgewater Risk Parity ·
Citadel Mean Reversion · GS Sustain · JPM Earnings Surprise · Renaissance Pattern ·
Two Sigma Alt Data

---

## Known Limitations

- **Kronos**: zero-shot transformer vol forecasts have not been validated in live trading. Used only for position sizing, never for direction.
- **GDELT lag**: sentiment reflects articles from the past 7 days, not real-time.
- **Regime risk**: all signals are calibrated for normal markets. They degrade during structural regime changes (2008, 2020-style shocks).
- **No real-time price feed**: prices update once daily via yfinance. Intraday signals are not reliable.
- **Halal screening**: relies on SPUS/HLAL whitelist as a proxy. Individual stocks may have changed business activities since last ETF rebalance.

---

## Running Locally

```bash
pip install -r requirements.txt
python orchestrator.py          # Daily signal run
python backtest/replay.py       # Historical validation
python evaluate_journal.py      # Journal accuracy update
```

Environment variables (optional):
- `FRED_API_KEY` — enables FRED macro pull (free at fred.stlouisfed.org)
- `RESEND_API_KEY` — enables email alerts (free tier: 3000/mo)
- `ALERT_EMAIL` — destination for alerts (default: adilm29@gmail.com)

---

## Automated Pipelines

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| `daily_run.yml` | Weekdays 5:30 UTC | Full signal run + pushes `output/dashboard.json` |
| `health_check.yml` | Every 4h | Checks freshness, opens issue if stale >36h |
| `weekly_backtest.yml` | Sundays 6:00 UTC | Reruns backtest, evaluates journal accuracy |

---

*This system uses 13 data inputs + 9 institutional frameworks. No single one beats the market. Together they tilt the odds — that's the real edge. Anyone promising more is selling something.*
