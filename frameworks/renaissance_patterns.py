"""
Renaissance-inspired Pattern Detection Framework.
Detects: seasonality, earnings drift, momentum patterns.
Score: -2 to +2
"""
from datetime import datetime


def renaissance_score(ticker: str, price_data: dict, analyst_data: dict,
                      news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    today = datetime.utcnow()
    month = today.month
    details["month"] = month

    # Seasonal patterns (simplified)
    # "Sell in May" effect — April/May caution for cyclicals
    sector_from_macro = macro_data.get("sector_rotation_signal", {}) if macro_data else {}

    # Jan/Feb effect — small cap outperformance
    if month in (1, 2):
        score += 0.3
        details["seasonality"] = "jan_effect_tailwind"
    # Q4 tax-loss harvesting recovery (Nov/Dec)
    elif month in (11, 12):
        score += 0.3
        details["seasonality"] = "q4_recovery"
    # May-October historically weaker
    elif month in (5, 6, 7, 8):
        score -= 0.3
        details["seasonality"] = "summer_weakness"

    # Earnings beat drift: stocks tend to drift up 30-60 days after a beat
    beat = news_data.get("earnings_beat_and_raised", False)
    if beat:
        score += 1.0
        details["earnings_drift"] = "post_beat_drift"

    # Momentum pattern: above 200MA and RSI 40-65 = healthy trend
    rsi = price_data.get("rsi", 50)
    sma200 = price_data.get("sma200", 0)
    price = price_data.get("price", 0)
    if price and sma200 and price > sma200 and 40 < rsi < 65:
        score += 0.5
        details["momentum_pattern"] = "healthy_uptrend"
    elif price and sma200 and price < sma200 and rsi < 45:
        score -= 0.5
        details["momentum_pattern"] = "downtrend_confirmed"

    score = max(-2, min(2, score))
    reason = f"Renaissance patterns: {details.get('seasonality', 'neutral')}, {details.get('momentum_pattern', 'no_pattern')}"
    return {"score": round(score, 1), "reason": reason, "details": details}
