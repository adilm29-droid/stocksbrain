"""
whales.py — Queries SEC EDGAR for recent 13F-HR institutional filings.

Functions:
    get_whale_activity(ticker) -> dict
"""

import sys
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None

EDGAR_SEARCH_URL = (
    "https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22"
    "&dateRange=custom&startdt={start}&enddt={end}&forms=13F-HR"
)

EDGAR_HEADERS = {
    "User-Agent": "StocksBrain adilm29@gmail.com",
    "Accept": "application/json",
}

_EMPTY = {"institutional_change_pct": 0.0, "top_holders": [], "filing_count": 0}


def get_whale_activity(ticker: str) -> dict:
    """
    Fetch recent 13F-HR filings mentioning the ticker from SEC EDGAR.

    Returns dict:
        institutional_change_pct (float) — placeholder; EDGAR doesn't directly give delta
        top_holders (list of {name, filed_date, accession_no})
        filing_count (int)

    Returns empty dict on failure.
    """
    if requests is None:
        return _EMPTY

    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)

    url = EDGAR_SEARCH_URL.format(
        ticker=ticker,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )

    try:
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[WARN] whales.get_whale_activity({ticker}): request failed — {exc}", file=sys.stderr)
        return _EMPTY

    try:
        hits = data.get("hits", {}).get("hits", [])
        filing_count = len(hits)
        top_holders = []

        for hit in hits[:10]:
            source = hit.get("_source", {})
            entity_name = source.get("entity_name", "Unknown")
            filed_at = source.get("file_date", "")
            accession_no = source.get("accession_no", "")

            top_holders.append({
                "name": entity_name,
                "filed_date": filed_at,
                "accession_no": accession_no,
            })

        # institutional_change_pct: We'd need to compare across quarters for a real delta.
        # As a heuristic proxy: more recent filings = more institutional interest.
        institutional_change_pct = min(filing_count * 2.0, 20.0)  # rough heuristic signal

        return {
            "institutional_change_pct": round(institutional_change_pct, 1),
            "top_holders": top_holders,
            "filing_count": filing_count,
        }

    except Exception as exc:
        print(f"[WARN] whales.get_whale_activity({ticker}): parse error — {exc}", file=sys.stderr)
        return _EMPTY
