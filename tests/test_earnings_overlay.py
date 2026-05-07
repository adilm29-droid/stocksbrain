import sys, os, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.scorer import score_holding

def make_metrics(earnings_tickers):
    return {
        "total_value": 100_000, "cash_pct": 5.0,
        "earnings_next_7_days": earnings_tickers,
        "autopilot_tickers": set(), "direct_tickers": {"AMD"}
    }

def test_amd_earnings_in_5_days_forces_hold():
    """If AMD is in earnings_next_7_days, action MUST be HOLD regardless of score"""
    metrics = make_metrics(["AMD"])
    result = score_holding(
        ticker="AMD",
        holding_config={"shares": 4.33, "avg_cost": 100.0, "sector": "Technology", "bucket": "equity"},
        price_data={"price": 80.0, "rsi": 25.0, "sma200": 120.0},  # Oversold → would normally BUY
        analyst_data={"upside_pct": 35.0},
        insider_data={"has_buying": True},
        news_data={"thesis_break_flags": [], "earnings_beat_and_raised": False, "pe_doubled_from_entry": False},
        macro_data={},
        portfolio_metrics=metrics,
    )
    assert result["decision"] == "HOLD", f"Expected HOLD during earnings blackout, got {result['decision']}"
    assert any("earnings_freeze" in o for o in result["overlays_applied"]), "earnings_freeze overlay must be applied"

def test_ticker_not_in_blackout_is_unrestricted():
    """NVDA NOT in earnings blackout → normal scoring applies"""
    metrics = make_metrics([])  # No earnings blackout
    result = score_holding(
        ticker="NVDA",
        holding_config={"shares": 10.18, "avg_cost": 100.0, "sector": "Technology", "bucket": "equity"},
        price_data={"price": 80.0, "rsi": 25.0, "sma200": 60.0},
        analyst_data={"upside_pct": 40.0},
        insider_data={"has_buying": True},
        news_data={"thesis_break_flags": [], "earnings_beat_and_raised": True, "pe_doubled_from_entry": False},
        macro_data={},
        portfolio_metrics=metrics,
    )
    assert "earnings_freeze" not in str(result["overlays_applied"])
