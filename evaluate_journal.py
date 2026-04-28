#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
evaluate_journal.py — Weekly accuracy evaluator.
Reads logs/journal.jsonl, evaluates 30/90-day outcomes, appends to logs/accuracy.jsonl.
Run every Sunday via GHA weekly_backtest.yml.
"""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
JOURNAL = os.path.join(LOGS_DIR, "journal.jsonl")
ACCURACY = os.path.join(LOGS_DIR, "accuracy.jsonl")


def load_lines(path: str) -> list:
    lines = []
    if not os.path.exists(path):
        return lines
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            try:
                lines.append(json.loads(raw.strip()))
            except Exception:
                pass
    return lines


def already_evaluated(accuracy_entries: list) -> set:
    return {f"{e['original_ts']}_{e['ticker']}" for e in accuracy_entries}


def get_current_price(ticker: str) -> float | None:
    try:
        import yfinance as yf
        data = yf.download(ticker, period="2d", progress=False, auto_adjust=True)
        if data is None or len(data) == 0:
            return None
        return float(data["Close"].dropna().iloc[-1])
    except Exception:
        return None


def was_correct(action: str, entry_price: float, current_price: float) -> bool:
    ret = (current_price - entry_price) / entry_price
    if action == "BUY" and ret > 0.03:
        return True
    if action in ("SELL", "TRIM") and ret < -0.03:
        return True
    if action == "HOLD" and abs(ret) < 0.10:
        return True
    return False


def main():
    os.makedirs(LOGS_DIR, exist_ok=True)
    journal = load_lines(JOURNAL)
    accuracy = load_lines(ACCURACY)
    evaluated = already_evaluated(accuracy)

    now = datetime.utcnow()
    new_entries: list = []

    for entry in journal:
        try:
            ts_str = entry.get("ts", "")
            ticker = entry.get("ticker", "")
            action = entry.get("action", "HOLD")
            entry_price = float(entry.get("price") or 0)
            horizon = int(entry.get("horizon_days") or 30)

            key = f"{ts_str}_{ticker}"
            if key in evaluated or not entry_price:
                continue

            ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
            days_elapsed = (now - ts).days
            if days_elapsed < horizon:
                continue  # Horizon not yet reached

            current = get_current_price(ticker)
            if current is None:
                continue

            actual_return = (current - entry_price) / entry_price
            correct = was_correct(action, entry_price, current)

            new_entries.append({
                "evaluated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "original_ts": ts_str,
                "ticker": ticker,
                "action": action,
                "entry_price": entry_price,
                "current_price": round(current, 4),
                "actual_return": round(actual_return, 4),
                "actual_return_pct": round(actual_return * 100, 2),
                "horizon_days": horizon,
                "days_elapsed": days_elapsed,
                "correct": correct,
            })

        except Exception as e:
            print(f"  [evaluate] error on entry {entry.get('ticker')}: {e}", file=sys.stderr)

    if new_entries:
        with open(ACCURACY, "a", encoding="utf-8") as f:
            for e in new_entries:
                f.write(json.dumps(e, default=str) + "\n")

    # Summary stats
    all_acc = accuracy + new_entries
    if all_acc:
        n_correct = sum(1 for e in all_acc if e.get("correct"))
        rate = n_correct / len(all_acc)
        print(f"Accuracy journal: {len(all_acc)} evaluated, {rate:.1%} correct.")
    else:
        print("No entries yet past horizon.")

    print(f"New entries added: {len(new_entries)}")


if __name__ == "__main__":
    main()
