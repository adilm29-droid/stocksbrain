"""
JPMorgan Earnings Momentum Framework.
Scores based on earnings history, estimate revisions, guidance trajectory.
Score: -2 to +2
"""
import yfinance as yf


def jpm_earnings_score(ticker: str, price_data: dict, analyst_data: dict,
                       news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    try:
        t = yf.Ticker(ticker)
        info = t.info
    except Exception as e:
        return {"score": 0, "reason": f"Data error: {e}", "details": {}}

    # 1. Earnings beat signal from news_data
    beat = news_data.get("earnings_beat_and_raised", False)
    if beat:
        score += 1
        details["earnings_beat"] = True

    # 2. Analyst upside from analyst_data
    upside = analyst_data.get("upside_pct")
    details["analyst_upside"] = upside
    if upside is not None:
        if upside > 20:
            score += 1
        elif upside > 10:
            score += 0.5
        elif upside < 0:
            score -= 1

    # 3. Forward PE vs trailing PE (guidance trajectory)
    fwd_pe = info.get("forwardPE")
    trail_pe = info.get("trailingPE")
    details["fwd_pe"] = fwd_pe
    details["trail_pe"] = trail_pe
    if fwd_pe and trail_pe and trail_pe > 0:
        if fwd_pe < trail_pe * 0.85:
            score += 1  # Earnings expected to grow strongly
            details["pe_contraction"] = True
        elif fwd_pe > trail_pe * 1.15:
            score -= 0.5  # Earnings declining

    # 4. EPS quarter surprise from info
    eps_surprise = info.get("earningsQuarterlyGrowth")
    details["eps_qoq_growth"] = eps_surprise
    if eps_surprise is not None:
        if eps_surprise > 0.15:
            score += 0.5
        elif eps_surprise < -0.10:
            score -= 0.5

    score = max(-2, min(2, score))
    upside_str = f"upside {upside:.1f}%" if upside else "upside N/A"
    reason = f"JPM earnings momentum: {upside_str}, beat={beat}"
    return {"score": round(score, 1), "reason": reason, "details": details}
