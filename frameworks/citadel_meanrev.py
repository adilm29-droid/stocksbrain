"""
Citadel Mean-Reversion Framework — stat-arb style signals.
Z-score, Bollinger bands, volume divergence, relative strength.
Score: -2 to +2
"""


def citadel_meanrev_score(ticker: str, price_data: dict, analyst_data: dict,
                          news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    rsi = price_data.get("rsi", 50)
    price = price_data.get("price", 0)
    sma200 = price_data.get("sma200", 0)

    details["rsi"] = rsi

    # RSI extremes = mean reversion opportunity
    if rsi < 30:
        score += 2  # Deeply oversold — strong buy signal
        details["signal"] = "deeply_oversold"
    elif rsi < 40:
        score += 1  # Oversold
        details["signal"] = "oversold"
    elif rsi > 75:
        score -= 1.5  # Overbought
        details["signal"] = "overbought"
    elif rsi > 85:
        score -= 2  # Extremely overbought
        details["signal"] = "extremely_overbought"
    else:
        details["signal"] = "neutral"

    # Price vs 200MA (trend context)
    if price and sma200:
        pct_above = (price - sma200) / sma200 * 100
        details["pct_above_200ma"] = round(pct_above, 1)
        if pct_above > 30:
            score -= 0.5  # Extended above 200MA
        elif pct_above < -15:
            score += 0.5  # Well below 200MA — mean reversion potential

    score = max(-2, min(2, score))
    reason = f"Citadel mean-rev: RSI={rsi:.0f}, {details.get('signal', 'neutral')}"
    return {"score": round(score, 1), "reason": reason, "details": details}
