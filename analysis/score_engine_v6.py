"""
StocksBrain V6 — 14-Factor Scoring Engine.
Replaces score_engine_v1 (scorer.py) with weighted multi-source intelligence.

Factor weights (total scale: ~-22.4 to +22.4):
  1. Technicals (full suite)          1.0
  2. Earnings momentum                1.0
  3. Analyst rating revisions         0.8
  4. Insider trading                  1.5
  5. Institutional 13F changes        0.8
  6. Congressional trades             0.5
  7. News sentiment                   1.0
  8. Reddit retail (inverse signal)   0.3
  9. Options flow                     0.8
 10. AI deals & partnerships          1.0
 11. M&A activity                     1.0
 12. Political/policy news            0.7
 13. Kronos forecast (1 of 14)        0.7
 14. Institutional frameworks agg.    1.5
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import CORE_ETF_TICKERS, THRESHOLDS, EARNINGS_CALENDAR, HALAL_APPROVED

FACTOR_WEIGHTS = {
    "technicals":       1.0,
    "earnings_momentum":1.0,
    "analyst_revisions":0.8,
    "insider_trading":  1.5,
    "thirteen_f":       0.8,
    "congress_trades":  0.5,
    "news_sentiment":   1.0,
    "reddit_retail":    0.3,
    "options_flow":     0.8,
    "ai_deals":         1.0,
    "ma_activity":      1.0,
    "political_news":   0.7,
    "kronos":           0.7,
    "frameworks_agg":   1.5,
}

TOTAL_MAX_WEIGHT = sum(FACTOR_WEIGHTS.values())  # ≈ 12.3
# Each factor raw score is -1 to +1; weighted sum is -12.3 to +12.3


def score_holding_v6(
    ticker: str,
    holding_config: dict,
    price_data: dict,
    analyst_data: dict,
    insider_data: dict,
    news_data: dict,
    macro_data: dict,
    portfolio_metrics: dict,
    options_data: dict = None,
    framework_scores: dict = None,
    congress_data: dict = None,
    kronos_data: dict = None,
) -> dict:
    """
    V6 14-factor scoring. Returns same interface as scorer.py for backward compatibility.
    """
    options_data = options_data or {}
    framework_scores = framework_scores or {}
    congress_data = congress_data or {}
    kronos_data = kronos_data or {}

    def _f(d, key, default=0.0):
        v = d.get(key) if d else None
        return float(v) if v is not None else default

    # --- Position metrics ---
    price = _f(price_data, "price") or _f(holding_config, "avg_cost")
    avg_cost = float(holding_config.get("avg_cost", price or 1.0))
    shares = float(holding_config.get("shares", 0.0))
    holding_value = shares * price
    total_value = portfolio_metrics.get("total_value", 1.0) or 1.0
    position_pct = holding_value / total_value * 100 if total_value > 0 else 0.0
    gain_pct = (price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0.0

    rsi = _f(price_data, "rsi", 50.0)
    sma200 = _f(price_data, "sma200", 0.0)
    upside_pct = analyst_data.get("upside_pct")
    has_buying = bool(insider_data.get("has_buying", False))
    has_cluster_buy = bool(insider_data.get("has_cluster_buy", False))
    has_cluster_sell = bool(insider_data.get("has_cluster_sell", False))
    earnings_beat_raised = bool(news_data.get("earnings_beat_and_raised", False))
    thesis_break_flags = news_data.get("thesis_break_flags", []) or []
    sentiment_score = _f(news_data, "sentiment_score", 0.0)

    signals: dict = {}
    score_breakdown: list = []
    factor_raw_scores: dict = {}

    # ---- Factor 1: Technicals (-1 to +1) ----
    tech_score = 0.0
    rsi_healthy = rsi < THRESHOLDS["rsi_oversold"] and (sma200 == 0.0 or price > sma200)
    rsi_ob = rsi > THRESHOLDS["rsi_overbought"]
    if rsi_healthy:
        tech_score += 0.6
    if rsi_ob:
        tech_score -= 0.5
    if sma200 > 0 and price > sma200:
        tech_score += 0.4
    elif sma200 > 0 and price < sma200:
        tech_score -= 0.4
    tech_score = max(-1, min(1, tech_score))
    factor_raw_scores["technicals"] = tech_score
    signals["rsi_healthy_pullback"] = rsi_healthy
    signals["rsi_overbought"] = rsi_ob
    if tech_score > 0:
        score_breakdown.append(f"+{tech_score:.1f}x1.0 Technicals: RSI {rsi:.0f} {'oversold' if rsi_healthy else 'OK'}, {'above' if price > sma200 else 'below'} 200MA")
    elif tech_score < 0:
        score_breakdown.append(f"{tech_score:.1f}x1.0 Technicals: RSI {rsi:.0f} {'overbought' if rsi_ob else 'OK'}, {'above' if price > sma200 else 'below'} 200MA")

    # ---- Factor 2: Earnings Momentum (-1 to +1) ----
    earn_score = 0.0
    if earnings_beat_raised:
        earn_score += 0.8
    signals["earnings_beat_raised"] = earnings_beat_raised
    earn_score = max(-1, min(1, earn_score))
    factor_raw_scores["earnings_momentum"] = earn_score

    # ---- Factor 3: Analyst Revisions (-1 to +1) ----
    analyst_score = 0.0
    if upside_pct is not None:
        if upside_pct > THRESHOLDS["analyst_upside_buy"]:
            analyst_score = min(1.0, upside_pct / 30.0)
        elif upside_pct < THRESHOLDS["analyst_upside_sell"]:
            analyst_score = -0.6
    factor_raw_scores["analyst_revisions"] = analyst_score
    signals["analyst_upside_strong"] = (upside_pct or 0) > THRESHOLDS["analyst_upside_buy"]
    signals["analyst_upside_weak"] = (upside_pct or 0) < THRESHOLDS["analyst_upside_sell"]
    if analyst_score != 0:
        score_breakdown.append(f"{'+'if analyst_score > 0 else ''}{analyst_score:.2f}x0.8 Analyst upside: {upside_pct:.1f}%" if upside_pct else "Analyst: no data")

    # ---- Factor 4: Insider Trading (-1 to +1) ----
    insider_score = 0.0
    if has_cluster_buy:
        insider_score = 1.0  # Strong cluster buy = max signal
    elif has_buying:
        insider_score = 0.5  # Single insider buy
    if has_cluster_sell:
        insider_score -= 0.4  # Cluster sell (less signal than buy)
    insider_score = max(-1, min(1, insider_score))
    factor_raw_scores["insider_trading"] = insider_score
    signals["insider_buying"] = has_buying
    signals["insider_cluster_buy"] = has_cluster_buy
    if insider_score > 0:
        score_breakdown.append(f"+{insider_score:.1f}x1.5 Insider: {'cluster buy' if has_cluster_buy else 'buying detected'}")

    # ---- Factor 5: 13F Changes (0 for now — quarterly data) ----
    factor_raw_scores["thirteen_f"] = 0.0  # Updated quarterly when 13Fs filed

    # ---- Factor 6: Congressional Trades (-1 to +1) ----
    congress_score = 0.0
    if congress_data.get("has_cluster"):
        if congress_data.get("buy_count", 0) > congress_data.get("sell_count", 0):
            congress_score = 0.6
        else:
            congress_score = -0.3
    factor_raw_scores["congress_trades"] = congress_score
    signals["congress_cluster"] = congress_data.get("has_cluster", False)

    # ---- Factor 7: News Sentiment (-1 to +1) ----
    news_score = max(-1, min(1, sentiment_score * 2))  # Scale from ±0.5 to ±1
    if len(thesis_break_flags) > 0:
        news_score -= 0.5
    news_score = max(-1, min(1, news_score))
    factor_raw_scores["news_sentiment"] = news_score
    signals["thesis_break"] = len(thesis_break_flags) > 0

    # ---- Factor 8: Reddit Retail (inverse — 0.3 weight) ----
    # Extreme retail bullishness = contrarian sell
    reddit_score = 0.0  # Would need Reddit API integration
    factor_raw_scores["reddit_retail"] = reddit_score

    # ---- Factor 9: Options Flow (-1 to +1) ----
    options_score = 0.0
    options_sentiment = options_data.get("sentiment", "NEUTRAL")
    unusual_calls = options_data.get("unusual_calls", False)
    unusual_puts = options_data.get("unusual_puts", False)
    if unusual_calls and options_sentiment in ("VERY_BULLISH", "BULLISH"):
        options_score = 0.8
    elif unusual_puts and options_sentiment in ("VERY_BEARISH", "BEARISH"):
        options_score = -0.8
    elif options_sentiment == "VERY_BULLISH":
        options_score = 0.4
    elif options_sentiment == "VERY_BEARISH":
        options_score = -0.4
    factor_raw_scores["options_flow"] = options_score
    signals["unusual_options"] = unusual_calls or unusual_puts

    # ---- Factor 10: AI Deals (0 for now — need to build tracker) ----
    factor_raw_scores["ai_deals"] = 0.0

    # ---- Factor 11: M&A Activity (0 for now) ----
    factor_raw_scores["ma_activity"] = 0.0

    # ---- Factor 12: Political/Policy News (-1 to +1) ----
    factor_raw_scores["political_news"] = 0.0  # Would need political_news.py

    # ---- Factor 13: Kronos (-1 to +1) ----
    kronos_score = 0.0
    if kronos_data.get("direction") == "UP":
        kronos_score = 0.5  # Directional only, capped at 0.5
    elif kronos_data.get("direction") == "DOWN":
        kronos_score = -0.5
    factor_raw_scores["kronos"] = kronos_score

    # ---- Factor 14: Institutional Frameworks (-1 to +1) ----
    frameworks_agg_score = 0.0
    if framework_scores:
        raw = framework_scores.get("score", 0)
        frameworks_agg_score = max(-1, min(1, raw / 2))  # Map -2/+2 to -1/+1
    factor_raw_scores["frameworks_agg"] = frameworks_agg_score
    if frameworks_agg_score != 0:
        score_breakdown.append(f"{'+'if frameworks_agg_score > 0 else ''}{frameworks_agg_score:.1f}x1.5 Frameworks: {framework_scores.get('breakdown', {})}")

    # ---- Weighted aggregate score ----
    weighted_score = sum(
        factor_raw_scores.get(factor, 0) * weight
        for factor, weight in FACTOR_WEIGHTS.items()
    )
    # Normalize to -5 to +5 range for backward compatibility
    score_normalized = round((weighted_score / TOTAL_MAX_WEIGHT) * 5, 2)
    score_int = round(score_normalized)

    # ---- Decision table ----
    if score_int >= 3:
        decision = "BUY"
    elif score_int >= 1:
        decision = "HOLD"
    elif score_int == 0:
        decision = "HOLD"
    elif score_int >= -2:
        decision = "TRIM"
    else:
        decision = "SELL"

    overlays_applied: list = []

    # Overlay 1: Autopilot tickers
    autopilot_tickers = portfolio_metrics.get("autopilot_tickers", set())
    if ticker in autopilot_tickers and decision in ("SELL", "TRIM"):
        overlays_applied.append(f"autopilot_{decision}_to_HOLD")
        decision = "HOLD"

    # Overlay 2: Earnings freeze (next 7 days)
    earnings_next_7 = portfolio_metrics.get("earnings_next_7_days", [])
    if ticker in earnings_next_7 and decision != "HOLD":
        overlays_applied.append(f"earnings_freeze_{decision}_to_HOLD")
        decision = "HOLD"

    # Overlay 3: Core ETF protection
    if ticker in CORE_ETF_TICKERS and decision in ("SELL", "TRIM"):
        overlays_applied.append(f"core_etf_{decision}_to_HOLD")
        decision = "HOLD"

    # Overlay 4: Cash buffer
    low_cash_flag = ""
    cash_pct = portfolio_metrics.get("cash_pct", 100.0)
    if cash_pct < 3.0 and decision == "BUY":
        overlays_applied.append("low_cash_dip_only")
        low_cash_flag = " (dip only — low cash)"

    # ---- Build output line ----
    gain_emoji = "📈" if gain_pct > 0 else "📉"
    gain_str = f"{gain_pct:+.1f}%"

    if decision == "BUY":
        output_line = f"[{ticker}] 💰 BUY{low_cash_flag} — score {score_int}/5, {gain_emoji} position {gain_str}"
    elif decision == "TRIM":
        output_line = f"[{ticker}] ⚠️ TRIM — score {score_int}/5, gain {gain_str} — consider reducing"
    elif decision == "SELL":
        output_line = f"[{ticker}] 🔴 SELL — score {score_int}/5 — thesis review needed"
    else:
        reasons = [b for b in score_breakdown if b]
        short_reason = reasons[0] if reasons else f"RSI {rsi:.0f}, analyst {upside_pct:.0f}% upside" if upside_pct else "no strong signals"
        output_line = f"[{ticker}] ✅ HOLD — {short_reason[:80]}"

    # Mark halal compliance
    signals["is_halal"] = ticker in HALAL_APPROVED or ticker.rstrip("-USD") in HALAL_APPROVED
    signals["is_core_etf"] = ticker in CORE_ETF_TICKERS

    return {
        "ticker": ticker,
        "score": score_int,
        "weighted_score_raw": round(weighted_score, 3),
        "factor_scores": {k: round(v, 3) for k, v in factor_raw_scores.items()},
        "signals": signals,
        "decision": decision,
        "output_line": output_line,
        "overlays_applied": overlays_applied,
        "score_breakdown": score_breakdown,
        "position_pct": round(position_pct, 2),
        "gain_pct": round(gain_pct, 2),
        "holding_value": round(holding_value, 2),
    }
