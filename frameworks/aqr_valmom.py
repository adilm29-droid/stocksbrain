"""
AQR Value + Momentum Framework.
Identifies: high momentum + low valuation (rare gem) vs low momentum + high valuation (trap).
Score: -2 to +2
"""
import yfinance as yf


def aqr_valmom_score(ticker: str, price_data: dict, analyst_data: dict,
                     news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return {"score": 0, "reason": "Data unavailable", "details": {}}

    # Momentum signal
    rsi = price_data.get("rsi", 50)
    sma200 = price_data.get("sma200", 0)
    price = price_data.get("price", 0)

    above_200ma = price > sma200 if (price and sma200) else None
    momentum_positive = above_200ma and rsi > 45 and rsi < 75
    momentum_negative = not above_200ma if above_200ma is not None else False

    details["above_200ma"] = above_200ma
    details["rsi"] = rsi

    # Valuation signal
    pe = info.get("trailingPE")
    ps = info.get("priceToSalesTrailing12Months")
    details["pe"] = pe
    details["ps"] = ps

    low_valuation = (pe and pe < 25) or (ps and ps < 5)
    high_valuation = (pe and pe > 60) or (ps and ps > 20)

    # AQR scoring matrix
    if momentum_positive and low_valuation:
        score = 2  # Rare gem: momentum + value
        details["signal"] = "value_momentum_gem"
    elif momentum_positive and not high_valuation:
        score = 1  # Good: momentum, fair valuation
        details["signal"] = "momentum_with_ok_value"
    elif momentum_negative and high_valuation:
        score = -2  # Trap: no momentum + expensive
        details["signal"] = "overvalued_momentum_trap"
    elif momentum_negative:
        score = -1  # Weak: losing momentum
        details["signal"] = "momentum_breakdown"
    else:
        details["signal"] = "neutral"

    score = max(-2, min(2, score))
    reason = f"AQR Val+Mom: {details.get('signal', 'neutral')} (RSI={rsi:.0f}, PE={pe})"
    return {"score": round(score, 1), "reason": reason, "details": details}
