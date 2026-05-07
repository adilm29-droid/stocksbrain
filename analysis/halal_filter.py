# -*- coding: utf-8 -*-
"""halal_filter.py — Hard halal compliance gate. Non-compliant → excluded from BUY."""

from config import HALAL_APPROVED


def check_halal(ticker: str) -> dict:
    """Return halal_ok, halal_status, reason for a ticker. Never raises."""
    try:
        if ticker in HALAL_APPROVED:
            return {
                "halal_ok": True,
                "halal_status": "COMPLIANT",
                "reason": "SPUS/HLAL/Wahed-approved whitelist",
            }
        # Autopilot portfolio names are always considered compliant (Wio internal)
        autopilot_names = {"Cybersecurity", "Architects of AI", "FATMAA", "Dividend Stocks"}
        if ticker in autopilot_names:
            return {
                "halal_ok": True,
                "halal_status": "COMPLIANT",
                "reason": "Autopilot portfolio — Shariah-screened by provider",
            }
        return {
            "halal_ok": False,
            "halal_status": "NON_COMPLIANT",
            "reason": "Not in halal-screened whitelist (AAOIFI/SPUS/HLAL)",
        }
    except Exception as e:
        return {"halal_ok": False, "halal_status": "ERROR", "reason": f"check error: {e}"}


def apply_halal_gate(scored_holdings: list) -> list:
    """
    Apply halal filter as hard gate.
    Non-compliant tickers: BUY → HOLD. SELL/TRIM allowed (risk management).
    Annotates each holding with halal_ok + halal_status.
    """
    result = []
    for h in scored_holdings:
        ticker = h.get("ticker", "")
        halal = check_halal(ticker)
        h = h.copy()
        h["halal_ok"] = halal["halal_ok"]
        h["halal_status"] = halal["halal_status"]

        if not halal["halal_ok"] and h.get("decision") == "BUY":
            h["decision"] = "HOLD"
            h["overlays_applied"] = h.get("overlays_applied", []) + ["halal_gate_BUY→HOLD"]
            line = h.get("output_line", "")
            h["output_line"] = line.replace("💰 BUY", "✅ HOLD [halal-N/A]").replace("BUY", "HOLD [halal-N/A]")
            h["score_breakdown"] = h.get("score_breakdown", []) + [
                f"Halal gate: {halal['reason']} — BUY downgraded to HOLD"
            ]
        result.append(h)
    return result
