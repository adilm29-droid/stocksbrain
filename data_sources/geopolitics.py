# -*- coding: utf-8 -*-
"""
geopolitics.py — GDELT tone + FRED macro + Treasury auction calendar.
All sections degrade gracefully if APIs are unavailable.
"""
import os
import sys
import requests
from datetime import datetime, timedelta

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
GDELT_BASE = "https://api.gdeltproject.org/api/v2/doc/doc"
FRED_BASE = "https://api.fred.stlouisfed.org/series/observations"

GEOPOLITICAL_TERMS = [
    "tariff", "sanctions", "China Taiwan", "rate hike",
    "AI export controls", "OPEC oil", "Federal Reserve inflation",
]

FRED_SERIES = {
    "DGS10": "yield_10y",
    "DGS2": "yield_2y",
    "DFF": "fed_funds_rate",
    "UNRATE": "unemployment_rate",
    "CPIAUCSL": "cpi",
}


# ---------------------------------------------------------------------------
# GDELT
# ---------------------------------------------------------------------------

def _gdelt_tone(term: str, days_back: int = 7) -> dict:
    """Fetch average tone for a query term from GDELT v2 doc API."""
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=days_back)
        params = {
            "query": term,
            "mode": "artlist",
            "maxrecords": 50,
            "format": "json",
            "startdatetime": start.strftime("%Y%m%d%H%M%S"),
            "enddatetime": end.strftime("%Y%m%d%H%M%S"),
            "sort": "DateDesc",
        }
        r = requests.get(GDELT_BASE, params=params, timeout=12)
        if r.status_code != 200:
            return {"term": term, "avg_tone": 0.0, "count": 0}
        data = r.json()
        articles = data.get("articles") or []
        tones = []
        for a in articles:
            raw = a.get("tone", "")
            if raw:
                try:
                    tones.append(float(str(raw).split(",")[0]))
                except Exception:
                    pass
        avg = sum(tones) / len(tones) if tones else 0.0
        return {"term": term, "avg_tone": round(avg, 2), "count": len(articles)}
    except Exception as e:
        return {"term": term, "avg_tone": 0.0, "count": 0, "_error": str(e)}


# ---------------------------------------------------------------------------
# FRED
# ---------------------------------------------------------------------------

def _fred_latest(series_id: str) -> float | None:
    if not FRED_API_KEY:
        return None
    try:
        r = requests.get(
            FRED_BASE,
            params={
                "series_id": series_id,
                "api_key": FRED_API_KEY,
                "file_type": "json",
                "limit": 1,
                "sort_order": "desc",
            },
            timeout=10,
        )
        if r.status_code != 200:
            return None
        obs = r.json().get("observations") or []
        if obs:
            v = obs[0].get("value", ".")
            return float(v) if v != "." else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Treasury auctions
# ---------------------------------------------------------------------------

def _upcoming_auctions() -> list:
    try:
        r = requests.get(
            "https://api.fiscaldata.treasury.gov/services/api/v1/debt/auctions",
            params={"sort": "-auctionDate", "page[size]": 10, "format": "json"},
            timeout=10,
        )
        if r.status_code == 200:
            items = r.json().get("data") or []
            return [
                {
                    "security_type": i.get("securityType", ""),
                    "auction_date": i.get("auctionDate", ""),
                    "term": i.get("term", ""),
                }
                for i in items[:5]
            ]
    except Exception:
        pass
    # Fallback: TreasuryDirect securities API
    try:
        r = requests.get(
            "https://treasurydirect.gov/TA_WS/securities/announced",
            params={"format": "json", "type": "Note,Bond,Bill", "pagesize": 5},
            timeout=10,
        )
        if r.status_code == 200:
            items = r.json().get("securityList") or []
            return [
                {
                    "security_type": i.get("securityType", ""),
                    "auction_date": i.get("auctionDate", ""),
                    "term": i.get("term", ""),
                }
                for i in items[:5]
            ]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_geopolitics_pulse() -> dict:
    """
    Returns macro_pulse dict. Never raises — returns {} on total failure.
    Only first 4 GDELT terms are queried to avoid rate-limiting.
    """
    try:
        # GDELT — limit to 4 queries
        gdelt_results = [_gdelt_tone(term) for term in GEOPOLITICAL_TERMS[:4]]
        avg_tone = (
            sum(r["avg_tone"] for r in gdelt_results) / len(gdelt_results)
            if gdelt_results else 0.0
        )

        # FRED
        fred: dict = {}
        for sid, label in FRED_SERIES.items():
            v = _fred_latest(sid)
            if v is not None:
                fred[label] = v

        yield_curve = None
        if "yield_10y" in fred and "yield_2y" in fred:
            yield_curve = round(fred["yield_10y"] - fred["yield_2y"], 3)

        auctions = _upcoming_auctions()

        # Risk flags
        risk_flags: list[str] = []
        if yield_curve is not None and yield_curve < 0:
            risk_flags.append("inverted_yield_curve")
        if avg_tone < -2.0:
            risk_flags.append("high_geopolitical_risk")
        if fred.get("fed_funds_rate", 0) > 5.0:
            risk_flags.append("elevated_fed_funds")
        if fred.get("unemployment_rate", 0) > 5.5:
            risk_flags.append("rising_unemployment")

        return {
            "gdelt_sentiment": gdelt_results,
            "overall_geopolitical_tone": round(avg_tone, 2),
            "fred": fred,
            "yield_curve_10_2": yield_curve,
            "upcoming_treasury_auctions": auctions,
            "risk_flags": risk_flags,
            "fred_available": bool(FRED_API_KEY),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        return {"_error": str(e), "risk_flags": [], "fred": {}}
