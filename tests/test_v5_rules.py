import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rules_engine.v5_check import check_all_rules

BASE_PORTFOLIO = {"total_value": 100_000, "cash_pct": 5.0, "positions": {"AMD": {"position_pct": 4.0, "gain_pct": 30.0}}}

def test_amd_earnings_blackout_is_violation():
    """AMD trim 5 days before earnings → Rule 4 violation"""
    results = check_all_rules(
        portfolio=BASE_PORTFOLIO,
        ticker="AMD",
        action="TRIM",
        context={"earnings_next_7_days": ["AMD"], "data_points_count": 8}
    )
    rule4 = next(r for r in results if r["rule_id"] == 4)
    assert rule4["status"] == "violation", f"Expected violation for earnings blackout, got {rule4['status']}"
    assert "AMD" in rule4["reason"]

def test_no_violation_when_hold_during_blackout():
    """HOLD during earnings blackout → Rule 4 OK"""
    results = check_all_rules(
        portfolio=BASE_PORTFOLIO,
        ticker="AMD",
        action="HOLD",
        context={"earnings_next_7_days": ["AMD"], "data_points_count": 8}
    )
    rule4 = next(r for r in results if r["rule_id"] == 4)
    assert rule4["status"] == "ok"

def test_7_data_points_for_buy_is_violation():
    """7 data points for BUY → Rule 7 violation"""
    results = check_all_rules(
        portfolio=BASE_PORTFOLIO,
        ticker="NVDA",
        action="BUY",
        context={"data_points_count": 7, "earnings_next_7_days": []}
    )
    rule7 = next(r for r in results if r["rule_id"] == 7)
    assert rule7["status"] == "violation"

def test_8_data_points_for_buy_is_ok():
    """8 data points for BUY → Rule 7 OK"""
    results = check_all_rules(
        portfolio=BASE_PORTFOLIO,
        ticker="NVDA",
        action="BUY",
        context={"data_points_count": 8, "earnings_next_7_days": []}
    )
    rule7 = next(r for r in results if r["rule_id"] == 7)
    assert rule7["status"] == "ok"
