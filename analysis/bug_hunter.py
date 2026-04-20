"""
bug_hunter.py — Logical contradiction detection for StocksBrain v2.

Functions:
    hunt_contradictions(scored_holdings) -> list[str]
"""


def hunt_contradictions(scored_holdings: list) -> list:
    """Catch logical contradictions in the signal output."""
    contradictions = []

    for h in scored_holdings:
        ticker = h.get("ticker", "?")
        score = h.get("score", 0)
        decision = h.get("decision", "HOLD")
        signals = h.get("signals", {})

        # BUY decision but overbought
        if decision == "BUY" and signals.get("rsi_overbought"):
            contradictions.append(
                f"{ticker}: BUY signal but RSI > 70 (overbought) — check overlay logic"
            )

        # SELL on a core ETF
        if decision == "SELL" and signals.get("is_core_etf"):
            contradictions.append(
                f"{ticker}: SELL on a core ETF — overlay should have blocked this"
            )

        # Score says strong sell but decision is HOLD
        if score <= -3 and decision == "HOLD":
            overlays = h.get("overlays_applied", [])
            if not overlays:
                contradictions.append(
                    f"{ticker}: Score {score} (strong sell) but HOLD with no overlay explanation"
                )

        # Score says strong buy but decision is not BUY
        if score >= 3 and decision != "BUY":
            overlays = h.get("overlays_applied", [])
            if not overlays:
                contradictions.append(
                    f"{ticker}: Score {score} (strong buy) but not BUY — missing overlay?"
                )

        # Thesis break + BUY
        if decision == "BUY" and signals.get("thesis_break"):
            contradictions.append(
                f"{ticker}: BUY recommended despite thesis-break flag in news"
            )

    return contradictions
