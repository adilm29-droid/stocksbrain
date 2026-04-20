#!/usr/bin/env python3
"""StocksBrain v2 — Daily portfolio signal orchestrator."""
import json
import sys
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOLDINGS, AUTOPILOT_PORTFOLIOS, CORE_ETF_TICKERS, THRESHOLDS
from data_sources.prices import get_price_data
from data_sources.analysts import get_analyst_data
from data_sources.insiders import get_insider_activity
from data_sources.news import get_news_sentiment
from data_sources.macro import get_macro_data
from data_sources.options import get_options_flow
from analysis.scorer import score_holding
from analysis.risk_reviewer import review_portfolio_risk
from analysis.bug_hunter import hunt_contradictions

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def fetch_all_data(ticker):
    """Fetch all data for a single ticker."""
    print(f"  Fetching {ticker}...", file=sys.stderr)
    price = get_price_data(ticker) or {}
    analyst = (
        get_analyst_data(ticker)
        if ticker not in {"BTC-USD", "ETH-USD", "XRP-USD", "SOL-USD", "GLD", "SLV"}
        else {}
    )
    insider = (
        get_insider_activity(ticker)
        if ticker not in {"BTC-USD", "ETH-USD", "XRP-USD", "SOL-USD", "GLD", "SLV"}
        else {}
    )
    news = get_news_sentiment(ticker) or {}
    options = get_options_flow(ticker) or {}
    return ticker, price, analyst, insider, news, options


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("StocksBrain v2 — Daily Briefing", file=sys.stderr)
    print("=" * 40, file=sys.stderr)

    # Fetch macro data
    print("Fetching macro data...", file=sys.stderr)
    macro = get_macro_data() or {}

    # Calculate portfolio metrics
    tickers = list(HOLDINGS.keys())
    autopilot_total = sum(p["total_value"] for p in AUTOPILOT_PORTFOLIOS.values())

    # Fetch all data in parallel
    print(f"Fetching data for {len(tickers)} holdings...", file=sys.stderr)
    price_cache = {}
    analyst_cache = {}
    insider_cache = {}
    news_cache = {}
    options_cache = {}

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
                ticker = futures[future]
                print(f"  Error fetching {ticker}: {e}", file=sys.stderr)

    # Calculate portfolio totals
    total_direct = sum(
        HOLDINGS[t]["shares"] * (price_cache.get(t, {}).get("price") or HOLDINGS[t]["avg_cost"])
        for t in tickers
    )
    total_value = total_direct + autopilot_total
    cash_pct = 0.0  # No cash holdings in config — reflect as 0%

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
        "earnings_next_7_days": [],  # Would come from earnings calendar
        "autopilot_tickers": set(AUTOPILOT_PORTFOLIOS.keys()),
        "direct_tickers": set(tickers),
    }

    # Score all holdings
    print("Scoring holdings...", file=sys.stderr)
    scored = []
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
        scored.append(result)

    # Add autopilot portfolios as scored entries (overlay always applies)
    for name, ap in AUTOPILOT_PORTFOLIOS.items():
        gain_pct = (
            (ap["total_value"] - ap["total_cost"]) / ap["total_cost"] * 100
            if ap["total_cost"] > 0
            else 0
        )
        scored.append(
            {
                "ticker": name,
                "score": 1,
                "decision": "HOLD",
                "output_line": (
                    f"[{name}] ✅ HOLD — Autopilot portfolio, managed externally"
                    f" (gain: {gain_pct:+.1f}%)"
                ),
                "overlays_applied": ["autopilot"],
                "score_breakdown": ["Autopilot overlay: always HOLD"],
                "signals": {"autopilot": True},
                "current_price": None,
                "position_pct": (
                    round(ap["total_value"] / total_value * 100, 2) if total_value > 0 else 0
                ),
                "gain_pct": round(gain_pct, 2),
                "holding_value": ap["total_value"],
            }
        )

    # Risk review and contradiction check
    risk_flags = review_portfolio_risk(scored, portfolio_metrics)
    contradictions = hunt_contradictions(scored)

    # Summary counts
    decisions = [h["decision"] for h in scored]
    summary = {
        "buy_count": decisions.count("BUY"),
        "hold_count": decisions.count("HOLD"),
        "trim_count": decisions.count("TRIM"),
        "sell_count": decisions.count("SELL"),
    }

    # Build dashboard.json
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
        "holdings": scored,
        "risk_flags": risk_flags,
        "contradictions": contradictions,
        "summary": summary,
    }

    dashboard_path = os.path.join(OUTPUT_DIR, "dashboard.json")
    with open(dashboard_path, "w") as f:
        json.dump(dashboard, f, indent=2, default=str)
    print(f"  Saved {dashboard_path}", file=sys.stderr)

    # Build briefing.txt
    lines = [
        "=" * 60,
        "STOCKSBRAIN v2 — DAILY BRIEFING",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "=" * 60,
        "",
        "MACRO CONTEXT",
        "-" * 40,
    ]
    if macro:
        lines.append(
            f"VIX: {macro.get('vix', 'N/A')} | SP500 Trend: {macro.get('sp500_trend', 'N/A')}"
        )
        lines.append(
            f"DXY: {macro.get('dxy', 'N/A')} | 10Y Yield: {macro.get('ten_year_yield', 'N/A')}%"
        )
        lines.append(
            f"Gold: ${macro.get('gold_price', 'N/A')} | Oil: ${macro.get('oil_price', 'N/A')}"
        )

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
        "",
        "SUMMARY",
        "-" * 40,
        f"BUY: {summary['buy_count']} | HOLD: {summary['hold_count']}"
        f" | TRIM: {summary['trim_count']} | SELL: {summary['sell_count']}",
        "",
        "=" * 60,
    ]

    briefing_text = "\n".join(lines)
    briefing_path = os.path.join(OUTPUT_DIR, "briefing.txt")
    with open(briefing_path, "w", encoding="utf-8") as f:
        f.write(briefing_text)
    print(f"  Saved {briefing_path}", file=sys.stderr)

    # Print to stdout (use errors="replace" so Windows cp1252 consoles don't crash on emoji)
    try:
        print(briefing_text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((briefing_text + "\n").encode("utf-8", errors="replace"))
    print(f"\nPortfolio Total: ${total_value:,.2f}", file=sys.stderr)
    print(f"Holdings scored: {len(scored)}", file=sys.stderr)


if __name__ == "__main__":
    main()
