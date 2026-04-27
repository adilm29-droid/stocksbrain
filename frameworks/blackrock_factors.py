"""
BlackRock Factor Construction Framework — 6-factor model.
Factors: Value, Momentum, Quality, Size, Volatility, Yield.
Score: -2 to +2
"""
import yfinance as yf


def blackrock_factor_score(ticker: str, price_data: dict, analyst_data: dict,
                           news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}
    factor_scores = {}

    try:
        info = yf.Ticker(ticker).info
    except Exception as e:
        return {"score": 0, "reason": f"Data error: {e}", "details": {}}

    # Factor 1: Value (P/E vs sector)
    pe = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")
    if pe and 0 < pe < 60:
        factor_scores["value"] = 1
        score += 0.3
    elif pe and pe > 80:
        factor_scores["value"] = -1
        score -= 0.3
    else:
        factor_scores["value"] = 0
    details["pe"] = pe

    # Factor 2: Momentum (from price data)
    rsi = price_data.get("rsi", 50)
    sma200 = price_data.get("sma200", 0)
    price = price_data.get("price", 0)
    details["rsi"] = rsi
    if price and sma200 and price > sma200 and rsi > 40 and rsi < 75:
        factor_scores["momentum"] = 1
        score += 0.4
    elif price and sma200 and price < sma200:
        factor_scores["momentum"] = -1
        score -= 0.4
    else:
        factor_scores["momentum"] = 0

    # Factor 3: Quality (ROE, gross margin)
    roe = info.get("returnOnEquity", 0) or 0
    gross_margin = info.get("grossMargins", 0) or 0
    details["roe"] = round(roe * 100, 1)
    details["gross_margin"] = round(gross_margin * 100, 1)
    quality = (1 if roe > 0.15 else 0) + (1 if gross_margin > 0.40 else 0)
    factor_scores["quality"] = quality - 1  # -1 to +1
    score += factor_scores["quality"] * 0.4

    # Factor 4: Size (market cap — prefer mid/large)
    mktcap = info.get("marketCap", 0) or 0
    details["market_cap_b"] = round(mktcap / 1e9, 1)
    if mktcap > 10e9:
        factor_scores["size"] = 1
        score += 0.2
    elif mktcap < 500e6:
        factor_scores["size"] = -1
        score -= 0.3
    else:
        factor_scores["size"] = 0

    # Factor 5: Volatility (low vol premium)
    beta = info.get("beta", 1.0) or 1.0
    details["beta"] = beta
    if beta < 0.8:
        factor_scores["volatility"] = 1
        score += 0.2
    elif beta > 1.5:
        factor_scores["volatility"] = -1
        score -= 0.2
    else:
        factor_scores["volatility"] = 0

    # Factor 6: Yield (dividend + buyback proxy)
    div_yield = info.get("dividendYield", 0) or 0
    details["div_yield"] = round(div_yield * 100, 2)
    if div_yield > 0.02:
        factor_scores["yield"] = 1
        score += 0.2

    score = max(-2, min(2, score))
    top_factors = [f for f, s in factor_scores.items() if s > 0]
    reason = f"BlackRock factors: {', '.join(top_factors) if top_factors else 'mixed'}"
    details["factor_scores"] = factor_scores
    return {"score": round(score, 1), "reason": reason, "details": details}
