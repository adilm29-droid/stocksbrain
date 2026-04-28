# -*- coding: utf-8 -*-
"""
alerts/dispatch.py — Resend.com email dispatcher.
Max 3 emails/day. Deduped by content hash. Never emails "do nothing."
"""
import hashlib
import json
import os
from datetime import date
from typing import Optional

RESEND_API_KEY: Optional[str] = os.environ.get("RESEND_API_KEY", "")
ALERT_FROM = os.environ.get("ALERT_FROM_EMAIL", "StocksBrain <alerts@resend.dev>")
ALERT_TO = os.environ.get("ALERT_EMAIL", "adilm29@gmail.com")
MAX_DAILY = 3

_SENT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sent_log.json")


# ---------------------------------------------------------------------------
# Rate-limit / dedup state
# ---------------------------------------------------------------------------

def _load_log() -> dict:
    today = str(date.today())
    try:
        if os.path.exists(_SENT_LOG):
            with open(_SENT_LOG, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("date") == today:
                return d
    except Exception:
        pass
    return {"date": today, "count": 0, "hashes": []}


def _save_log(log: dict) -> None:
    try:
        with open(_SENT_LOG, "w", encoding="utf-8") as f:
            json.dump(log, f)
    except Exception:
        pass


def _hash(subject: str, body: str) -> str:
    return hashlib.sha256(f"{subject}\n{body}".encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Send
# ---------------------------------------------------------------------------

def send_alert(subject: str, body: str) -> bool:
    """
    Send email via Resend. Returns True if sent.
    Skips if: no API key, daily limit reached, or duplicate content.
    """
    if not RESEND_API_KEY:
        print(f"[alerts] No RESEND_API_KEY — skip: {subject}")
        return False

    log = _load_log()
    if log["count"] >= MAX_DAILY:
        print(f"[alerts] Daily cap {MAX_DAILY} reached — skip: {subject}")
        return False

    h = _hash(subject, body)
    if h in log.get("hashes", []):
        print(f"[alerts] Duplicate — skip: {subject}")
        return False

    try:
        import requests
        r = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": ALERT_FROM,
                "to": [ALERT_TO],
                "subject": f"[StocksBrain] {subject}",
                "html": f"<pre style='font-family:monospace'>{body}</pre>",
            },
            timeout=12,
        )
        if r.status_code in (200, 201):
            log["count"] += 1
            log.setdefault("hashes", []).append(h)
            _save_log(log)
            print(f"[alerts] Sent: {subject}")
            return True
        print(f"[alerts] Resend {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[alerts] Exception: {e}")
        return False


# ---------------------------------------------------------------------------
# Condition checks
# ---------------------------------------------------------------------------

def dispatch_alerts(
    scored_holdings: list,
    insider_clusters: list,
    gov_contracts: dict,
    macro_pulse: dict,
    earnings_next_7: list | None = None,
    vol_forecasts: dict | None = None,
) -> list[str]:
    """
    Evaluate all alert conditions and fire emails for actionable items.
    Returns list of subjects sent.
    """
    sent: list[str] = []

    # 1. Insider cluster
    for cl in insider_clusters:
        t = cl["ticker"]
        n = cl["insider_count"]
        v = cl["total_value"]
        subj = f"Insider Cluster: {t} — {n} insiders buying (${v:,.0f})"
        body = (
            f"INSIDER CLUSTER DETECTED\n"
            f"Ticker:  {t}\n"
            f"Insiders: {n} buying within 30 days\n"
            f"Total value: ${v:,.0f}\n\n"
            f"Signal: BULLISH (weight ×{cl.get('weight_multiplier', 1.5)})\n"
            f"Action: Review size of {t} position"
        )
        if send_alert(subj, body):
            sent.append(subj)

    # 2. Government contract win
    for t, cd in gov_contracts.items():
        if cd.get("government_tailwind") and cd.get("max_award", 0) >= 50_000_000:
            award = cd["max_award"]
            subj = f"Gov Contract: {t} — ${award / 1e6:.0f}M award"
            body = (
                f"GOVERNMENT CONTRACT WIN\n"
                f"Ticker: {t}\n"
                f"Award:  ${award:,.0f}\n"
                f"Agency: {(cd.get('awards') or [{}])[0].get('agency', 'unknown')}\n\n"
                f"Action: Monitor for sustained revenue impact"
            )
            if send_alert(subj, body):
                sent.append(subj)

    # 3. Intraday drop >7%
    for h in scored_holdings:
        chg = (h.get("signals") or {}).get("day_change_pct") or 0.0
        if float(chg) <= -7.0:
            t = h["ticker"]
            subj = f"Price Drop: {t} down {abs(chg):.1f}% today"
            body = (
                f"INTRADAY PRICE DROP\n"
                f"Ticker:  {t}\n"
                f"Change:  {chg:.1f}%\n"
                f"Signal:  {h.get('decision', 'HOLD')}\n\n"
                f"Action: Thesis review — buying opportunity or breakdown?"
            )
            if send_alert(subj, body):
                sent.append(subj)

    # 4. Earnings within 48h
    if earnings_next_7:
        from datetime import datetime
        now = datetime.utcnow()
        from config import EARNINGS_CALENDAR
        for ticker in earnings_next_7:
            cal = EARNINGS_CALENDAR.get(ticker, {})
            if cal.get("reported"):
                continue
            try:
                from datetime import datetime as dt2
                d = dt2.strptime(cal["date"], "%Y-%m-%d")
                hours_away = (d - now).total_seconds() / 3600
                if 0 < hours_away <= 48:
                    subj = f"Earnings <48h: {ticker} reports {cal['date']} {cal.get('timing','')}"
                    body = (
                        f"EARNINGS APPROACHING\n"
                        f"Ticker:  {ticker}\n"
                        f"Date:    {cal['date']} {cal.get('timing','')}\n"
                        f"Hours:   {hours_away:.0f}h away\n\n"
                        f"Action: No new trades. Hold through."
                    )
                    if send_alert(subj, body):
                        sent.append(subj)
            except Exception:
                pass

    # 5. Kronos 95th-percentile volatility
    if vol_forecasts:
        for t, vf in vol_forecasts.items():
            if vf.get("volatility_percentile", 0) >= 95:
                subj = f"High Vol Alert: {t} at {vf['volatility_percentile']}th vol percentile"
                body = (
                    f"VOLATILITY SPIKE\n"
                    f"Ticker:  {t}\n"
                    f"Realized vol: {vf.get('expected_volatility_pct','N/A')}% annualized\n"
                    f"Percentile: {vf.get('volatility_percentile')}th\n\n"
                    f"Action: Reduce position size — Kronos/EWMA vol signal."
                )
                if send_alert(subj, body):
                    sent.append(subj)

    # 6. High geopolitical risk
    tone = macro_pulse.get("overall_geopolitical_tone", 0)
    if float(tone) < -3.0:
        risk_flags = macro_pulse.get("risk_flags", [])
        subj = f"Macro Risk: Geopolitical tone at {tone:.1f}"
        body = (
            f"MACRO RISK ALERT\n"
            f"Geopolitical tone: {tone:.1f} (very negative)\n"
            f"Risk flags: {', '.join(risk_flags) or 'none'}\n\n"
            f"Action: Review portfolio risk. Consider reducing speculative positions."
        )
        if send_alert(subj, body):
            sent.append(subj)

    return sent
