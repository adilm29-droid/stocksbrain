"""
Bridgewater All-Weather Risk Parity Framework — simplified.
Checks if position fits a balanced risk profile across regimes.
Score: -2 to +2
"""
import yfinance as yf


def bridgewater_score(ticker: str, price_data: dict, analyst_data: dict,
                      news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    # Macro regime context
    vix = macro_data.get("vix", 20) if macro_data else 20
    sp500_trend = macro_data.get("sp500_trend", "NEUTRAL") if macro_data else "NEUTRAL"

    try:
        info = yf.Ticker(ticker).info
    except Exception:
        return {"score": 0, "reason": "Data unavailable", "details": {}}

    beta = info.get("beta")
    details["beta"] = beta

    # 1. In high-volatility regime (VIX > 25), low-beta is preferred
    if vix > 25:
        if beta is not None:
            if beta < 0.7:
                score += 1  # Defensive in risk-off
            elif beta > 1.3:
                score -= 1  # Too risky in risk-off
    else:
        # Low VIX — reward growth/cyclical
        if beta is not None:
            if beta > 1.0:
                score += 0.5  # Growth-tilted in risk-on
            elif beta < 0.5:
                score -= 0.5  # Underperforms in rally

    # 2. Dividend yield (income component — beneficial in any regime)
    div_yield = info.get("dividendYield")
    details["dividend_yield"] = div_yield
    if div_yield and div_yield > 0.02:
        score += 0.5

    # 3. Sector regime fit
    sector = info.get("sector", "")
    details["sector"] = sector
    if sp500_trend == "BEARISH" and sector in ("Utilities", "Consumer Staples", "Healthcare"):
        score += 0.5
    elif sp500_trend == "BULLISH" and sector in ("Technology", "Consumer Discretionary", "Financials"):
        score += 0.5

    score = max(-2, min(2, score))
    beta_str = f"beta={beta:.2f}" if beta else "beta=N/A"
    reason = f"Bridgewater risk parity: {beta_str}, VIX={vix:.0f}"
    return {"score": round(score, 1), "reason": reason, "details": details}
