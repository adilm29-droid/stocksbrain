#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""StocksBrain v2 — Daily portfolio signal orchestrator."""
import json
import sys
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOLDINGS, AUTOPILOT_PORTFOLIOS, CORE_ETF_TICKERS, THRESHOLDS
from data_sources.prices import get_price_data
from data_sources.analysts import get_analyst_data
from data_sources.insiders import get_insider_activity
from data_sources.news import get_news_sentiment
from data_sources.options import get_options_flow

try:
    from intelligence.macro import get_macro_intelligence as get_macro_data_v6
    USE_V6_MACRO = True
except ImportError:
    from data_sources.macro import get_macro_data
    USE_V6_MACRO = False

from analysis.scorer import score_holding
from analysis.risk_reviewer import review_portfolio_risk
from analysis.bug_hunter import hunt_contradictions

# v2 modules — each imports lazily so a missing dep never kills the run
try:
    from analysis.halal_filter import apply_halal_gate
    HAS_HALAL = True
except Exception:
    HAS_HALAL = False

try:
    from analysis.math_layer import compute_math_metrics, compute_correlation_matrix, save_correlations
    HAS_MATH = True
except Exception:
    HAS_MATH = False

try:
    from analysis.kronos_forecast import forecast as kronos_forecast
    HAS_KRONOS = True
except Exception:
    HAS_KRONOS = False

try:
    from analysis.insider_clusters import detect_insider_clusters
    HAS_CLUSTERS = True
except Exception:
    HAS_CLUSTERS = False

try:
    from analysis.outcome_journal import log_batch
    HAS_JOURNAL = True
except Exception:
    HAS_JOURNAL = False

try:
    from data_sources.geopolitics import get_geopolitics_pulse
    HAS_GEO = True
except Exception:
    HAS_GEO = False

try:
    from data_sources.government_contracts import get_government_contracts
    HAS_GOV = True
except Exception:
    HAS_GOV = False

try:
    from alerts.dispatch import dispatch_alerts
    HAS_ALERTS = True
except Exception:
    HAS_ALERTS = False

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_earnings_next_7_days(tickers: list) -> list:
    try:
        from config import EARNINGS_CALENDAR
        today = datetime.utcnow().date()
        cutoff = today + timedelta(days=7)
        result = []
        for ticker in tickers:
            if ticker in EARNINGS_CALENDAR:
                entry = EARNINGS_CALENDAR[ticker]
                if not entry.get("reported", False):
                    try:
                        d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
                        if today <= d <= cutoff:
                            result.append(ticker)
                    except Exception:
                        pass
        return result
    except Exception:
        return []


