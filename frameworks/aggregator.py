"""
Institutional Frameworks Aggregator — StocksBrain V6.
Runs all 9 frameworks and returns a unified score + breakdown.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frameworks.gs_sustain import gs_sustain_score
from frameworks.bridgewater_risk import bridgewater_score
from frameworks.jpm_earnings import jpm_earnings_score
from frameworks.blackrock_factors import blackrock_factor_score
from frameworks.citadel_meanrev import citadel_meanrev_score
from frameworks.renaissance_patterns import renaissance_score
from frameworks.twosigma_altdata import twosigma_altdata_score
from frameworks.aqr_valmom import aqr_valmom_score
from frameworks.berkshire_moat import berkshire_moat_score


FRAMEWORK_WEIGHTS = {
    "gs_sustain": 1.0,
    "bridgewater": 0.8,
    "jpm_earnings": 1.2,
    "blackrock": 1.0,
    "citadel": 0.7,
    "renaissance": 0.6,
    "twosigma": 0.8,
    "aqr_valmom": 1.2,
    "berkshire_moat": 1.0,
}


def run_all_frameworks(ticker: str, price_data: dict, analyst_data: dict,
                       news_data: dict, macro_data: dict) -> dict:
    """
    Run all 9 institutional frameworks for a ticker.
    Returns: {score: float, breakdown: dict, details: dict}
    Score range: approximately -9 to +9 weighted
    """
    results = {}
    errors = []

    framework_funcs = [
        ("gs_sustain", gs_sustain_score),
        ("bridgewater", bridgewater_score),
        ("jpm_earnings", jpm_earnings_score),
        ("blackrock", blackrock_factor_score),
        ("citadel", citadel_meanrev_score),
        ("renaissance", renaissance_score),
        ("twosigma", twosigma_altdata_score),
        ("aqr_valmom", aqr_valmom_score),
        ("berkshire_moat", berkshire_moat_score),
    ]

    for name, func in framework_funcs:
        try:
            raw = func(ticker, price_data, analyst_data, news_data, macro_data)
            weight = FRAMEWORK_WEIGHTS.get(name, 1.0)
            results[name] = {
                "raw_score": raw.get("score", 0),
                "weighted_score": raw.get("score", 0) * weight,
                "reason": raw.get("reason", ""),
                "details": raw.get("details", {}),
            }
        except Exception as e:
            errors.append(f"{name}: {e}")
            results[name] = {"raw_score": 0, "weighted_score": 0, "reason": f"Error: {e}", "details": {}}

    total_weighted = sum(v["weighted_score"] for v in results.values())
    total_possible = sum(2.0 * w for w in FRAMEWORK_WEIGHTS.values())  # max +2 per framework
    normalized = (total_weighted / total_possible) * 2 if total_possible > 0 else 0  # -2 to +2

    return {
        "score": round(normalized, 2),
        "raw_weighted_total": round(total_weighted, 2),
        "breakdown": {k: {"score": v["raw_score"], "reason": v["reason"]} for k, v in results.items()},
        "errors": errors,
    }
