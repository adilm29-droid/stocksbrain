"""
Two Sigma Alt-Data Framework — alternative data signals.
Uses publicly available proxies for web traffic, job trends, news velocity.
Score: -2 to +2
Note: Full Two Sigma uses proprietary satellite/credit card data — these are free proxies.
"""
import requests


def twosigma_altdata_score(ticker: str, price_data: dict, analyst_data: dict,
                           news_data: dict, macro_data: dict) -> dict:
    score = 0
    details = {}

    # Signal 1: News velocity (number of recent articles = attention)
    sentiment = news_data.get("sentiment_score", 0)
    article_count = news_data.get("article_count", 0)
    details["news_sentiment"] = sentiment
    details["article_count"] = article_count

    if sentiment > 0.3 and article_count >= 3:
        score += 1  # Positive coverage momentum
        details["news_signal"] = "positive_momentum"
    elif sentiment < -0.3 and article_count >= 3:
        score -= 1  # Negative coverage momentum
        details["news_signal"] = "negative_momentum"

    # Signal 2: Analyst revision momentum (proxy for institutional re-rating)
    upside = analyst_data.get("upside_pct")
    if upside and upside > 25:
        score += 0.5
        details["analyst_revision"] = "strong_upside"
    elif upside and upside < -5:
        score -= 0.5
        details["analyst_revision"] = "downside_risk"

    # Signal 3: Earnings surprise quality (forward indicator)
    beat_raised = news_data.get("earnings_beat_and_raised", False)
    thesis_breaks = news_data.get("thesis_break_flags", [])
    if beat_raised:
        score += 0.5
    if len(thesis_breaks) > 0:
        score -= 0.5

    score = max(-2, min(2, score))
    reason = f"TwoSigma alt-data: news_sentiment={sentiment:.2f}, {details.get('news_signal', 'neutral')}"
    return {"score": round(score, 1), "reason": reason, "details": details}
