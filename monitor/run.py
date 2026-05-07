"""
StocksBrain 24/7 Portfolio Monitor

Pulls current portfolio state, fetches live prices via yfinance,
checks V5 rules, and generates alert files in alerts/
"""
import json
import os
import sys
import hashlib
import argparse
from datetime import datetime, timezone, timedelta

# Make sure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'alerts')
os.makedirs(OUTPUT_DIR, exist_ok=True)

LAST_HASH_FILE = os.path.join(OUTPUT_DIR, '.last_hash')


def _load_portfolio():
    """Load portfolio from config.py."""
    from config import HOLDINGS, AUTOPILOT_PORTFOLIOS
    return HOLDINGS, AUTOPILOT_PORTFOLIOS


def _fetch_prices(tickers: list) -> dict:
    """Fetch live prices via yfinance."""
    prices = {}
    try:
        import yfinance as yf
        data = yf.download(tickers, period='2d', interval='1d', progress=False, group_by='ticker', auto_adjust=True)
        for t in tickers:
            try:
                if len(tickers) == 1:
                    close = data['Close'].dropna()
                    if not close.empty:
                        prices[t] = {'price': float(close.iloc[-1]), 'prev_close': float(close.iloc[-2]) if len(close) > 1 else float(close.iloc[-1])}
                else:
                    col = data[t]['Close'].dropna() if t in data.columns.get_level_values(0) else None
                    if col is not None and not col.empty:
                        prices[t] = {'price': float(col.iloc[-1]), 'prev_close': float(col.iloc[-2]) if len(col) > 1 else float(col.iloc[-1])}
            except Exception:
                pass
    except Exception as e:
        print(f"yfinance error: {e}", file=sys.stderr)
    return prices


def _fetch_macro() -> dict:
    """Fetch macro signals: VIX, S&P trend, gold, oil."""
    macro = {}
    try:
        import yfinance as yf
        macro_tickers = {'^VIX': 'vix', '^GSPC': 'sp500', 'GC=F': 'gold', 'CL=F': 'oil'}
        for yt, key in macro_tickers.items():
            try:
                d = yf.download(yt, period='5d', interval='1d', progress=False, auto_adjust=True)
                close = d['Close'].dropna()
                if not close.empty:
                    macro[key] = float(close.iloc[-1])
            except Exception:
                pass
        # S&P 200-day MA trend
        try:
            sp_hist = yf.download('^GSPC', period='250d', interval='1d', progress=False, auto_adjust=True)
            sp_close = sp_hist['Close'].dropna()
            if len(sp_close) >= 200:
                ma200 = float(sp_close.iloc[-200:].mean())
                current = float(sp_close.iloc[-1])
                macro['sp500_above_200ma'] = current > ma200
                macro['sp500_200ma'] = round(ma200, 2)
        except Exception:
            pass
    except Exception as e:
        print(f"macro fetch error: {e}", file=sys.stderr)
    return macro


def _check_rules(ticker: str, position_pct: float, gain_pct: float,
                 drawdown_from_peak: float, earnings_next_7: list,
                 sector_pct: float, halal_core_pct: float, macro: dict) -> list:
    """Run targeted V5 rule checks for monitor alerts."""
    alerts = []

    # Rule 17: drawdown -15% to -20% → thesis recheck
    if drawdown_from_peak <= -15:
        severity = 'HIGH' if drawdown_from_peak <= -20 else 'MEDIUM'
        alerts.append({
            'rule': 17,
            'severity': severity,
            'ticker': ticker,
            'message': f'{ticker} down {drawdown_from_peak:.1f}% from 52w peak — thesis recheck required (Rule 17)',
            'suggested_action': 'Review thesis. Not auto-sell. Beat-and-raise within 7d = HOLD.',
        })

    # Rule 4: earnings within 7 days
    if ticker in earnings_next_7:
        alerts.append({
            'rule': 4,
            'severity': 'HIGH',
            'ticker': ticker,
            'message': f'{ticker} has earnings within 7 days — all positions frozen to HOLD (Rule 4)',
            'suggested_action': 'No new trades. HOLD until 24h post-earnings.',
        })

    # Rule 8: position > 7%
    if position_pct > 7:
        alerts.append({
            'rule': 8,
            'severity': 'MEDIUM',
            'ticker': ticker,
            'message': f'{ticker} at {position_pct:.1f}% — exceeds 7% single-position cap (Rule 8)',
            'suggested_action': 'Review for trim. Target ≤7% per position.',
        })

    # Rule 27: winner trim threshold
    if gain_pct > 75 and position_pct > 5:
        alerts.append({
            'rule': 27,
            'severity': 'MEDIUM',
            'ticker': ticker,
            'message': f'{ticker} up {gain_pct:.1f}% at {position_pct:.1f}% of portfolio — winner trim review (Rule 27)',
            'suggested_action': f'Consider trimming 25-50% to lock in gains.',
        })

    return alerts


