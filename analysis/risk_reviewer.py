"""
risk_reviewer.py — Portfolio-level risk flag detection for StocksBrain v2.

Functions:
    review_portfolio_risk(scored_holdings, portfolio_metrics) -> list[dict]
"""


def review_portfolio_risk(scored_holdings: list, portfolio_metrics: dict) -> list:
    """Identify portfolio-level risk flags."""
    flags = []

    # Check each individual holding for concentration
    for h in scored_holdings:
        if h.get("position_pct", 0) > 7.0:
            flags.append(
                {
                    "flag": "CONCENTRATION",
                    "severity": "WARNING",
                    "detail": (
                        f"{h['ticker']} is {h['position_pct']:.1f}% of portfolio (cap: 7%)"
                    ),
                }
            )

    # Sector concentration (tech > 40%)
    tech_pct = portfolio_metrics.get("tech_pct", 0)
    if tech_pct > 40:
        flags.append(
            {
                "flag": "TECH_CONCENTRATION",
                "severity": "WARNING",
                "detail": f"Technology exposure at {tech_pct:.1f}% — above 40% threshold",
            }
        )

    # Crypto concentration (> 10%)
    crypto_pct = portfolio_metrics.get("crypto_pct", 0)
    if crypto_pct > 10:
        flags.append(
            {
                "flag": "CRYPTO_OVERWEIGHT",
                "severity": "INFO",
                "detail": f"Crypto at {crypto_pct:.1f}% — above 10% threshold",
            }
        )

    # Cash buffer
    if portfolio_metrics.get("cash_pct", 100) < 5.0:
        flags.append(
            {
                "flag": "LOW_CASH",
                "severity": "CRITICAL",
                "detail": (
                    f"Cash buffer at {portfolio_metrics.get('cash_pct', 0):.1f}%"
                    " — below 5% minimum"
                ),
            }
        )

    # Positions down > 50%
    for h in scored_holdings:
        if h.get("gain_pct", 0) < -50:
            flags.append(
                {
                    "flag": "DEEP_LOSS",
                    "severity": "WARNING",
                    "detail": (
                        f"{h['ticker']} down {abs(h.get('gain_pct', 0)):.1f}%"
                        " from cost basis — review thesis"
                    ),
                }
            )

    return flags
