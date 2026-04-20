"""
politicians.py — Scrapes Capitol Trades for congressional trading activity.

Functions:
    get_politician_trades(ticker) -> dict
"""

import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

CAPITOL_TRADES_URL = "https://www.capitoltrades.com/trades?asset={ticker}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_EMPTY = {"has_buying": False, "trades": []}


def get_politician_trades(ticker: str) -> dict:
    """
    Fetch recent congressional trades for the given ticker from Capitol Trades.

    Returns dict:
        has_buying (bool) — True if any recent purchase found
        trades (list of {politician, date, type, amount})

    Returns empty dict on failure (non-critical data source).
    """
    if requests is None or BeautifulSoup is None:
        return _EMPTY

    url = CAPITOL_TRADES_URL.format(ticker=ticker)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[WARN] politicians.get_politician_trades({ticker}): {exc}", file=sys.stderr)
        return _EMPTY

    try:
        soup = BeautifulSoup(resp.text, "html.parser")

        trades = []
        # Capitol Trades uses various table/card layouts; try multiple selectors
        rows = soup.select("table tbody tr")
        if not rows:
            rows = soup.select(".trade-row")

        for row in rows[:20]:  # cap at 20 records
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            try:
                politician = cells[0].get_text(strip=True)
                date = cells[1].get_text(strip=True)
                trade_type = cells[2].get_text(strip=True)
                amount = cells[3].get_text(strip=True)

                trades.append({
                    "politician": politician,
                    "date": date,
                    "type": trade_type,
                    "amount": amount,
                })
            except Exception:
                continue

        has_buying = any(
            "purchase" in t.get("type", "").lower() or "buy" in t.get("type", "").lower()
            for t in trades
        )

        return {
            "has_buying": has_buying,
            "trades": trades,
        }

    except Exception as exc:
        print(f"[WARN] politicians.get_politician_trades({ticker}): parse error — {exc}", file=sys.stderr)
        return _EMPTY
