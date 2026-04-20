"""
insiders.py — Scrapes OpenInsider for Form 4 insider transactions (90-day window).

Functions:
    get_insider_activity(ticker) -> dict
"""

import sys
from datetime import datetime, timedelta

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

OPENINSIDER_URL = "https://openinsider.com/screener?s={ticker}&fd=90&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=40&page=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

_EMPTY = {"has_buying": False, "recent_buys": [], "recent_sells": []}


def _parse_value(val_str: str) -> float:
    """Parse dollar/share strings like '$1,234,567' or '10,000' to float."""
    try:
        cleaned = val_str.replace("$", "").replace(",", "").replace("+", "").strip()
        return float(cleaned) if cleaned else 0.0
    except (ValueError, AttributeError):
        return 0.0


def get_insider_activity(ticker: str) -> dict:
    """
    Fetch 90-day insider activity for ticker from OpenInsider.

    Returns dict:
        has_buying (bool)
        recent_buys (list of {date, insider, title, shares, value, transaction_type})
        recent_sells (list of same structure)
        error (str, only if failed)
    """
    if requests is None or BeautifulSoup is None:
        return {**_EMPTY, "error": "requests/beautifulsoup4 not installed"}

    url = OPENINSIDER_URL.format(ticker=ticker)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[WARN] insiders.get_insider_activity({ticker}): request failed — {exc}", file=sys.stderr)
        return {**_EMPTY, "error": str(exc)}

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"class": "tinytable"})
        if not table:
            return {**_EMPTY, "error": "No insider table found"}

        rows = table.find_all("tr")[1:]  # skip header
        recent_buys = []
        recent_sells = []

        cutoff = datetime.now() - timedelta(days=90)

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 16:
                continue

            # Column indices based on OpenInsider table layout:
            # 1=filing date, 2=trade date, 5=company, 6=insider name, 7=title,
            # 9=transaction type, 11=shares, 12=price, 13=value
            try:
                trade_date_str = cells[2].get_text(strip=True)
                trade_date = datetime.strptime(trade_date_str, "%Y-%m-%d")
            except (ValueError, IndexError):
                try:
                    trade_date_str = cells[1].get_text(strip=True)
                    trade_date = datetime.strptime(trade_date_str[:10], "%Y-%m-%d")
                except Exception:
                    continue

            if trade_date < cutoff:
                continue

            try:
                insider_name = cells[6].get_text(strip=True) if len(cells) > 6 else "Unknown"
                title = cells[7].get_text(strip=True) if len(cells) > 7 else ""
                transaction_type = cells[9].get_text(strip=True) if len(cells) > 9 else ""
                shares_str = cells[11].get_text(strip=True) if len(cells) > 11 else "0"
                value_str = cells[13].get_text(strip=True) if len(cells) > 13 else "0"

                shares = _parse_value(shares_str)
                value = _parse_value(value_str)

                entry = {
                    "date": trade_date.strftime("%Y-%m-%d"),
                    "insider": insider_name,
                    "title": title,
                    "shares": shares,
                    "value": value,
                    "transaction_type": transaction_type,
                }

                # P = Purchase (buy), S = Sale (sell)
                t_upper = transaction_type.upper()
                if "P - PURCHASE" in t_upper or (transaction_type.startswith("P") and "S" not in t_upper[:2]):
                    recent_buys.append(entry)
                elif "S - SALE" in t_upper or transaction_type.startswith("S"):
                    recent_sells.append(entry)

            except Exception as parse_exc:
                print(f"[WARN] insiders: row parse error for {ticker}: {parse_exc}", file=sys.stderr)
                continue

        return {
            "has_buying": len(recent_buys) > 0,
            "recent_buys": recent_buys,
            "recent_sells": recent_sells,
        }

    except Exception as exc:
        print(f"[ERROR] insiders.get_insider_activity({ticker}): parse error — {exc}", file=sys.stderr)
        return {**_EMPTY, "error": str(exc)}
