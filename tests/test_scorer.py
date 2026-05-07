import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from analysis.scorer import score_holding

BASE_METRICS = {"total_value": 100_000, "cash_pct": 5.0, "earnings_next_7_days": [], "autopilot_tickers": set(), "direct_tickers": {"AMD", "PLTR"}}

def test_amd_up60_rsi75_no_thesis_break_does_not_trigger_sell_rule():
    """AMD up 60%, RSI 75, no thesis break → large_gain_with_sell_signal must be False"""
    result = score_holding(
        ticker="AMD",
        holding_config={"shares": 4.33, "avg_cost": 100.0, "sector": "Technology", "bucket": "equity"},
        price_data={"price": 160.0, "rsi": 75.0, "sma200": 120.0},
        analyst_data={"upside_pct": 10.0},
        insider_data={"has_buying": False},
        news_data={"thesis_break_flags": [], "earnings_beat_and_raised": False, "pe_doubled_from_entry": False},
        macro_data={},
        portfolio_metrics=BASE_METRICS,
    )
    assert result["signals"]["large_gain_with_sell_signal"] is False, "large gain without thesis break must NOT trigger sell rule"
    assert result["decision"] != "SELL", "Should not be SELL on RSI alone with 60% gain"

def test_amd_up60_rsi75_ceo_resigned_triggers_sell():
    """AMD up 60%, RSI 75, thesis break 'CEO resigned' → sell triggers correctly"""
    result = score_holding(
        ticker="AMD",
        holding_config={"shares": 4.33, "avg_cost": 100.0, "sector": "Technology", "bucket": "equity"},
        price_data={"price": 160.0, "rsi": 75.0, "sma200": 120.0},
        analyst_data={"upside_pct": 10.0},
        insider_data={"has_buying": False},
        news_data={"thesis_break_flags": ["CEO resigned"], "earnings_beat_and_raised": False, "pe_doubled_from_entry": False},
        macro_data={},
        portfolio_metrics=BASE_METRICS,
    )
    assert result["signals"]["thesis_break"] is True
    assert result["signals"]["large_gain_with_sell_signal"] is True, "large gain WITH thesis break should trigger sell rule"

def test_pltr_up30_rsi65_no_sell():
    """PLTR up 30%, RSI 65 → no sell (under 50% threshold)"""
    result = score_holding(
        ticker="PLTR",
        holding_config={"shares": 5.09, "avg_cost": 130.0, "sector": "Technology", "bucket": "equity"},
        price_data={"price": 169.0, "rsi": 65.0, "sma200": 140.0},
        analyst_data={"upside_pct": 12.0},
        insider_data={"has_buying": False},
        news_data={"thesis_break_flags": [], "earnings_beat_and_raised": False, "pe_doubled_from_entry": False},
        macro_data={},
        portfolio_metrics=BASE_METRICS,
    )
    assert result["signals"]["large_gain_with_sell_signal"] is False
    assert result["decision"] in ("HOLD", "TRIM", "BUY"), "Should not be SELL at 30% gain"
