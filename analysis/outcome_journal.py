# -*- coding: utf-8 -*-
"""
outcome_journal.py — Logs every recommendation to logs/journal.jsonl.
Never raises — journal failure must not crash the orchestrator.
"""
import json
import os
from datetime import datetime

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
JOURNAL_PATH = os.path.join(LOGS_DIR, "journal.jsonl")


def log_recommendation(
    ticker: str,
    action: str,
    price: float,
    reasoning: str,
    factors: dict,
    horizon_days: int = 30,
) -> None:
    """Append one recommendation entry to logs/journal.jsonl."""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        entry = {
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ticker": ticker,
            "action": action,
            "price": round(float(price), 4) if price else None,
            "reasoning": reasoning,
            "factors": factors,
            "horizon_days": horizon_days,
        }
        with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


def log_batch(scored_holdings: list) -> int:
    """Log all scored holdings from a run. Returns count logged."""
    count = 0
    for h in scored_holdings:
        price = h.get("current_price")
        if not price:
            continue
        log_recommendation(
            ticker=h.get("ticker", ""),
            action=h.get("decision", "HOLD"),
            price=float(price),
            reasoning=h.get("output_line", ""),
            factors={
                "score": h.get("score"),
                "signals": h.get("signals", {}),
                "overlays": h.get("overlays_applied", []),
                "halal_ok": h.get("halal_ok"),
                "halal_status": h.get("halal_status"),
                "kelly": (h.get("math_metrics") or {}).get("kelly_fraction_capped"),
                "volatility_signal": (h.get("vol_forecast") or {}).get("signal"),
            },
            horizon_days=30,
        )
        count += 1
    return count
