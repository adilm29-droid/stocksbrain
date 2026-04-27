"""
Congressional Trading Intelligence — Capitol Trades scraper.
Public disclosure data. 30-45 day lag. Use as confirmation, not standalone signal.
Source: capitoltrades.com (public data)
"""
import requests
from datetime import datetime, timedelta


CAPITOL_TRADES_API = "https://api.capitoltrades.com/v2/trades?politician=all&size=100"


def get_congress_trades(ticker: str, days: int = 45) -> dict:
    """
    Get congressional trades for a ticker.
    Returns: {trade_count, buy_count, sell_count, total_value,
              politicians, has_cluster, committees}
    Note: 30-45 day disclosure lag — use as thesis confirmation only.
    """
    try:
        resp = requests.get(
            CAPITOL_TRADES_API,
            params={"ticker": ticker},
            timeout=15,
            headers={"User-Agent": "StocksBrain/2.0 research-bot", "Accept": "application/json"},
        )
        if resp.status_code != 200:
            return _empty_result()

        data = resp.json()
        trades_raw = data.get("data", [])

        cutoff = datetime.utcnow() - timedelta(days=days)
        trades = []
        for t in trades_raw:
            try:
                filed_date = datetime.fromisoformat(t.get("filedAt", "").replace("Z", "+00:00"))
                if filed_date.replace(tzinfo=None) < cutoff:
                    continue
                trades.append({
                    "politician": t.get("politician", {}).get("name", "Unknown"),
                    "party": t.get("politician", {}).get("party", ""),
                    "type": "BUY" if t.get("type") == "purchase" else "SELL",
                    "amount": t.get("amount", 0),
                    "committees": t.get("politician", {}).get("committees", []),
                })
            except Exception:
                continue

        buys = [t for t in trades if t["type"] == "BUY"]
        sells = [t for t in trades if t["type"] == "SELL"]
        total_value = sum(t.get("amount", 0) for t in trades)

        # Cluster: 3+ politicians same ticker = meaningful signal
        has_cluster = len(trades) >= 3

        return {
            "trade_count": len(trades),
            "buy_count": len(buys),
            "sell_count": len(sells),
            "total_value": total_value,
            "politicians": list({t["politician"] for t in trades}),
            "has_cluster": has_cluster,
            "committees": list({c for t in trades for c in t.get("committees", [])}),
            "caveat": "30-45 day disclosure lag. Use as confirmation only.",
        }

    except Exception as e:
        return _empty_result(error=str(e))


def _empty_result(error=None):
    return {
        "trade_count": 0, "buy_count": 0, "sell_count": 0,
        "total_value": 0, "politicians": [], "has_cluster": False,
        "committees": [],
        "caveat": "30-45 day disclosure lag. Use as confirmation only.",
        "error": error,
    }
