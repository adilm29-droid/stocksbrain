"""
options.py — Fetches options chain data via yfinance for put/call ratio and unusual activity.

Functions:
    get_options_flow(ticker) -> dict
"""

import sys

try:
    import yfinance as yf
except ImportError:
    yf = None

_NEUTRAL = {
    "put_call_ratio": None,
    "unusual_activity": False,
    "sentiment": "NEUTRAL",
}


def get_options_flow(ticker: str) -> dict:
    """
    Fetch options chain for nearest expiry and compute flow metrics.

    Returns dict:
        put_call_ratio (float | None) — total put volume / total call volume
        unusual_activity (bool) — True if any contract has volume > 10x open_interest
        sentiment ("BULLISH" | "BEARISH" | "NEUTRAL")
    """
    if yf is None:
        return {**_NEUTRAL, "error": "yfinance not installed"}

    try:
        ticker_obj = yf.Ticker(ticker)
        expirations = ticker_obj.options

        if not expirations:
            return {**_NEUTRAL, "error": "No options expirations available"}

        # Use nearest expiry
        nearest_expiry = expirations[0]
        chain = ticker_obj.option_chain(nearest_expiry)

        calls = chain.calls
        puts = chain.puts

        if calls is None or calls.empty or puts is None or puts.empty:
            return {**_NEUTRAL, "error": "Empty options chain"}

        # Put/call ratio by volume
        total_call_volume = calls["volume"].fillna(0).sum()
        total_put_volume = puts["volume"].fillna(0).sum()

        if total_call_volume == 0:
            put_call_ratio = None
        else:
            put_call_ratio = round(float(total_put_volume) / float(total_call_volume), 3)

        # Unusual activity: any contract with volume > 10x open interest
        unusual_activity = False

        for df in [calls, puts]:
            if "volume" in df.columns and "openInterest" in df.columns:
                for _, row in df.iterrows():
                    vol = row.get("volume", 0) or 0
                    oi = row.get("openInterest", 0) or 0
                    if oi > 0 and vol > oi * 10:
                        unusual_activity = True
                        break

        # Sentiment heuristic based on put/call ratio
        if put_call_ratio is None:
            sentiment = "NEUTRAL"
        elif put_call_ratio < 0.7:
            sentiment = "BULLISH"
        elif put_call_ratio > 1.2:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"

        return {
            "put_call_ratio": put_call_ratio,
            "unusual_activity": unusual_activity,
            "sentiment": sentiment,
            "expiry_used": nearest_expiry,
        }

    except Exception as exc:
        print(f"[WARN] options.get_options_flow({ticker}): {exc}", file=sys.stderr)
        return {**_NEUTRAL, "error": str(exc)}
