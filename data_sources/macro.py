"""
macro.py — Fetches macro indicators using yfinance.

Functions:
    get_macro_data() -> dict
"""

import sys

try:
    import yfinance as yf
    import numpy as np
except ImportError:
    yf = None
    np = None

# Sector ETFs used as proxies for rotation analysis
SECTOR_MAP = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Energy": "XLE",
    "Consumer Staples": "XLP",
    "Consumer Discretionary": "XLY",
    "Utilities": "XLU",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}


def _fetch_latest_price(ticker: str) -> float | None:
    """Fetch latest close for a given ticker."""
    if yf is None:
        return None
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist is None or hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception as exc:
        print(f"[WARN] macro._fetch_latest_price({ticker}): {exc}", file=sys.stderr)
        return None


def _fetch_sma200_data(ticker: str) -> tuple[float | None, float | None]:
    """Returns (latest_price, sma200) tuple."""
    if yf is None:
        return None, None
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        if hist is None or hist.empty:
            return None, None
        closes = hist["Close"].dropna().values.astype(float)
        price = float(closes[-1])
        sma200 = float(np.mean(closes[-200:])) if len(closes) >= 200 else float(np.mean(closes))
        return price, sma200
    except Exception as exc:
        print(f"[WARN] macro._fetch_sma200_data({ticker}): {exc}", file=sys.stderr)
        return None, None


def _derive_sector_rotation(vix: float | None, sp500_trend: str) -> dict:
    """
    Simple heuristic for sector rotation signals.

    Rules:
    - VIX < 20 AND SP500 BULLISH  → Tech/Growth FAVORABLE, Defensives NEUTRAL
    - VIX > 25                    → Defensives FAVORABLE, Tech/Growth UNFAVORABLE
    - Otherwise                   → NEUTRAL across the board
    """
    result = {sector: "NEUTRAL" for sector in SECTOR_MAP}

    if vix is None:
        return result

    growth_sectors = {"Technology", "Consumer Discretionary", "Communication Services"}
    defensive_sectors = {"Healthcare", "Consumer Staples", "Utilities"}

    if vix < 20 and sp500_trend == "BULLISH":
        for s in growth_sectors:
            result[s] = "FAVORABLE"
        for s in defensive_sectors:
            result[s] = "NEUTRAL"
    elif vix > 25:
        for s in growth_sectors:
            result[s] = "UNFAVORABLE"
        for s in defensive_sectors:
            result[s] = "FAVORABLE"

    return result


def get_macro_data() -> dict:
    """
    Fetch macro environment data.

    Returns dict:
        vix (float)
        dxy (float)
        ten_year_yield (float)
        oil_price (float)
        gold_price (float)
        sp500_price (float)
        sp500_sma200 (float)
        sp500_trend ("BULLISH" | "BEARISH" | "UNKNOWN")
        sector_rotation_signal (dict: sector -> "FAVORABLE"/"NEUTRAL"/"UNFAVORABLE")
    """
    if yf is None:
        return {
            "vix": None,
            "dxy": None,
            "ten_year_yield": None,
            "oil_price": None,
            "gold_price": None,
            "sp500_price": None,
            "sp500_sma200": None,
            "sp500_trend": "UNKNOWN",
            "sector_rotation_signal": {},
            "error": "yfinance not installed",
        }

    print("[INFO] Fetching macro data...", file=sys.stderr)

    vix = _fetch_latest_price("^VIX")
    dxy = _fetch_latest_price("DX-Y.NYB")
    ten_year_yield = _fetch_latest_price("^TNX")
    oil_price = _fetch_latest_price("CL=F")
    gold_price = _fetch_latest_price("GC=F")

    sp500_price, sp500_sma200 = _fetch_sma200_data("^GSPC")

    if sp500_price is not None and sp500_sma200 is not None:
        sp500_trend = "BULLISH" if sp500_price > sp500_sma200 else "BEARISH"
    else:
        sp500_trend = "UNKNOWN"

    sector_rotation = _derive_sector_rotation(vix, sp500_trend)

    return {
        "vix": round(vix, 2) if vix is not None else None,
        "dxy": round(dxy, 3) if dxy is not None else None,
        "ten_year_yield": round(ten_year_yield, 3) if ten_year_yield is not None else None,
        "oil_price": round(oil_price, 2) if oil_price is not None else None,
        "gold_price": round(gold_price, 2) if gold_price is not None else None,
        "sp500_price": round(sp500_price, 2) if sp500_price is not None else None,
        "sp500_sma200": round(sp500_sma200, 2) if sp500_sma200 is not None else None,
        "sp500_trend": sp500_trend,
        "sector_rotation_signal": sector_rotation,
    }
