"""
scorer.py — Core signal scoring engine for StocksBrain v2.

Functions:
    score_holding(ticker, holding_config, price_data, analyst_data,
                  insider_data, news_data, macro_data, portfolio_metrics) -> dict
"""

from config import CORE_ETF_TICKERS, THRESHOLDS


def score_holding(
    ticker: str,
    holding_config: dict,
    price_data: dict,
    analyst_data: dict,
    insider_data: dict,
    news_data: dict,
    macro_data: dict,
    portfolio_metrics: dict,
) -> dict:
    """
    Score a single holding and return a rich result dict.

    Returns:
        ticker           (str)
        score            (int)  -5 to +5
        signals          (dict) signal_name -> bool
        decision         (str)  BUY | HOLD | TRIM | SELL
        output_line      (str)  human-readable line for the briefing
        overlays_applied (list) names of overlays that changed the decision
        score_breakdown  (list) human-readable explanation of each scored signal
    """

    # ------------------------------------------------------------------ #
    # Helper: safe numeric access                                          #
    # ------------------------------------------------------------------ #
    def _f(d, key, default=0.0):
        v = d.get(key) if d else None
        return float(v) if v is not None else default

    # ------------------------------------------------------------------ #
    # Derived position metrics                                             #
    # ------------------------------------------------------------------ #
    price = _f(price_data, "price") or _f(holding_config, "avg_cost")
    avg_cost = float(holding_config.get("avg_cost", price or 1.0))
    shares = float(holding_config.get("shares", 0.0))
    holding_value = shares * price
    total_value = portfolio_metrics.get("total_value", 1.0) or 1.0
    position_pct = holding_value / total_value * 100 if total_value > 0 else 0.0
    gain_pct = (price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0.0

    rsi = _f(price_data, "rsi", 50.0)
    sma200 = _f(price_data, "sma200", 0.0)
    upside_pct = analyst_data.get("upside_pct")  # may be None
    has_buying = bool(insider_data.get("has_buying", False))
    earnings_beat_raised = bool(news_data.get("earnings_beat_and_raised", False))
    thesis_break_flags = news_data.get("thesis_break_flags", []) or []
    pe_doubled = bool(news_data.get("pe_doubled_from_entry", False))

    sector = holding_config.get("sector", "")
    sector_rotation_signal = macro_data.get("sector_rotation_signal", {}) if macro_data else {}
    sector_signal = sector_rotation_signal.get(sector, "NEUTRAL") if sector else "NEUTRAL"

    # ------------------------------------------------------------------ #
    # Evaluate individual signals                                          #
    # ------------------------------------------------------------------ #
    signals: dict[str, bool] = {}
    score_breakdown: list[str] = []
    score = 0

    # --- BUY signals (+1 each) ---

    # 1. RSI healthy pullback + above 200MA
    rsi_healthy = rsi < THRESHOLDS["rsi_oversold"] and (sma200 == 0.0 or price > sma200)
    signals["rsi_healthy_pullback"] = rsi_healthy
    if rsi_healthy:
        score += 1
        score_breakdown.append(f"+1 RSI oversold ({rsi:.1f}) and above 200MA")

    # 2. Analyst upside strong
    analyst_strong = (upside_pct is not None) and (upside_pct > THRESHOLDS["analyst_upside_buy"])
    signals["analyst_upside_strong"] = analyst_strong
    if analyst_strong:
        score += 1
        score_breakdown.append(f"+1 Analyst upside {upside_pct:.1f}% > {THRESHOLDS['analyst_upside_buy']}%")

    # 3. Insider buying
    signals["insider_buying"] = has_buying
    if has_buying:
        score += 1
        score_breakdown.append("+1 Insider buying detected (last 90 days)")

    # 4. Earnings beat and raised guidance
    signals["earnings_beat_raised"] = earnings_beat_raised
    if earnings_beat_raised:
        score += 1
        score_breakdown.append("+1 Earnings beat with raised guidance")

    # 5. Sector rotation favorable
    sector_favorable = sector_signal == "FAVORABLE"
    signals["sector_rotation_favorable"] = sector_favorable
    if sector_favorable:
        score += 1
        score_breakdown.append(f"+1 Sector rotation favorable for {sector or 'this sector'}")

    # --- SELL signals (-1 each) ---

    # 1. RSI overbought
    rsi_ob = rsi > THRESHOLDS["rsi_overbought"]
    signals["rsi_overbought"] = rsi_ob
    if rsi_ob:
        score -= 1
        score_breakdown.append(f"-1 RSI overbought ({rsi:.1f} > {THRESHOLDS['rsi_overbought']})")

    # 2. P/E doubled from entry
    signals["pe_doubled"] = pe_doubled
    if pe_doubled:
        score -= 1
        score_breakdown.append("-1 P/E ratio has doubled since entry")

    # 3. Analyst upside weak
    analyst_weak = (upside_pct is not None) and (upside_pct < THRESHOLDS["analyst_upside_sell"])
    signals["analyst_upside_weak"] = analyst_weak
    if analyst_weak:
        score -= 1
        score_breakdown.append(f"-1 Analyst upside only {upside_pct:.1f}% < {THRESHOLDS['analyst_upside_sell']}%")

    # 4. Concentration risk
    concentration_risky = position_pct > THRESHOLDS["concentration_cap"]
    signals["concentration_risk"] = concentration_risky
    if concentration_risky:
        score -= 1
        score_breakdown.append(
            f"-1 Concentration {position_pct:.1f}% > {THRESHOLDS['concentration_cap']}% cap"
        )

    # 5. Thesis break
    thesis_broken = len(thesis_break_flags) > 0
    signals["thesis_break"] = thesis_broken
    if thesis_broken:
        score -= 1
        score_breakdown.append(f"-1 Thesis-break flags: {', '.join(thesis_break_flags[:3])}")

    # 6. Large gain only penalised when thesis is genuinely broken
    # (guidance cut / CEO change / regulatory) — not for pure technical signals.
    # This prevents winners from flipping to SELL just because RSI ran hot.
    large_gain_sell = (gain_pct > THRESHOLDS["gain_trim_threshold"]) and thesis_broken
    signals["large_gain_with_sell_signal"] = large_gain_sell
    if large_gain_sell:
        score -= 1
        score_breakdown.append(
            f"-1 Large gain ({gain_pct:.1f}%) combined with thesis-break signal"
        )

    # Flag core ETF membership (used by bug_hunter)
    signals["is_core_etf"] = ticker in CORE_ETF_TICKERS

    # ------------------------------------------------------------------ #
    # Clamp score                                                          #
    # ------------------------------------------------------------------ #
    score = max(-5, min(5, score))

    # ------------------------------------------------------------------ #
    # Decision table                                                       #
    # ------------------------------------------------------------------ #
    if score >= 3:
        decision = "BUY"
    elif score >= 1:
        decision = "HOLD"
    elif score == 0:
        decision = "HOLD"
    elif score >= -2:
        decision = "TRIM"
    else:
        decision = "SELL"

    overlays_applied: list[str] = []

    # ------------------------------------------------------------------ #
    # Overlays (applied in order, may downgrade decision)                  #
    # ------------------------------------------------------------------ #

    # Overlay 1: Autopilot tickers — downgrade SELL -> HOLD
    autopilot_tickers = portfolio_metrics.get("autopilot_tickers", set())
    if ticker in autopilot_tickers:
        if decision == "SELL":
            decision = "HOLD"
            overlays_applied.append("autopilot_sell_downgraded_to_hold")
        # TRIM only allowed if also in HOLDINGS — autopilot portfolios are not
        # direct HOLDINGS, so block TRIM too for pure autopilot entries
        if decision == "TRIM" and ticker not in portfolio_metrics.get("direct_tickers", set()):
            decision = "HOLD"
            overlays_applied.append("autopilot_trim_downgraded_to_hold")

    # Overlay 2: Earnings in next 7 days — freeze all decisions to HOLD
    earnings_next_7 = portfolio_metrics.get("earnings_next_7_days", [])
    if ticker in earnings_next_7:
        if decision != "HOLD":
            overlays_applied.append(f"earnings_freeze_{decision}_to_HOLD")
            decision = "HOLD"

    # Overlay 3: Low cash + BUY — keep BUY but add note
    cash_pct = portfolio_metrics.get("cash_pct", 100.0)
    low_cash_flag = ""
    if cash_pct < 5.0 and decision == "BUY":
        overlays_applied.append("low_cash_add_on_dip")
        low_cash_flag = " (add on dip — low cash)"

    # Overlay 4: Core ETF — SELL/TRIM -> HOLD
    if ticker in CORE_ETF_TICKERS:
        if decision in ("SELL", "TRIM"):
            overlays_applied.append(f"core_etf_{decision}_downgraded_to_HOLD")
            decision = "HOLD"

    # ------------------------------------------------------------------ #
    # Build reason sentence                                                #
    # ------------------------------------------------------------------ #
    reason_parts = []

    if score_breakdown:
        # Pick the most impactful breakdowns (first buy and first sell)
        positives = [b for b in score_breakdown if b.startswith("+")]
        negatives = [b for b in score_breakdown if b.startswith("-")]
        if positives:
            # Strip the "+1 " prefix for readability
            reason_parts.append(positives[0][3:].capitalize())
        if negatives:
            reason_parts.append(negatives[0][3:].capitalize())
    else:
        if upside_pct is not None:
            reason_parts.append(f"analyst upside {upside_pct:.1f}%")
        if rsi != 50.0:
            reason_parts.append(f"RSI {rsi:.1f}")

    if not reason_parts:
        reason_parts.append("no strong signals")

    reason = "; ".join(reason_parts)

    # ------------------------------------------------------------------ #
    # Output line format                                                   #
    # ------------------------------------------------------------------ #
    if decision == "BUY":
        dip_price = price * 0.97
        output_line = (
            f"💰 BUY on dip below ${dip_price:.2f}{low_cash_flag} — {reason}"
        )
    elif decision == "HOLD":
        rsi_note = f"RSI {rsi:.1f}"
        upside_note = f"analyst upside {upside_pct:.1f}%" if upside_pct is not None else "no analyst data"
        if reason_parts and reason_parts[0] not in ("no strong signals",):
            output_line = f"✅ HOLD — {reason}"
        else:
            output_line = f"✅ HOLD — {rsi_note}, {upside_note}"
    elif decision == "TRIM":
        output_line = f"⚠️ TRIM 25% — {reason} (current price ${price:.2f})"
    else:  # SELL
        output_line = f"🔴 SELL — {reason}"

    # Prefix ticker for clarity
    output_line = f"[{ticker}] {output_line}"

    return {
        "ticker": ticker,
        "score": score,
        "signals": signals,
        "decision": decision,
        "output_line": output_line,
        "overlays_applied": overlays_applied,
        "score_breakdown": score_breakdown,
        # Pass through for use by orchestrator / risk_reviewer
        "position_pct": round(position_pct, 2),
        "gain_pct": round(gain_pct, 2),
        "holding_value": round(holding_value, 2),
    }
