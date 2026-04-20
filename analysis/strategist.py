"""
strategist.py — Portfolio fit analysis for StocksBrain v2.

Functions:
    check_portfolio_fit(ticker, holding_config, all_holdings_with_prices, portfolio_metrics) -> dict
"""


def check_portfolio_fit(
    ticker: str,
    holding_config: dict,
    all_holdings_with_prices: dict,
    portfolio_metrics: dict,
) -> dict:
    """Check if adding more of this position makes strategic sense."""
    # Calculate current position size
    current_value = holding_config["shares"] * holding_config.get(
        "current_price", holding_config["avg_cost"]
    )
    position_pct = (
        current_value / portfolio_metrics["total_value"] * 100
        if portfolio_metrics["total_value"] > 0
        else 0
    )

    result = {
        "ticker": ticker,
        "current_position_pct": round(position_pct, 2),
        "headroom_to_cap": round(max(0, 7.0 - position_pct), 2),
        "fit_recommendation": "",
        "notes": [],
    }

    if position_pct >= 7.0:
        result["fit_recommendation"] = "AT_CAP"
        result["notes"].append(
            f"Position at {position_pct:.1f}% — at 7% concentration cap, do not add"
        )
    elif position_pct >= 5.0:
        result["fit_recommendation"] = "NEAR_CAP"
        result["notes"].append(
            f"Position at {position_pct:.1f}% — approaching 7% cap, add cautiously"
        )
    else:
        result["fit_recommendation"] = "HAS_ROOM"
        result["notes"].append(
            f"Position at {position_pct:.1f}% — has room to add up to {7.0 - position_pct:.1f}pp more"
        )

    return result
