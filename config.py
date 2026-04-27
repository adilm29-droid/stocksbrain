HOLDINGS = {
    # Equities
    "AMD":  {"shares": 3.32560237, "avg_cost": 174.16, "bucket": "equity", "sector": "Technology"},
    "AMZN": {"shares": 7.35181268, "avg_cost": 224.15, "bucket": "equity", "sector": "Consumer Discretionary"},
    "KO":   {"shares": 1.41585302, "avg_cost": 70.63,  "bucket": "equity", "sector": "Consumer Staples"},
    "META": {"shares": 0.55467511, "avg_cost": 631.00, "bucket": "equity", "sector": "Technology"},
    "MSFT": {"shares": 1.45468479, "avg_cost": 514.75, "bucket": "equity", "sector": "Technology"},
    "NKE":  {"shares": 10.56899598,"avg_cost": 62.25,  "bucket": "equity", "sector": "Consumer Discretionary"},
    "NVDA": {"shares": 10.17663281,"avg_cost": 170.89, "bucket": "equity", "sector": "Technology"},
    "PLTR": {"shares": 7.08551806, "avg_cost": 162.83, "bucket": "equity", "sector": "Technology"},
    "PEP":  {"shares": 0.68190124, "avg_cost": 146.65, "bucket": "equity", "sector": "Consumer Staples"},
    "SPOT": {"shares": 0.29083350, "avg_cost": 687.68, "bucket": "equity", "sector": "Technology"},
    "SSTK": {"shares": 24.02652532,"avg_cost": 20.81,  "bucket": "equity", "sector": "Technology"},
    "TSLA": {"shares": 3.20773912, "avg_cost": 326.12, "bucket": "equity", "sector": "Consumer Discretionary"},
    "HNST": {"shares": 131.27494223,"avg_cost": 3.81,  "bucket": "equity", "sector": "Consumer Staples"},
    "UNH":  {"shares": 4.94367806, "avg_cost": 305.27, "bucket": "equity", "sector": "Healthcare"},
    "V":    {"shares": 0.29801924, "avg_cost": 335.55, "bucket": "equity", "sector": "Financials"},
    # Core ETFs
    "SPUS": {"shares": 60.95569328,"avg_cost": 52.38,  "bucket": "core_etf", "sector": "ETF"},
    "URTH": {"shares": 5.34159500, "avg_cost": 187.21, "bucket": "core_etf", "sector": "ETF"},
    "HLAL": {"shares": 16.03849238,"avg_cost": 62.35,  "bucket": "core_etf", "sector": "ETF"},
    # Commodities (yfinance futures tickers)
    "GC=F": {"shares": 0.51789,    "avg_cost": 4510.57,"bucket": "commodity", "sector": "Precious Metals"},
    "SI=F": {"shares": 21.74808,   "avg_cost": 72.86,  "bucket": "commodity", "sector": "Precious Metals"},
    # Crypto (yfinance format)
    "BTC-USD": {"shares": 0.01466495, "avg_cost": 96555.0, "bucket": "crypto", "sector": "Crypto"},
    "ETH-USD": {"shares": 0.42399581, "avg_cost": 3133.6,  "bucket": "crypto", "sector": "Crypto"},
    "XRP-USD": {"shares": 637.18524387,"avg_cost": 2.222,  "bucket": "crypto", "sector": "Crypto"},
    "SOL-USD": {"shares": 9.38194714, "avg_cost": 140.52,  "bucket": "crypto", "sector": "Crypto"},
}

AUTOPILOT_PORTFOLIOS = {
    "Cybersecurity": {"total_value": 5397.87, "total_cost": 5800},
    "Architects of AI": {"total_value": 6012.93, "total_cost": 5800},
    "FATMAA": {"total_value": 5956.48, "total_cost": 5800},
    "Dividend Stocks": {"total_value": 6193.79, "total_cost": 5800},
}

CORE_ETF_TICKERS = {"SPUS", "URTH", "HLAL"}

# Cash buffer config (USD)
CASH_BUFFER_TARGET_USD = 1500.0
CASH_BUFFER_MIN_USD = 500.0
CASH_BUFFER_PCT_MIN = 3.0  # % alert threshold

WATCHLIST = ["GOOG", "AAPL", "BRKB", "SCHD", "VTI"]

# Halal-screened universe (SPUS + HLAL + Wahed approved)
HALAL_APPROVED = {
    "SPUS", "HLAL", "URTH", "AMZN", "MSFT", "NVDA", "META", "GOOGL", "AAPL",
    "TSLA", "AMD", "PLTR", "V", "KO", "PEP", "NKE", "UNH", "SPOT", "SSTK",
    "HNST", "BTC-USD", "ETH-USD", "GC=F", "SI=F",
}

THRESHOLDS = {
    "rsi_oversold": 35,
    "rsi_overbought": 70,
    "analyst_upside_buy": 15.0,
    "analyst_upside_sell": 5.0,
    "concentration_cap": 7.0,
    "gain_trim_threshold": 50.0,
    "crypto_alt_max_pct": 2.0,
    "crypto_total_max_pct": 12.0,
    "single_stock_max_pct": 7.0,
    "moonshot_total_max_usd": 2500.0,
    "moonshot_single_max_pct": 1.5,
}

# Earnings dates (updated 2026-04-27) — 3-source verified
# Format: ticker -> {"date": "YYYY-MM-DD", "timing": "BMO/AMC", "reported": bool}
EARNINGS_CALENDAR = {
    "MSFT": {"date": "2026-04-29", "timing": "AMC", "reported": False},
    "GOOGL": {"date": "2026-04-29", "timing": "AMC", "reported": False},
    "META": {"date": "2026-04-29", "timing": "AMC", "reported": False},
    "AMZN": {"date": "2026-04-29", "timing": "AMC", "reported": False},
    "TSLA": {"date": "2026-04-22", "timing": "AMC", "reported": True},
    "UNH":  {"date": "2026-04-21", "timing": "BMO", "reported": True},
    "AMD":  {"date": "2026-05-05", "timing": "AMC", "reported": False},
    "NVDA": {"date": "2026-05-28", "timing": "AMC", "reported": False},
    "PLTR": {"date": "2026-05-05", "timing": "AMC", "reported": False},
}
