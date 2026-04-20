"""
prices.py — Fetches OHLCV data and computes technical indicators via yfinance.

Functions:
    get_price_data(ticker, period="6mo") -> dict | None
"""

import sys
import numpy as np

try:
    import yfinance as yf
except ImportError:
    yf = None


def _calc_rsi(closes: np.ndarray, period: int = 14) -> float:
    """Standard Wilder RSI using exponential smoothing."""
    if len(closes) < period + 1:
        return 50.0  # neutral fallback

    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Initial averages (simple mean for first window)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    # Wilder smoothing for remaining periods
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def _ema(values: np.ndarray, span: int) -> np.ndarray:
    """Exponential moving average."""
    alpha = 2.0 / (span + 1)
    result = np.empty(len(values))
    result[0] = values[0]
    for i in range(1, len(values)):
        result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
    return result


def _calc_macd(closes: np.ndarray):
    """Returns (macd_line, signal_line) for the latest bar."""
    if len(closes) < 35:
        return 0.0, 0.0

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)
    macd_line = ema12 - ema26
    signal_line = _ema(macd_line, 9)
    return round(float(macd_line[-1]), 4), round(float(signal_line[-1]), 4)


def get_price_data(ticker: str, period: str = "6mo") -> dict | None:
    """
    Fetch price data and compute technical indicators.

    Returns dict with keys:
        price, change_pct, rsi, macd, macd_signal,
        sma50, sma200, volume

    Returns None on any error.
    """
    if yf is None:
        print(f"[ERROR] yfinance not installed — cannot fetch {ticker}", file=sys.stderr)
        return None

    try:
        ticker_obj = yf.Ticker(ticker)
        # Fetch enough history for SMA200 + RSI
        hist = ticker_obj.history(period="1y")

        if hist is None or hist.empty:
            print(f"[WARN] No price history for {ticker}", file=sys.stderr)
            return None

        closes = hist["Close"].dropna().values.astype(float)
        volumes = hist["Volume"].dropna().values

        if len(closes) < 2:
            print(f"[WARN] Insufficient data for {ticker}", file=sys.stderr)
            return None

        price = float(closes[-1])
        prev_close = float(closes[-2])
        change_pct = round((price - prev_close) / prev_close * 100, 2) if prev_close != 0 else 0.0

        rsi = _calc_rsi(closes)
        macd, macd_signal = _calc_macd(closes)

        sma50 = round(float(np.mean(closes[-50:])), 2) if len(closes) >= 50 else None
        sma200 = round(float(np.mean(closes[-200:])), 2) if len(closes) >= 200 else None

        volume = int(volumes[-1]) if len(volumes) > 0 else 0

        return {
            "ticker": ticker,
            "price": round(price, 4),
            "change_pct": change_pct,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
            "sma50": sma50,
            "sma200": sma200,
            "volume": volume,
        }

    except Exception as exc:
        print(f"[ERROR] prices.get_price_data({ticker}): {exc}", file=sys.stderr)
        return None
