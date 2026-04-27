"""
Berkshire Quality Moat Framework — Buffett-style moat detection.
Scores brand power, network effects, switching costs, cost advantages, patents, regulatory moats.
Score: -2 to +2
"""
import yfinance as yf


# Simplified moat classification by ticker (would expand with NLP analysis)
KNOWN_MOATS = {
    # Wide moat tickers (strong competitive advantages)
    "MSFT": {"moat_type": "network+switching", "strength": 5},
    "AMZN": {"moat_type": "network+cost", "strength": 5},
    "GOOGL": {"moat_type": "network+brand", "strength": 5},
    "META": {"moat_type": "network", "strength": 4},
    "NVDA": {"moat_type": "ip+switching", "strength": 5},
    "V":    {"moat_type": "network+brand", "strength": 5},
    "KO":   {"moat_type": "brand+distribution", "strength": 5},
    "PEP":  {"moat_type": "brand+distribution", "strength": 4},
    "UNH":  {"moat_type": "cost+regulatory", "strength": 4},
    "SPUS": {"moat_type": "diversified_etf", "strength": 3},
    "HLAL": {"moat_type": "diversified_etf", "strength": 3},
    "AMD":  {"moat_type": "ip+engineering", "strength": 3},
    "TSLA": {"moat_type": "brand+cost", "strength": 3},
    "PLTR": {"moat_type": "switching+ip", "strength": 3},
    "NKE":  {"moat_type": "brand", "strength": 3},
    "HNST": {"moat_type": "brand_niche", "strength": 2},
    "SSTK": {"moat_type": "switching+brand", "strength": 2},
    "SPOT": {"moat_type": "network+switching", "strength": 3},
}


def berkshire_moat_score(ticker: str, price_data: dict, analyst_data: dict,
                         news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    moat_info = KNOWN_MOATS.get(ticker, {})
    moat_strength = moat_info.get("strength", 0)
    moat_type = moat_info.get("moat_type", "unknown")
    details["moat_type"] = moat_type
    details["moat_strength"] = moat_strength

    # Base score from moat strength (0-5 scale → -2 to +2)
    if moat_strength >= 5:
        score = 2  # Wide moat
    elif moat_strength >= 4:
        score = 1.5
    elif moat_strength >= 3:
        score = 1  # Narrow moat
    elif moat_strength == 2:
        score = 0  # Questionable moat
    else:
        score = -1  # No moat detected

    # Adjust for valuation vs moat (Buffett says: fair price for great business)
    try:
        info = yf.Ticker(ticker).info
        pe = info.get("trailingPE")
        if pe:
            details["pe"] = pe
            # Even wide-moat stocks can be overpriced
            if pe > 80 and moat_strength < 5:
                score -= 0.5
                details["valuation_penalty"] = True
    except Exception:
        pass

    score = max(-2, min(2, score))
    reason = f"Berkshire moat: {moat_type} (strength {moat_strength}/5)"
    return {"score": round(score, 1), "reason": reason, "details": details}
