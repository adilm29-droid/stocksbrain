# StocksBrain v2 — Signal Scoring Rules

## Overview

Every holding is scored on a scale of **-5 (strong sell) to +5 (strong buy)** each run. Signals are accumulated, overlays are applied, and a final decision with a one-line output is produced.

---

## BUY Signals (+1 each)

| Signal | Condition |
|---|---|
| RSI Healthy Pullback | RSI < 35 AND price > 200-day MA |
| Analyst Upside | Analyst consensus target implies >15% upside |
| Insider Buying | Insider net buying via Form 4 in last 90 days (OpenInsider) |
| Earnings Beat + Guidance Raise | Last quarterly earnings beat AND guidance was raised |
| Sector Rotation Favorable | Current macro environment is a tailwind for this sector |

---

## SELL / TRIM Signals (-1 each)

| Signal | Condition |
|---|---|
| Overbought (RSI) | RSI > 70 |
| P/E Doubled | Current P/E has doubled relative to P/E at user's entry price |
| Analyst Consensus Weak | Analyst target implies < 5% upside, or negative upside |
| Concentration Risk | Position size > 7% of total portfolio value |
| Thesis Break | Any of: guidance cut, CEO resignation/departure, product failure, regulatory probe/hit, SEC action |
| Big Gain + Any Sell Signal | Stock is up > 50% from cost basis AND at least one of the above sell signals is present |

---

## Decision Table

| Score | Decision |
|---|---|
| +3 to +5 | **BUY** (add on dip) |
| +1 to +2 | **HOLD** |
| 0 | **HOLD**, watch closely |
| -1 to -2 | **TRIM** 20–30% |
| -3 to -5 | **SELL** (thesis broken) |

---

## Overlays (applied AFTER scoring)

These override the decision table output:

1. **Autopilot portfolio overlay**: If the holding is in an autopilot portfolio (not a directly held ticker), downgrade SELL → HOLD. TRIM is only applied if the position is also held directly.

2. **Earnings in next 7 days**: Downgrade ALL decisions to HOLD regardless of score. Too uncertain to act.

3. **Low cash buffer**: If total portfolio cash is below 5%, any BUY signal becomes "add on dip below $X" language — not "buy now." This prevents over-deployment.

4. **Core ETF protection**: Tickers SPUS, URTH, HLAL are never sold. Maximum output is HOLD. BUY is still allowed.

---

## Output Format (one line per stock)

Each holding gets exactly one of these output lines:

```
✅ HOLD — [one sentence explaining why]
⚠️ TRIM 25% — [one sentence why + suggested price level]
🔴 SELL — [one sentence why, thesis-break reason]
💰 BUY on dip below $X — [one sentence why]
```

---

## Holdings Scored Every Run

**Equities:** AMD, AMZN, KO, META, MSFT, NKE, NVDA, PLTR, TSLA, UNH

**Core ETFs (never sell):** SPUS, URTH, HLAL

**Crypto:** BTC-USD, ETH-USD, XRP-USD, SOL-USD

**Commodities:** GLD (Gold), SLV (Silver)

**Autopilot Portfolios (scored with overlay, not real tickers):**
- Cybersecurity
- FATMAA
- Architects of AI
- Dividend Stocks

---

## Data Sources Used

- **Prices / Technicals**: yfinance (RSI, MACD, SMA50, SMA200)
- **Analyst data**: yfinance `.info` (targetMeanPrice, recommendationMean)
- **Insider activity**: OpenInsider Form 4 scraper (90-day window)
- **News / Thesis-break**: Yahoo Finance RSS feed, keyword scanning
- **Macro**: yfinance (VIX, DXY, 10Y yield, Oil, Gold, SP500 200-day trend)
- **Options flow**: yfinance options chain (put/call ratio)
- **Politician trades**: Capitol Trades (non-critical, best-effort)
- **Whale / Institutional**: SEC EDGAR 13F-HR filings

---

## Sector Rotation Heuristic

- VIX < 20 AND SP500 above 200-day MA → Tech/Growth FAVORABLE, Defensive NEUTRAL
- VIX > 25 → Defensive FAVORABLE, Tech/Growth UNFAVORABLE
- Otherwise → NEUTRAL across sectors

---

## Risk Flags Checked Separately

- Any position > 7% of portfolio
- Tech sector > 40% of portfolio
- Crypto > 10% of portfolio
- Any position down > 50% from cost basis
- Cash buffer < 5% of total portfolio
