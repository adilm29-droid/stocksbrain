# StocksBrain v2

Daily portfolio signal engine. Fetches live prices, analyst targets, insider activity, and macro data, then scores each holding and produces a human-readable briefing.

## Quick start

```bash
pip install -r requirements.txt
python orchestrator.py          # full daily run
python quick_check.py           # fast price + RSI table only
```

Windows: double-click `daily_stocks.bat`  
Linux/Mac: `bash daily_stocks.sh`

## Output

- `output/briefing.txt` — human-readable daily briefing  
- `output/dashboard.json` — full structured data (holdings, macro, risk flags)

## Holdings

Configured in `config.py` — equities, core ETFs (SPUS/URTH/HLAL), crypto, and commodities. Autopilot portfolios (Cybersecurity, FATMAA, Architects of AI, Dividend Stocks) are tracked by value only.

## Signal scoring

Each holding scores –5 to +5 based on RSI, analyst upside, insider buying, news sentiment, and macro sector rotation. Decision thresholds: BUY (≥3), HOLD (0–2), TRIM (−1 to −2), SELL (≤−3). Core ETFs are protected from SELL/TRIM.

## GitHub Actions

`.github/workflows/daily_run.yml` runs at 22:00 UTC Mon–Fri and commits the output.
