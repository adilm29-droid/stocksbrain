"""
Insider Trading Intelligence — SEC EDGAR Form 4 cluster detection.
Cluster buy: 3+ insiders, 30 days, total >$1M = STRONG +2 signal.
Cluster sell: single sells often = compensation, not bearish.
Source: openinsider.com (free scraping) + SEC EDGAR.
"""
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


OPENINSIDER_URL = "http://openinsider.com/screener?s={ticker}&o=&pl=&ph=&ll=&lh=&fd=30&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=20&page=1"

OFFICER_WEIGHTS = {
    "CEO": 2.0, "CFO": 1.8, "President": 1.5, "COO": 1.5,
    "Director": 1.0, "EVP": 1.2, "SVP": 1.0, "VP": 0.8,
}


def _scrape_openinsider(ticker: str, days: int = 30) -> list:
    """Scrape openinsider.com for recent insider transactions."""
    try:
        url = OPENINSIDER_URL.format(ticker=ticker)
        resp = requests.get(url, timeout=10,
                            headers={"User-Agent": "StocksBrain/2.0 research-bot"})
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="tinytable")
        if not table:
            return []

        trades = []
        cutoff = datetime.utcnow() - timedelta(days=days)
        rows = table.find_all("tr")[1:]  # skip header

        for row in rows[:20]:
            cells = row.find_all("td")
            if len(cells) < 12:
                continue
            try:
                date_str = cells[1].get_text(strip=True)
                trade_date = datetime.strptime(date_str, "%Y-%m-%d")
                if trade_date < cutoff:
                    continue

                trade_type = cells[6].get_text(strip=True)  # P = purchase, S = sale
                title = cells[4].get_text(strip=True)
                value_str = cells[10].get_text(strip=True).replace(",", "").replace("$", "")
                value = float(value_str) if value_str and value_str != "-" else 0

                trades.append({
                    "date": date_str,
                    "title": title,
                    "type": "BUY" if "P" in trade_type else "SELL",
                    "value": value,
                    "weight": OFFICER_WEIGHTS.get(title.split()[0] if title else "", 0.5),
                })
            except Exception:
                continue

        return trades
    except Exception:
        return []


def get_insider_cluster(ticker: str, days: int = 30) -> dict:
    """
    Detect insider cluster buys/sells.
    Returns: {has_cluster_buy, has_cluster_sell, buy_count, sell_count,
              total_buy_value, total_sell_value, officers_buying, signal_strength}
    """
    trades = _scrape_openinsider(ticker, days)

    buys = [t for t in trades if t["type"] == "BUY"]
    sells = [t for t in trades if t["type"] == "SELL"]

    buy_value = sum(t["value"] for t in buys)
    sell_value = sum(t["value"] for t in sells)
    buy_weighted = sum(t["value"] * t["weight"] for t in buys)

    # Cluster buy: 2+ insiders buying, total > $250K
    has_cluster_buy = len(buys) >= 2 and buy_value > 250_000
    # Strong cluster buy: 3+ insiders, >$1M
    has_strong_cluster_buy = len(buys) >= 3 and buy_value > 1_000_000
    # Cluster sell: 3+ insiders selling >$5M (often comp-related, less signal)
    has_cluster_sell = len(sells) >= 3 and sell_value > 5_000_000

    officers = list({t["title"] for t in buys if t["value"] > 10_000})

    signal_strength = 0
    if has_strong_cluster_buy:
        signal_strength = 2
    elif has_cluster_buy:
        signal_strength = 1
    elif has_cluster_sell:
        signal_strength = -1

    return {
        "has_buying": len(buys) > 0,
        "has_cluster_buy": has_cluster_buy,
        "has_strong_cluster_buy": has_strong_cluster_buy,
        "has_cluster_sell": has_cluster_sell,
        "buy_count": len(buys),
        "sell_count": len(sells),
        "total_buy_value": buy_value,
        "total_sell_value": sell_value,
        "officers_buying": officers[:3],
        "signal_strength": signal_strength,
        "source": "openinsider",
    }
