"""
Goldman Sachs GS Sustain Framework — simplified implementation.
Identifies long-term winners via ROCE, market positioning, management quality, ESG.
Score: -2 to +2
"""
import yfinance as yf


def gs_sustain_score(ticker: str, price_data: dict, analyst_data: dict,
                     news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    try:
        info = yf.Ticker(ticker).info
    except Exception as e:
        return {"score": 0, "reason": f"Data unavailable: {e}", "details": {}}

    # 1. Return on equity (proxy for ROCE) > 15%
    roe = info.get("returnOnEquity")
    if roe is not None:
        details["roe"] = round(roe * 100, 1)
        if roe > 0.15:
            score += 1
        elif roe < 0:
            score -= 1

    # 2. Profit margins (proxy for industry positioning)
    margin = info.get("profitMargins")
    if margin is not None:
        details["profit_margin"] = round(margin * 100, 1)
        if margin > 0.15:
            score += 1
        elif margin < 0.05:
            score -= 1

    # 3. Revenue growth (proxy for management quality)
    rev_growth = info.get("revenueGrowth")
    if rev_growth is not None:
        details["revenue_growth"] = round(rev_growth * 100, 1)
        if rev_growth > 0.10:
            score += 0.5
        elif rev_growth < -0.05:
            score -= 0.5

    # 4. Low debt (ESG governance proxy)
    de_ratio = info.get("debtToEquity")
    if de_ratio is not None:
        details["debt_to_equity"] = round(de_ratio, 2)
        if de_ratio < 50:
            score += 0.5
        elif de_ratio > 200:
            score -= 0.5

    score = max(-2, min(2, score))
    roe_str = f"ROE {details.get('roe', 'N/A')}%"
    margin_str = f"margin {details.get('profit_margin', 'N/A')}%"
    reason = f"GS Sustain: {roe_str}, {margin_str}"

    return {"score": round(score, 1), "reason": reason, "details": details}
