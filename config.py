HOLDINGS = {
    # ticker: {shares, avg_cost, bucket}
    "AMD": {"shares": 4.33, "avg_cost": 142.50, "bucket": "equity"},
    "AMZN": {"shares": 7.35, "avg_cost": 185.20, "bucket": "equity"},
    "KO": {"shares": 10.0, "avg_cost": 62.50, "bucket": "equity"},
    "META": {"shares": 0.55, "avg_cost": 520.00, "bucket": "equity"},
    "MSFT": {"shares": 1.45, "avg_cost": 380.00, "bucket": "equity"},
    "NKE": {"shares": 8.0, "avg_cost": 75.00, "bucket": "equity"},
    "NVDA": {"shares": 5.0, "avg_cost": 110.00, "bucket": "equity"},
    "PLTR": {"shares": 15.0, "avg_cost": 22.00, "bucket": "equity"},
    "TSLA": {"shares": 3.21, "avg_cost": 250.00, "bucket": "equity"},
    "UNH": {"shares": 4.94, "avg_cost": 490.00, "bucket": "equity"},
    "SPUS": {"shares": 50.0, "avg_cost": 42.00, "bucket": "core_etf"},
    "URTH": {"shares": 20.0, "avg_cost": 105.00, "bucket": "core_etf"},
    "HLAL": {"shares": 30.0, "avg_cost": 38.00, "bucket": "core_etf"},
    "BTC-USD": {"shares": 0.05, "avg_cost": 45000.00, "bucket": "crypto"},
    "ETH-USD": {"shares": 0.5, "avg_cost": 2800.00, "bucket": "crypto"},
    "XRP-USD": {"shares": 500.0, "avg_cost": 0.80, "bucket": "crypto"},
    "SOL-USD": {"shares": 3.0, "avg_cost": 120.00, "bucket": "crypto"},
    "GLD": {"shares": 5.0, "avg_cost": 185.00, "bucket": "commodity"},
    "SLV": {"shares": 20.0, "avg_cost": 22.00, "bucket": "commodity"},
}

AUTOPILOT_PORTFOLIOS = {
    "Cybersecurity": {"total_value": 5000, "total_cost": 4500},
    "FATMAA": {"total_value": 8000, "total_cost": 7000},
    "Architects of AI": {"total_value": 6000, "total_cost": 5500},
    "Dividend Stocks": {"total_value": 4000, "total_cost": 3800},
}

CORE_ETF_TICKERS = {"SPUS", "URTH", "HLAL"}
CASH_BUFFER_PCT_MIN = 5.0  # alert if below this

WATCHLIST = ["GOOG", "AAPL", "BRKB", "VTI", "QQQ"]

THRESHOLDS = {
    "rsi_oversold": 35,
    "rsi_overbought": 70,
    "analyst_upside_buy": 15.0,   # % upside to trigger buy signal
    "analyst_upside_sell": 5.0,   # % upside below which is sell signal
    "concentration_cap": 7.0,     # % of portfolio
    "gain_trim_threshold": 50.0,  # % gain that triggers trim consideration
}