def fetch_all_data(ticker):
    """Fetch all data sources for a single ticker."""
    print(f"  Fetching {ticker}...", file=sys.stderr)
    skip_fundamental = ticker in {"BTC-USD", "ETH-USD", "XRP-USD", "SOL-USD", "GLD", "SLV", "GC=F", "SI=F"}
    price = get_price_data(ticker) or {}
    analyst = get_analyst_data(ticker) if not skip_fundamental else {}
    insider = get_insider_activity(ticker) if not skip_fundamental else {}
    news = get_news_sentiment(ticker) or {}
    options = get_options_flow(ticker) or {}
    return ticker, price, analyst, insider, news, options


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("StocksBrain v2 — Daily Briefing", file=sys.stderr)
    print("=" * 40, file=sys.stderr)

    # ------------------------------------------------------------------
    # Macro (existing + v2 geopolitics)
    # ------------------------------------------------------------------
    print("Fetching macro data...", file=sys.stderr)
    if USE_V6_MACRO:
        macro = get_macro_data_v6() or {}
    else:
        from data_sources.macro import get_macro_data
        macro = get_macro_data() or {}

    macro_pulse: dict = {}
    if HAS_GEO:
        print("Fetching geopolitics pulse...", file=sys.stderr)
        try:
            macro_pulse = get_geopolitics_pulse() or {}
        except Exception as e:
            print(f"  [geo] error: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Price + fundamental data for all holdings
    # ------------------------------------------------------------------
    tickers = list(HOLDINGS.keys())
    autopilot_total = sum(p["total_value"] for p in AUTOPILOT_PORTFOLIOS.values())

    print(f"Fetching data for {len(tickers)} holdings...", file=sys.stderr)
    price_cache: dict = {}
    analyst_cache: dict = {}
    insider_cache: dict = {}
    news_cache: dict = {}
    options_cache: dict = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_all_data, t): t for t in tickers}
        for future in as_completed(futures):
            try:
                ticker, price, analyst, insider, news, options = future.result()
                price_cache[ticker] = price
                analyst_cache[ticker] = analyst
                insider_cache[ticker] = insider
                news_cache[ticker] = news
                options_cache[ticker] = options
            except Exception as e:
                t = futures[future]
                print(f"  Error fetching {t}: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Government contracts (new v2)
    # ------------------------------------------------------------------
    gov_contracts: dict = {}
    if HAS_GOV:
        print("Checking government contracts...", file=sys.stderr)
        try:
            gov_contracts = get_government_contracts(tickers) or {}
        except Exception as e:
            print(f"  [gov] error: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Portfolio totals
    # ------------------------------------------------------------------
    total_direct = sum(
        HOLDINGS[t]["shares"] * (price_cache.get(t, {}).get("price") or HOLDINGS[t]["avg_cost"])
        for t in tickers
    )
    total_value = total_direct + autopilot_total
    cash_pct = 0.0

    tech_value = sum(
        HOLDINGS[t]["shares"] * (price_cache.get(t, {}).get("price") or HOLDINGS[t]["avg_cost"])
        for t in tickers
        if HOLDINGS[t].get("bucket") == "equity"
        and t in {"AMD", "AMZN", "META", "MSFT", "NVDA", "PLTR", "TSLA"}
    )
    crypto_value = sum(
        HOLDINGS[t]["shares"] * (price_cache.get(t, {}).get("price") or HOLDINGS[t]["avg_cost"])
        for t in tickers
        if HOLDINGS[t].get("bucket") == "crypto"
    )

    portfolio_metrics = {
        "total_value": total_value,
        "cash_pct": cash_pct,
        "tech_pct": tech_value / total_value * 100 if total_value > 0 else 0,
        "crypto_pct": crypto_value / total_value * 100 if total_value > 0 else 0,
        "earnings_next_7_days": _get_earnings_next_7_days(tickers),
        "cash_usd": 348.0,
        "autopilot_tickers": set(AUTOPILOT_PORTFOLIOS.keys()),
        "direct_tickers": set(tickers),
    }

    # ------------------------------------------------------------------
    # STEP 1: Halal filter — must run FIRST as hard gate
    # ------------------------------------------------------------------
    print("Scoring holdings...", file=sys.stderr)
    scored_raw: list = []
    for ticker in tickers:
        price_data = price_cache.get(ticker, {})
        if not price_data:
            print(f"  Skipping {ticker} — no price data", file=sys.stderr)
            continue

        holding_config = HOLDINGS[ticker].copy()
        current_price = price_data.get("price", holding_config["avg_cost"])
        holding_value = holding_config["shares"] * current_price
        gain_pct = (current_price - holding_config["avg_cost"]) / holding_config["avg_cost"] * 100
        position_pct = holding_value / total_value * 100 if total_value > 0 else 0

        result = score_holding(
            ticker=ticker,
            holding_config=holding_config,
            price_data=price_data,
            analyst_data=analyst_cache.get(ticker, {}),
            insider_data=insider_cache.get(ticker, {}),
            news_data=news_cache.get(ticker, {}),
            macro_data=macro,
            portfolio_metrics=portfolio_metrics,
        )
        result["current_price"] = current_price
        result["position_pct"] = round(position_pct, 2)
        result["gain_pct"] = round(gain_pct, 2)
        result["holding_value"] = round(holding_value, 2)
        scored_raw.append(result)

    # Autopilot portfolios
    for name, ap in AUTOPILOT_PORTFOLIOS.items():
        gain_pct = (
            (ap["total_value"] - ap["total_cost"]) / ap["total_cost"] * 100
            if ap["total_cost"] > 0 else 0
        )
        scored_raw.append({
            "ticker": name,
            "score": 1,
            "decision": "HOLD",
            "output_line": f"[{name}] ✅ HOLD — Autopilot portfolio, managed externally (gain: {gain_pct:+.1f}%)",
            "overlays_applied": ["autopilot"],
            "score_breakdown": ["Autopilot overlay: always HOLD"],
            "signals": {"autopilot": True},
            "current_price": None,
            "position_pct": round(ap["total_value"] / total_value * 100, 2) if total_value > 0 else 0,
            "gain_pct": round(gain_pct, 2),
            "holding_value": ap["total_value"],
        })

    # Apply halal gate
    if HAS_HALAL:
        scored = apply_halal_gate(scored_raw)
    else:
        scored = scored_raw

    # ------------------------------------------------------------------
    # STEP 2: Math layer — Sharpe, Sortino, Kelly, correlations
    # ------------------------------------------------------------------
    spus_price_data = price_cache.get("SPUS", {})
    vol_forecasts: dict = {}

    if HAS_MATH or HAS_KRONOS:
        print("Computing quantitative metrics...", file=sys.stderr)
        for h in scored:
            ticker = h["ticker"]
            pd = price_cache.get(ticker, {})
            if not pd:
                continue
            if HAS_MATH:
                try:
                    h["math_metrics"] = compute_math_metrics(ticker, pd, spus_price_data)
                    # Inject kelly into position size recommendation
                    kelly = h["math_metrics"].get("kelly_fraction_capped", 0.01)
                    h["recommended_position_pct"] = round(kelly * 100, 2)
                except Exception as e:
                    h["math_metrics"] = {"_error": str(e)}
            if HAS_KRONOS:
                try:
                    vf = kronos_forecast(ticker, pd)
                    h["vol_forecast"] = vf
                    vol_forecasts[ticker] = vf
                    # vol signal (-1/0/+1) feeds into score as factor 13
                    if vf.get("signal") == -1:
                        h["score"] = max(-5, h.get("score", 0) - 1)
                        h["score_breakdown"] = h.get("score_breakdown", []) + [
                            f"-1 Kronos/EWMA vol at {vf.get('volatility_percentile')}th pct (size down)"
                        ]
                    elif vf.get("signal") == 1:
                        h["score"] = min(5, h.get("score", 0) + 1)
                        h["score_breakdown"] = h.get("score_breakdown", []) + [
                            f"+1 Kronos/EWMA vol at {vf.get('volatility_percentile')}th pct (size up)"
                        ]
                except Exception as e:
                    h["vol_forecast"] = {"_error": str(e)}

    # Correlation matrix
    corr_matrix: dict = {}
    if HAS_MATH:
        try:
            corr_matrix = compute_correlation_matrix(price_cache)
            save_correlations(corr_matrix)
        except Exception as e:
            print(f"  [math] correlation error: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # STEP 3: Insider clusters
    # ------------------------------------------------------------------
    insider_clusters: list = []
    if HAS_CLUSTERS:
        try:
            insider_clusters = detect_insider_clusters(insider_cache)
            if insider_clusters:
                print(f"  Insider clusters: {len(insider_clusters)} found", file=sys.stderr)
                # Boost scores for cluster tickers
                cluster_tickers = {c["ticker"] for c in insider_clusters}
                for h in scored:
                    if h["ticker"] in cluster_tickers:
                        h["score"] = min(5, h.get("score", 0) + 1)
                        h["insider_cluster"] = True
                        h["score_breakdown"] = h.get("score_breakdown", []) + [
                            "+1 Insider cluster (≥3 insiders, ≥$500K within 30d)"
                        ]
        except Exception as e:
            print(f"  [clusters] error: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # STEP 4: Risk review and contradiction check
    # ------------------------------------------------------------------
    risk_flags = review_portfolio_risk(scored, portfolio_metrics)
    contradictions = hunt_contradictions(scored)

    # ------------------------------------------------------------------
    # STEP 5: Log recommendations to journal
    # ------------------------------------------------------------------
    if HAS_JOURNAL:
        try:
            n = log_batch(scored)
            print(f"  Logged {n} recommendations to journal", file=sys.stderr)
        except Exception as e:
            print(f"  [journal] error: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # STEP 6: Dispatch alerts
    # ------------------------------------------------------------------
    if HAS_ALERTS:
        try:
            sent = dispatch_alerts(
                scored_holdings=scored,
                insider_clusters=insider_clusters,
                gov_contracts=gov_contracts,
                macro_pulse=macro_pulse,
                earnings_next_7=portfolio_metrics.get("earnings_next_7_days"),
                vol_forecasts=vol_forecasts,
            )
            if sent:
                print(f"  Alerts sent: {len(sent)}", file=sys.stderr)
        except Exception as e:
            print(f"  [alerts] error: {e}", file=sys.stderr)

    # ------------------------------------------------------------------
    # STEP 7: Load backtest summary
    # ------------------------------------------------------------------
    backtest_summary: dict = {}
    bt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backtest", "results.json")
    if os.path.exists(bt_path):
        try:
            with open(bt_path, "r", encoding="utf-8") as f:
                bt = json.load(f)
            backtest_summary = {
                "hit_rate": bt.get("hit_rate"),
                "hit_rate_pct": bt.get("hit_rate_pct"),
                "vs_spus": bt.get("spus_total_return_pct"),
                "max_drawdown": bt.get("max_drawdown"),
                "generated_at": bt.get("generated_at"),
            }
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Build summary + output
    # ------------------------------------------------------------------
    decisions = [h["decision"] for h in scored]
    summary = {
        "buy_count": decisions.count("BUY"),
        "hold_count": decisions.count("HOLD"),
        "trim_count": decisions.count("TRIM"),
        "sell_count": decisions.count("SELL"),
    }

    # Build enriched recommendations list for UI
    recommendations = [
        {
            "ticker": h["ticker"],
            "action": h.get("decision", "HOLD"),
            "score": h.get("score", 0),
            "confidence": _score_to_confidence(h.get("score", 0)),
            "position_size_pct": h.get("recommended_position_pct", h.get("position_pct", 0)),
            "reasoning": h.get("output_line", ""),
            "halal_ok": h.get("halal_ok", True),
            "halal_status": h.get("halal_status", "COMPLIANT"),
            "kelly_capped": (h.get("math_metrics") or {}).get("kelly_fraction_capped"),
            "vol_percentile": (h.get("vol_forecast") or {}).get("volatility_percentile"),
            "sharpe": (h.get("math_metrics") or {}).get("sharpe_1y"),
            "government_tailwind": gov_contracts.get(h["ticker"], {}).get("government_tailwind", False),
        }
        for h in scored
    ]

    dashboard = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "portfolio_metrics": {
            "total_value": round(total_value, 2),
            "direct_holdings_value": round(total_direct, 2),
            "autopilot_value": round(autopilot_total, 2),
            "cash_pct": cash_pct,
            "tech_pct": round(portfolio_metrics["tech_pct"], 2),
            "crypto_pct": round(portfolio_metrics["crypto_pct"], 2),
        },
        "macro": macro,
        "macro_pulse": macro_pulse,
        "holdings": scored,
        "recommendations": recommendations,
        "risk_flags": risk_flags,
        "contradictions": contradictions,
        "summary": summary,
        "correlations": corr_matrix,
        "backtest_summary": backtest_summary,
        "insider_clusters": insider_clusters,
        "government_contracts": {
            t: {"government_tailwind": v.get("government_tailwind", False), "max_award": v.get("max_award", 0)}
            for t, v in gov_contracts.items()
        },
    }

    dashboard_path = os.path.join(OUTPUT_DIR, "dashboard.json")
    with open(dashboard_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, indent=2, default=str)
    print(f"  Saved {dashboard_path}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Build briefing.txt
    # ------------------------------------------------------------------
    lines = [
        "=" * 60,
        "STOCKSBRAIN v2 — DAILY BRIEFING",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60, "",
        "MACRO CONTEXT", "-" * 40,
    ]
    if macro:
        lines.append(f"VIX: {macro.get('vix', 'N/A')} | SP500 Trend: {macro.get('sp500_trend', 'N/A')}")
        lines.append(f"DXY: {macro.get('dxy', 'N/A')} | 10Y Yield: {macro.get('ten_year_yield', 'N/A')}%")
        lines.append(f"Gold: ${macro.get('gold_price', 'N/A')} | Oil: ${macro.get('oil_price', 'N/A')}")
    if macro_pulse.get("fred"):
        fred = macro_pulse["fred"]
        lines.append(f"2/10 Spread: {macro_pulse.get('yield_curve_10_2', 'N/A')} | FFR: {fred.get('fed_funds_rate', 'N/A')}%")
    if macro_pulse.get("risk_flags"):
        lines.append(f"Macro risk flags: {', '.join(macro_pulse['risk_flags'])}")

    if insider_clusters:
        lines += ["", "INSIDER CLUSTERS", "-" * 40]
        for cl in insider_clusters:
            lines.append(f"  {cl['ticker']}: {cl['insider_count']} insiders, ${cl['total_value']:,.0f} — BULLISH")

    lines += ["", "SIGNALS TODAY", "-" * 40]
    for h in sorted(scored, key=lambda x: x.get("score", 0), reverse=True):
        lines.append(h["output_line"])
        if h.get("score_breakdown"):
            for item in h["score_breakdown"]:
                lines.append(f"    {item}")

    if risk_flags:
        lines += ["", "RISK FLAGS", "-" * 40]
        for flag in risk_flags:
            sev = flag.get("severity", "INFO")
            lines.append(f"[{sev}] {flag['detail']}")

    if contradictions:
        lines += ["", "CONTRADICTIONS DETECTED", "-" * 40]
        for c in contradictions:
            lines.append(f"WARNING  {c}")

    lines += [
        "", "SUMMARY", "-" * 40,
        f"BUY: {summary['buy_count']} | HOLD: {summary['hold_count']}"
        f" | TRIM: {summary['trim_count']} | SELL: {summary['sell_count']}",
        "", "=" * 60,
    ]

    briefing_text = "\n".join(lines)
    briefing_path = os.path.join(OUTPUT_DIR, "briefing.txt")
    with open(briefing_path, "w", encoding="utf-8") as f:
        f.write(briefing_text)
    print(f"  Saved {briefing_path}", file=sys.stderr)

    try:
        print(briefing_text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((briefing_text + "\n").encode("utf-8", errors="replace"))

    print(f"\nPortfolio Total: ${total_value:,.2f}", file=sys.stderr)
    print(f"Holdings scored: {len(scored)}", file=sys.stderr)


def _score_to_confidence(score: int) -> str:
    if score >= 3:
        return "HIGH"
    if score >= 1:
        return "MEDIUM"
    if score >= -1:
        return "LOW"
    return "NEGATIVE"


if __name__ == "__main__":
    main()
