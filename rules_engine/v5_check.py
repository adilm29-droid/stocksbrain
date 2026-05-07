"""V5 broker rules checker — runs before every recommendation is added to dashboard.json."""
import json
import os
from typing import Any

_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'v5_rules.json')

def _load_rules():
    with open(_RULES_PATH, encoding='utf-8') as f:
        return json.load(f)

def check_all_rules(portfolio: dict, ticker: str, action: str, context: dict = None) -> list[dict]:
    """
    Run all V5 rules against a proposed action.

    Args:
        portfolio: dict with keys: total_value, cash_pct, positions (dict of ticker->metrics)
        ticker: the ticker being evaluated
        action: BUY | HOLD | TRIM | SELL
        context: optional extra context (earnings_next_7_days, data_points_count, etc.)

    Returns:
        list of {rule_id, rule_name, status: 'ok'|'warning'|'violation', reason}
    """
    if context is None:
        context = {}
    rules = _load_rules()
    results = []

    position = portfolio.get('positions', {}).get(ticker, {})
    position_pct = position.get('position_pct', 0)
    gain_pct = position.get('gain_pct', 0)
    data_points = context.get('data_points_count', 8)
    earnings_next_7 = context.get('earnings_next_7_days', [])
    days_since_trade = context.get('days_since_last_trade', 999)
    direction_changed = context.get('direction_changed', False)
    thesis_broken = context.get('thesis_broken', False)
    cash_pct = portfolio.get('cash_pct', 10.0)
    sector_pct = context.get('sector_pct', 0)
    halal_core_pct = context.get('halal_core_pct', 15.0)
    confidence = context.get('confidence', 'MEDIUM')
    blackout_active = ticker in earnings_next_7

    for rule in rules:
        rid = rule['id']
        status = 'ok'
        reason = ''

        # Rule 1: No flip-flops within 30 days
        if rid == 1:
            if days_since_trade < 30 and direction_changed and not thesis_broken:
                status = 'violation'
                reason = f'Position direction changed {days_since_trade}d after last trade without thesis break'

        # Rule 4: Earnings blackout
        elif rid == 4:
            if blackout_active and action != 'HOLD':
                status = 'violation'
                reason = f'{ticker} has earnings within 7 days — action must be HOLD'

        # Rule 7: 8 data points for BUY/SELL
        elif rid == 7:
            if action in ('BUY', 'SELL') and data_points < 8:
                status = 'violation'
                reason = f'Only {data_points}/8 data points for {action} decision'

        # Rule 8: Rebalance triggers
        elif rid == 8:
            if position_pct > 7:
                status = 'warning'
                reason = f'{ticker} at {position_pct:.1f}% — exceeds 7% single-position cap'
            elif sector_pct > 40:
                status = 'warning'
                reason = f'Sector at {sector_pct:.1f}% — exceeds 40% concentration limit'
            elif halal_core_pct < 12:
                status = 'warning'
                reason = f'Halal core at {halal_core_pct:.1f}% — below 12% minimum'
            elif gain_pct > 75 and position_pct > 5:
                status = 'warning'
                reason = f'{ticker} up {gain_pct:.1f}% and {position_pct:.1f}% of portfolio — review for trim'

        # Rule 11: HIGH confidence calibration
        elif rid == 11:
            if confidence == 'HIGH' and (data_points < 8 or blackout_active or thesis_broken):
                status = 'violation'
                reason = 'HIGH confidence claimed but conditions not met (need 8/8 data, no blackout, thesis intact)'

        # Rule 17: Circle of competence
        elif rid == 17:
            forbidden = context.get('asset_category', '')
            if forbidden in ('biotech_pipeline', 'options', 'leveraged_etf', 'penny_stock', 'recent_ipo'):
                status = 'violation'
                reason = f'{ticker} is in forbidden category: {forbidden}'

        # Rule 20: Sell rigor = buy rigor
        elif rid == 20:
            if action in ('SELL', 'TRIM') and data_points < 8:
                status = 'violation'
                reason = f'Only {data_points}/8 data points for {action} — same rigor as BUY required'

        # Rule 23: No leverage/derivatives
        elif rid == 23:
            if context.get('leveraged', False):
                status = 'violation'
                reason = 'Leveraged or derivatives position detected — not allowed'

        # Rule 27: Winner trim threshold
        elif rid == 27:
            if gain_pct > 75 and position_pct > 5 and action not in ('TRIM', 'SELL'):
                status = 'warning'
                reason = f'{ticker} up {gain_pct:.1f}% at {position_pct:.1f}% of portfolio — consider trim'

        results.append({
            'rule_id': rid,
            'rule_name': rule['name'],
            'status': status,
            'reason': reason or 'OK',
        })

    return results
