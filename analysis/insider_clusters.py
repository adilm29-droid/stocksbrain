# -*- coding: utf-8 -*-
"""
insider_clusters.py — Detects bullish insider buying clusters.
Cluster = ≥3 insiders at same company buying within 30 days, total ≥$500K.
"""
from datetime import datetime, timedelta


def detect_insider_clusters(insider_cache: dict) -> list:
    """
    insider_cache: {ticker: data dict from data_sources/insiders.py}
    Returns list of cluster dicts. Never raises.
    """
    clusters = []
    try:
        cutoff = datetime.utcnow() - timedelta(days=30)

        for ticker, data in insider_cache.items():
            if not data:
                continue

            # ---- Path A: structured recent_buys list ----
            recent_buys = data.get("recent_buys") or []
            if recent_buys:
                window = []
                for buy in recent_buys:
                    try:
                        tx_type = (buy.get("transaction_type") or "").upper()
                        if tx_type not in ("P", "BUY", "PURCHASE"):
                            continue
                        date_str = buy.get("date") or buy.get("startDate") or ""
                        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
                        if d >= cutoff:
                            window.append(buy)
                    except Exception:
                        continue

                if len(window) >= 3:
                    total_val = sum(float(b.get("value", 0) or 0) for b in window)
                    if total_val >= 500_000:
                        clusters.append(_make_cluster(ticker, len(window), total_val))
                continue

            # ---- Path B: summary flags only ----
            if (
                data.get("has_buying")
                and int(data.get("buy_count") or 0) >= 3
                and float(data.get("total_buy_value") or 0) >= 500_000
            ):
                clusters.append(
                    _make_cluster(
                        ticker,
                        int(data.get("buy_count", 3)),
                        float(data.get("total_buy_value", 500_000)),
                    )
                )

    except Exception:
        pass

    return clusters


def _make_cluster(ticker: str, count: int, total_value: float) -> dict:
    return {
        "ticker": ticker,
        "insider_count": count,
        "total_value": round(total_value, 2),
        "signal": "CLUSTER_BUY",
        "weight_multiplier": 1.5,
        "description": f"{count} insiders buying within 30d — total ${total_value:,.0f}",
    }
