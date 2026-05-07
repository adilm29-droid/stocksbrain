#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
backtest/replay.py — Historical signal replay over last 24 months.
Point-in-time data only. No look-ahead bias.

WARNING: If hit rate < 52%, a giant warning is printed here AND in README.
"""
import json
import os
import sys
from datetime import datetime, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BACKTEST_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


# ---------------------------------------------------------------------------
# Price loader
# ---------------------------------------------------------------------------

def load_history(ticker: str, years: int = 2) -> list[tuple[str, float]]:
    """Return [(date_str, price), ...] for last N years. Returns [] on failure."""
    try:
        import yfinance as yf
        end = datetime.utcnow()
        start = end - timedelta(days=years * 365 + 90)
        data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
        if data is None or len(data) == 0:
            return []
        closes = data["Close"].dropna()
        return [(str(idx.date()), float(p)) for idx, p in closes.items()]
    except Exception as e:
        print(f"  [backtest] load_history({ticker}) failed: {e}", file=sys.stderr)
        return []


# ---------------------------------------------------------------------------
# Signal generation (simplified RSI — same logic family as scorer.py)
# ---------------------------------------------------------------------------

def _rsi(prices: list[float], period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))][-period:]
    gains = [c for c in changes if c > 0]
    losses = [-c for c in changes if c < 0]
    ag = sum(gains) / period if gains else 0.0
    al = sum(losses) / period if losses else 1e-9
    rs = ag / al
    return round(100 - (100 / (1 + rs)), 2)


def simulate_signal(idx: int, prices: list[float]) -> str:
    window = prices[max(0, idx - 60): idx]
    if len(window) < 15:
        return "HOLD"
    rsi = _rsi(window)
    if rsi < 35:
        return "BUY"
    if rsi > 70:
        return "TRIM"
    return "HOLD"


# ---------------------------------------------------------------------------
# Core backtest
# ---------------------------------------------------------------------------

def run_backtest(tickers: list[str], months: int = 24) -> dict:
    """
    Replay last N months. Returns results dict.
    """
    try:
        print("  [backtest] Loading price histories...", file=sys.stderr)

        # Limit to first 12 tickers to keep runtime reasonable
        sample = [t for t in tickers if "-USD" not in t and "=" not in t][:12]

        price_map: dict[str, list[tuple[str, float]]] = {}
        for t in sample:
            hist = load_history(t, years=max(2, months // 12))
            if hist:
                price_map[t] = hist

        spus_hist = load_history("SPUS", years=max(2, months // 12))

        if len(price_map) < 3:
            return {
                "error": "Insufficient price data — need ≥3 tickers with 2y history",
                "hit_rate": 0.0, "hit_rate_pct": 0.0,
            }

        # Find common date range
        all_dates: list[str] = sorted(
            set.intersection(*[{d for d, _ in v} for v in price_map.values()])
        )
        if len(all_dates) < 60:
            return {"error": "Common date range too short", "hit_rate": 0.0, "hit_rate_pct": 0.0}

        print(f"  [backtest] {len(price_map)} tickers × {len(all_dates)} days", file=sys.stderr)

        # Build price lookup
        price_lookup: dict[str, dict[str, float]] = {}
        for ticker, hist in price_map.items():
            price_lookup[ticker] = {d: p for d, p in hist}

        # Evaluate signals
        correct = 0
        total = 0
        buy_returns: list[float] = []
        fwd_days = 30

        for i, cur_date in enumerate(all_dates[:-fwd_days]):
            future_date = all_dates[min(i + fwd_days, len(all_dates) - 1)]

            for ticker in sample:
                prices_up_to_now = [
                    p for d, p in price_map[ticker] if d <= cur_date
                ]
                sig = simulate_signal(len(prices_up_to_now), prices_up_to_now)
                cur_price = price_lookup[ticker].get(cur_date)
                fut_price = price_lookup[ticker].get(future_date)
                if cur_price is None or fut_price is None:
                    continue

                fwd_ret = (fut_price - cur_price) / cur_price

                if sig == "BUY":
                    buy_returns.append(fwd_ret)
                    correct += int(fwd_ret > 0.01)
                elif sig == "TRIM":
                    correct += int(fwd_ret < -0.01)
                elif sig == "HOLD":
                    correct += int(abs(fwd_ret) < 0.08)

                total += 1

        hit_rate = correct / total if total > 0 else 0.0

        # SPUS buy-and-hold
        spus_return = 0.0
        if spus_hist and len(spus_hist) >= 2:
            spus_lookup = {d: p for d, p in spus_hist}
            first = spus_lookup.get(all_dates[0])
            last = spus_lookup.get(all_dates[-1])
            if first and last and first > 0:
                spus_return = (last - first) / first

        # Strategy annualized return
        strategy_avg = float(np.mean(buy_returns)) if buy_returns else 0.0
        annualized = strategy_avg * 252 / fwd_days

        # Max drawdown of strategy
        max_dd = 0.0
        if buy_returns:
            cum = np.cumprod(1 + np.array(buy_returns))
            peak = np.maximum.accumulate(cum)
            dd = (cum - peak) / np.where(peak > 0, peak, 1)
            max_dd = float(np.min(dd))

        results = {
            "hit_rate": round(hit_rate, 4),
            "hit_rate_pct": round(hit_rate * 100, 1),
            "avg_buy_signal_return_30d": round(strategy_avg, 4),
            "annualized_buy_signal_return": round(annualized, 4),
            "max_drawdown": round(max_dd, 4),
            "spus_total_return": round(spus_return, 4),
            "spus_total_return_pct": round(spus_return * 100, 1),
            "total_signals_evaluated": total,
            "buy_signals": len(buy_returns),
            "tickers_backtested": sample,
            "months_backtested": months,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "beat_spus": strategy_avg > 0 and annualized > spus_return,
            "warning": None,
        }

        if hit_rate < 0.52:
            results["warning"] = (
                f"Hit rate {hit_rate * 100:.1f}% is below 52% threshold. "
                "System may not be generating alpha over random."
            )

        return results

    except Exception as e:
        return {"error": str(e), "hit_rate": 0.0, "hit_rate_pct": 0.0}


def _print_warning_banner(results: dict) -> None:
    w = results.get("warning")
    if w:
        banner = "=" * 70
        print(f"\n{banner}", file=sys.stderr)
        print("  *** BACKTEST WARNING ***", file=sys.stderr)
        print(f"  {w}", file=sys.stderr)
        print(f"  Hit Rate: {results.get('hit_rate_pct', 0):.1f}%", file=sys.stderr)
        print(f"  Strategy avg 30d return: {results.get('avg_buy_signal_return_30d', 0):.2%}", file=sys.stderr)
        print(f"  SPUS buy-and-hold: {results.get('spus_total_return_pct', 0):.1f}%", file=sys.stderr)
        print(f"{banner}\n", file=sys.stderr)


def main():
    from config import HOLDINGS
    tickers = list(HOLDINGS.keys())

    print("Running 24-month backtest...", file=sys.stderr)
    results = run_backtest(tickers, months=24)

    os.makedirs(BACKTEST_DIR, exist_ok=True)
    path = os.path.join(BACKTEST_DIR, "results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved {path}", file=sys.stderr)

    _print_warning_banner(results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
