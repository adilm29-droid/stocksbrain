"""
Allocation Rails — hardcoded portfolio safety constraints for Adil's Wio portfolio.
These CANNOT be overridden by any signal, no matter how strong.
"""

ALLOCATION_RAILS = {
    # Foundation layer (Layer 1 — 95% of capital)
    "core_etfs_min_pct": 40,          # SPUS+HLAL+URTH+autopilots combined
    "core_etfs_max_pct": 70,
    "single_stock_max_pct": 7.0,       # any single direct equity
    "crypto_max_pct": 12.0,            # all crypto combined
    "crypto_alt_max_pct": 2.0,         # XRP+SOL individually

    # Moonshot layer (Layer 2 — max 5%)
    "moonshot_total_max_pct": 5.0,
    "moonshot_single_max_pct": 1.5,
    "moonshot_total_max_usd": 2500.0,

    # Cash buffer
    "cash_buffer_target_usd": 1500.0,
    "cash_buffer_min_usd": 500.0,

    # Halal compliance (non-negotiable)
    "halal_only": True,

    # Trade frequency
    "max_new_buys_per_week": 1,
    "earnings_freeze_days": 7,  # No trades 7 days before earnings
}


def check_rails(
    action: str,
    ticker: str,
    position_pct: float,
    cash_usd: float,
    portfolio_total: float,
    is_moonshot: bool = False,
    is_halal: bool = True,
    current_moonshot_total_usd: float = 0.0,
) -> dict:
    """
    Check if a proposed action violates allocation rails.
    Returns: {allowed: bool, blocked_reason: str | None, downgraded_to: str | None}
    """
    rails = ALLOCATION_RAILS

    # Rail 1: Halal compliance
    if not is_halal:
        return {"allowed": False, "blocked_reason": "Halal violation — ticker not in approved list", "downgraded_to": None}

    # Rail 2: Cash buffer must be filled before any BUY
    if action in ("BUY", "ADD_TO", "NEW_BUY", "MOONSHOT") and cash_usd < rails["cash_buffer_min_usd"]:
        return {
            "allowed": False,
            "blocked_reason": f"Cash buffer ${cash_usd:.0f} below minimum ${rails['cash_buffer_min_usd']:.0f}",
            "downgraded_to": "HOLD",
        }

    # Rail 3: Single stock cap
    if action in ("BUY", "ADD_TO", "NEW_BUY") and position_pct > rails["single_stock_max_pct"]:
        return {
            "allowed": False,
            "blocked_reason": f"Position {position_pct:.1f}% exceeds {rails['single_stock_max_pct']}% single-stock cap",
            "downgraded_to": "HOLD",
        }

    # Rail 4: Moonshot bucket limits
    if is_moonshot:
        if current_moonshot_total_usd >= rails["moonshot_total_max_usd"]:
            return {
                "allowed": False,
                "blocked_reason": f"Moonshot bucket full (${current_moonshot_total_usd:.0f} / ${rails['moonshot_total_max_usd']:.0f})",
                "downgraded_to": "HOLD",
            }
        if cash_usd < rails["cash_buffer_target_usd"]:
            return {
                "allowed": False,
                "blocked_reason": f"Moonshot locked — cash buffer ${cash_usd:.0f} below target ${rails['cash_buffer_target_usd']:.0f}",
                "downgraded_to": "HOLD",
            }

    return {"allowed": True, "blocked_reason": None, "downgraded_to": None}


def get_rails_status(portfolio_metrics: dict) -> dict:
    """Return current rail compliance status for dashboard display."""
    cash = portfolio_metrics.get("cash_usd", 0)
    total = portfolio_metrics.get("total_value", 1)

    moonshot_locked = cash < ALLOCATION_RAILS["cash_buffer_target_usd"]
    cash_critical = cash < ALLOCATION_RAILS["cash_buffer_min_usd"]

    return {
        "cash_buffer_status": {
            "current": cash,
            "target": ALLOCATION_RAILS["cash_buffer_target_usd"],
            "min": ALLOCATION_RAILS["cash_buffer_min_usd"],
            "gap": max(0, ALLOCATION_RAILS["cash_buffer_target_usd"] - cash),
            "critical": cash_critical,
        },
        "moonshot_bucket": {
            "locked": moonshot_locked,
            "lock_reason": "Fill cash buffer to $1,500 first" if moonshot_locked else None,
        },
        "halal_only": ALLOCATION_RAILS["halal_only"],
        "single_stock_cap": ALLOCATION_RAILS["single_stock_max_pct"],
        "crypto_cap": ALLOCATION_RAILS["crypto_max_pct"],
    }
