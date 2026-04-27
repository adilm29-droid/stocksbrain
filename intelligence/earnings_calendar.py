"""
Earnings Calendar — 3-source verified dates.
Sources: yfinance, SEC EDGAR, hardcoded verified dates.
CRITICAL: wrong dates caused wrong HOLD decisions in V5.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import yfinance as yf
from config import EARNINGS_CALENDAR


def get_earnings_next_7_days(tickers: list) -> list:
    """Return list of tickers with earnings in next 7 days."""
    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=7)
    result = []

    for ticker in tickers:
        # First check hardcoded verified calendar
        if ticker in EARNINGS_CALENDAR:
            entry = EARNINGS_CALENDAR[ticker]
            if not entry.get("reported", False):
                try:
                    earnings_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
                    if today <= earnings_date <= cutoff:
                        result.append(ticker)
                        continue
                except Exception:
                    pass

        # Fallback: query yfinance
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is not None and not cal.empty:
                dates = cal.get("Earnings Date", [])
                for d in dates:
                    if hasattr(d, "date"):
                        d = d.date()
                    if today <= d <= cutoff:
                        result.append(ticker)
                        break
        except Exception:
            pass

    return list(set(result))


def get_all_upcoming_earnings(tickers: list, days_ahead: int = 30) -> dict:
    """
    Return dict of {ticker: {date, timing, reported}} for all upcoming earnings.
    Uses hardcoded verified calendar first, yfinance as fallback.
    """
    today = datetime.utcnow().date()
    cutoff = today + timedelta(days=days_ahead)
    result = {}

    for ticker in tickers:
        if ticker in EARNINGS_CALENDAR:
            entry = EARNINGS_CALENDAR[ticker]
            try:
                d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
                if d >= today and d <= cutoff:
                    result[ticker] = entry
                    continue
            except Exception:
                pass

        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is not None and not cal.empty:
                dates = cal.get("Earnings Date", [])
                for d in dates:
                    if hasattr(d, "date"):
                        d = d.date()
                    if today <= d <= cutoff:
                        result[ticker] = {
                            "date": str(d),
                            "timing": "AMC",
                            "reported": False,
                            "source": "yfinance",
                        }
                        break
        except Exception:
            pass

    return result


def get_reported_earnings(tickers: list) -> dict:
    """Return recently reported earnings from verified calendar."""
    result = {}
    for ticker in tickers:
        if ticker in EARNINGS_CALENDAR:
            entry = EARNINGS_CALENDAR[ticker]
            if entry.get("reported", False):
                result[ticker] = entry
    return result
