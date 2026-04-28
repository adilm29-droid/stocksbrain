# -*- coding: utf-8 -*-
"""
government_contracts.py — USAspending.gov API for defense/AI/cyber contracts.
Flags new $50M+ awards to portfolio companies as government_tailwind.
"""
import requests
from datetime import datetime, timedelta

USASPENDING_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Map ticker → list of strings to match against recipient names
COMPANY_PARENT_MAP: dict[str, list[str]] = {
    "MSFT": ["Microsoft"],
    "AMZN": ["Amazon", "Amazon Web Services", "AWS"],
    "PLTR": ["Palantir"],
    "NVDA": ["NVIDIA"],
    "META": ["Meta Platforms", "Facebook"],
    "AMD":  ["Advanced Micro Devices"],
    "UNH":  ["UnitedHealth"],
    "TSLA": ["Tesla"],
    "V":    ["Visa"],
    "GOOGL": ["Google", "Alphabet"],
    "AAPL":  ["Apple"],
}


def _search_awards(company_names: list[str], days_back: int = 30) -> list:
    """Search USAspending for recent awards to a company. Returns raw list."""
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=days_back)
        payload = {
            "filters": {
                "award_type_codes": ["A", "B", "C", "D"],
                "date_type": "action_date",
                "date_range": {
                    "start_date": start.strftime("%Y-%m-%d"),
                    "end_date": end.strftime("%Y-%m-%d"),
                },
                "recipient_search_text": company_names,
            },
            "fields": [
                "Award ID", "Recipient Name", "Award Amount",
                "awarding_agency_name", "Award Type",
            ],
            "limit": 10,
            "sort": "Award Amount",
            "order": "desc",
            "page": 1,
        }
        r = requests.post(USASPENDING_URL, json=payload, timeout=15)
        if r.status_code != 200:
            return []
        return r.json().get("results") or []
    except Exception:
        return []


def get_government_contracts(tickers: list[str], days_back: int = 30) -> dict:
    """
    Returns {ticker: {government_tailwind: bool, awards: list, max_award: float}}.
    Never raises.
    """
    result: dict = {}

    for ticker in tickers:
        names = COMPANY_PARENT_MAP.get(ticker)
        if not names:
            result[ticker] = {"government_tailwind": False, "awards": [], "max_award": 0.0}
            continue
        try:
            raw_awards = _search_awards(names, days_back=days_back)
            big_awards = []
            max_award = 0.0
            for award in raw_awards:
                try:
                    amount = float(award.get("Award Amount") or 0)
                except Exception:
                    amount = 0.0
                if amount >= 50_000_000:
                    big_awards.append({
                        "id": award.get("Award ID", ""),
                        "recipient": award.get("Recipient Name", ""),
                        "amount": amount,
                        "agency": award.get("awarding_agency_name", ""),
                    })
                    max_award = max(max_award, amount)

            result[ticker] = {
                "government_tailwind": len(big_awards) > 0,
                "awards": big_awards[:3],
                "max_award": max_award,
            }
        except Exception as e:
            result[ticker] = {
                "government_tailwind": False,
                "awards": [],
                "max_award": 0.0,
                "_error": str(e),
            }

    return result
