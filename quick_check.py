#!/usr/bin/env python3
"""Quick hourly price check — no heavy data fetching."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOLDINGS
from data_sources.prices import get_price_data


def main():
    print(f"{'Ticker':<10} {'Price':>10} {'Change%':>9} {'RSI':>6} {'vs200MA':>9}")
    print("-" * 50)
    for ticker, cfg in HOLDINGS.items():
        data = get_price_data(ticker, period="1mo")
        if not data:
            print(f"{ticker:<10} {'ERROR':>10}")
            continue
        price = data.get("price", 0)
        change = data.get("change_pct", 0)
        rsi = data.get("rsi", 0)
        sma200 = data.get("sma200", 0)
        vs200 = ((price - sma200) / sma200 * 100) if sma200 else 0
        rsi_flag = "WARNING" if rsi > 70 or rsi < 35 else "  "
        print(
            f"{ticker:<10} {price:>10.2f} {change:>+8.2f}% {rsi:>5.1f}"
            f" {vs200:>+8.1f}% {rsi_flag}"
        )


if __name__ == "__main__":
    main()