def _get_52w_high(prices_5d: dict, ticker: str) -> float:
    """Get 52-week high for drawdown calculation."""
    try:
        import yfinance as yf
        d = yf.download(ticker, period='52wk', interval='1wk', progress=False, auto_adjust=True)
        high = float(d['High'].max())
        return high
    except Exception:
        return prices_5d.get(ticker, {}).get('price', 1.0)


def run(dry_run: bool = False):
    now = datetime.now(timezone.utc)
    ts = now.strftime('%Y-%m-%d-%H%M')
    print(f"StocksBrain Monitor — {ts}", file=sys.stderr)

    holdings, autopilot = _load_portfolio()
    tickers = list(holdings.keys())

    # Fetch live prices
    print(f"Fetching prices for {len(tickers)} tickers...", file=sys.stderr)
    prices = _fetch_prices(tickers)

    # Fetch macro
    print("Fetching macro signals...", file=sys.stderr)
    macro = _fetch_macro()

    # Compute totals
    total_value = sum(
        holdings[t]['shares'] * (prices.get(t, {}).get('price') or holdings[t]['avg_cost'])
        for t in tickers
    ) + sum(p['total_value'] for p in autopilot.values())

    # Earnings next 7 days
    from orchestrator import _get_earnings_next_7_days
    earnings_next_7 = _get_earnings_next_7_days(tickers)

    # Sector concentrations
    sector_values: dict = {}
    for t in tickers:
        price = prices.get(t, {}).get('price') or holdings[t]['avg_cost']
        val = holdings[t]['shares'] * price
        sector = holdings[t].get('sector', 'Other')
        sector_values[sector] = sector_values.get(sector, 0) + val
    max_sector = max(sector_values.values()) if sector_values else 0
    max_sector_pct = (max_sector / total_value * 100) if total_value > 0 else 0
    max_sector_name = max(sector_values, key=sector_values.get) if sector_values else 'Unknown'

    # Halal core %
    from config import CORE_ETF_TICKERS
    halal_core_val = sum(
        holdings[t]['shares'] * (prices.get(t, {}).get('price') or holdings[t]['avg_cost'])
        for t in tickers if t in CORE_ETF_TICKERS
    ) + sum(p['total_value'] for p in autopilot.values())
    halal_core_pct = (halal_core_val / total_value * 100) if total_value > 0 else 0

    all_alerts = []

    # Portfolio-level checks
    if max_sector_pct > 40:
        all_alerts.append({
            'rule': 8,
            'severity': 'HIGH',
            'ticker': max_sector_name,
            'message': f'Sector {max_sector_name} at {max_sector_pct:.1f}% — exceeds 40% cap (Rule 8)',
            'suggested_action': 'Diversify into other sectors.',
        })

    if halal_core_pct < 12:
        all_alerts.append({
            'rule': 8,
            'severity': 'HIGH',
            'ticker': 'PORTFOLIO',
            'message': f'Halal core at {halal_core_pct:.1f}% — below 12% minimum (Rule 8)',
            'suggested_action': 'Add SPUS/HLAL/URTH or autopilot portfolio allocation.',
        })

    # Macro crash watch
    vix = macro.get('vix', 0)
    sp_above_200 = macro.get('sp500_above_200ma', True)
    macro_red = 0
    if vix > 30:
        macro_red += 1
    if not sp_above_200:
        macro_red += 1
    if macro_red >= 2:
        all_alerts.append({
            'rule': 18,
            'severity': 'HIGH',
            'ticker': 'MACRO',
            'message': f'Macro crash watch: VIX={vix:.1f}, S&P {"below" if not sp_above_200 else "above"} 200MA — {macro_red} red signals (Rule 18)',
            'suggested_action': 'Elevate cash. Pause new buys. Review all positions.',
        })

    # Per-ticker checks
    for ticker in tickers:
        price = prices.get(ticker, {}).get('price') or holdings[ticker]['avg_cost']
        avg_cost = holdings[ticker]['avg_cost']
        shares = holdings[ticker]['shares']
        value = shares * price
        position_pct = (value / total_value * 100) if total_value > 0 else 0
        gain_pct = (price - avg_cost) / avg_cost * 100 if avg_cost > 0 else 0

        # 52-week drawdown approximation using available price data
        peak_52w = price  # default: no drawdown
        drawdown_from_peak = 0.0
        if gain_pct < -14:  # Only fetch 52w high if looks like significant drawdown
            try:
                peak_52w = _get_52w_high(prices, ticker)
                drawdown_from_peak = (price - peak_52w) / peak_52w * 100 if peak_52w > 0 else 0
            except Exception:
                drawdown_from_peak = gain_pct  # fallback to gain % from cost basis

        sector_pct = (sector_values.get(holdings[ticker].get('sector', 'Other'), 0) / total_value * 100) if total_value > 0 else 0

        ticker_alerts = _check_rules(
            ticker=ticker,
            position_pct=position_pct,
            gain_pct=gain_pct,
            drawdown_from_peak=drawdown_from_peak,
            earnings_next_7=earnings_next_7,
            sector_pct=sector_pct,
            halal_core_pct=halal_core_pct,
            macro=macro,
        )
        all_alerts.extend(ticker_alerts)

    # Build alert markdown
    output_lines = [
        f"# StocksBrain Monitor — {ts}",
        f"Generated: {now.isoformat()}",
        f"Total portfolio value: ${total_value:,.2f}",
        f"VIX: {macro.get('vix', 'N/A')} | S&P 200MA: {'Above' if macro.get('sp500_above_200ma', True) else 'Below'}",
        f"Earnings next 7 days: {earnings_next_7 or 'None'}",
        f"Halal core: {halal_core_pct:.1f}% | Max sector: {max_sector_name} {max_sector_pct:.1f}%",
        "",
        f"## Alerts ({len(all_alerts)} total)",
    ]

    if all_alerts:
        for a in sorted(all_alerts, key=lambda x: ('LOW', 'MEDIUM', 'HIGH').index(x['severity']), reverse=True):
            output_lines += [
                f"",
                f"### [{a['severity']}] Rule {a['rule']} — {a['ticker']}",
                f"{a['message']}",
                f"**Action:** {a['suggested_action']}",
            ]
    else:
        output_lines.append("No alerts. All V5 rules pass.")

    output_lines += ["", f"---", f"*Monitor run by StocksBrain — {ts}*"]
    content = "\n".join(output_lines)

    # Write output file
    alert_filename = 'test.md' if dry_run else f'{ts}.md'
    alert_path = os.path.join(OUTPUT_DIR, alert_filename)
    with open(alert_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Alert written to: {alert_path}", file=sys.stderr)

    # Check if alerts changed vs last run
    content_hash = hashlib.md5(content.encode()).hexdigest()
    last_hash = ''
    if os.path.exists(LAST_HASH_FILE):
        with open(LAST_HASH_FILE) as f:
            last_hash = f.read().strip()

    if not dry_run:
        with open(LAST_HASH_FILE, 'w') as f:
            f.write(content_hash)

    new_alerts = all_alerts and content_hash != last_hash

    if new_alerts and not dry_run:
        print(f"New alerts detected ({len(all_alerts)} alerts) — would open GitHub issue in CI", file=sys.stderr)
        from monitor.notify import post_alert
        summary = f"{len(all_alerts)} alert(s) — " + "; ".join(a['message'][:60] for a in all_alerts[:3])
        post_alert(summary)

    print(f"Monitor complete: {len(all_alerts)} alerts, hash={'changed' if new_alerts else 'same'}", file=sys.stderr)
    return all_alerts


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Write to test.md, skip hash/notify')
    args = parser.parse_args()
    run(dry_run=args.dry_run)
