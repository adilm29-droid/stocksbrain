"""
analysts.py — Fetches analyst consensus and price targets via yfinance.

Functions:
    get_analyst_data(ticker) -> dict
"""

import sys

try:
    import yfinance as yf
except ImportError:
    yf = None

_EMPTY = {
    "consensus": "N/A",
    "target_price": None,
    "upside_pct": None,
    "num_analysts": 0,
    "recommendation_mean": None,
}


def _map_recommendation_mean(mean: float) -> str:
    """
    Convert yfinance recommendationMean (1-5 scale) to human-readable consensus.

    Scale:
        1.0 - 1.5  → Strong Buy
        1.5 - 2.5  → Buy
        2.5 - 3.5  → Hold
        3.5 - 4.5  → Sell
        4.5 - 5.0  → Strong Sell
    """
    if mean is None:
        return "N/A"
    if mean <= 1.5:
        return "Strong Buy"
    elif mean <= 2.5:
        return "Buy"
    elif mean <= 3.5:
        return "Hold"
    elif mean <= 4.5:
        return "Sell"
    else:
        return "Strong Sell"


def get_analyst_data(ticker: str) -> dict:
    """
    Fetch analyst consensus, price target, and upside from yfinance .info.

    Returns dict:
        consensus (str) — "Strong Buy" / "Buy" / "Hold" / "Sell" / "Strong Sell" / "N/A"
        target_price (float | None)
        upside_pct (float | None)
        num_analysts (int)
        recommendation_mean (float | None)
    """
    if yf is None:
        return {**_EMPTY, "error": "yfinance not installed"}

    try:
        info = yf.Ticker(ticker).info
    except Exception as exc:
        print(f"[ERROR] analysts.get_analyst_data({ticker}): {exc}", file=sys.stderr)
        return {**_EMPTY, "error": str(exc)}

    if not info:
        return {**_EMPTY, "error": "Empty info dict"}

    try:
        rec_mean = info.get("recommendationMean")
        target_price = info.get("targetMeanPrice")
        current_price = info.get("currentPrice") or info.get("regularMarketPrice")
        num_analysts = info.get("numberOfAnalystOpinions", 0) or 0

        consensus = _map_recommendation_mean(float(rec_mean) if rec_mean is not None else None)

        upside_pct = None
        if target_price and current_price and current_price > 0:
            upside_pct = round((float(target_price) - float(current_price)) / float(current_price) * 100, 2)

        return {
            "consensus": consensus,
            "target_price": round(float(target_price), 2) if target_price is not None else None,
            "upside_pct": upside_pct,
            "num_analysts": int(num_analysts),
            "recommendation_mean": round(float(rec_mean), 2) if rec_mean is not None else None,
        }

    except Exception as exc:
        print(f"[ERROR] analysts.get_analyst_data({ticker}): parse error — {exc}", file=sys.stderr)
        return {**_EMPTY, "error": str(exc)}
