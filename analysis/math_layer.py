# -*- coding: utf-8 -*-
"""math_layer.py — Sharpe, Sortino, max drawdown, beta vs SPUS, Kelly fraction."""

import json
import os
import numpy as np
from typing import Optional

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")


# ---------------------------------------------------------------------------
# Return extraction
# ---------------------------------------------------------------------------

def _price_history(price_data: dict) -> list:
    """Extract ordered price list from price_data dict."""
    history = price_data.get("history") or []
    prices = [float(p) for p in history if p is not None and float(p) > 0]
    return prices


def _returns(prices: list) -> list:
    if len(prices) < 2:
        return []
    return [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]


# ---------------------------------------------------------------------------
# Individual metrics
# ---------------------------------------------------------------------------

def sharpe_ratio(returns: list, rf_annual: float = 0.05) -> Optional[float]:
    if len(returns) < 20:
        return None
    arr = np.array(returns, dtype=float)
    excess = arr - rf_annual / 252
    std = float(np.std(excess, ddof=1))
    if std == 0:
        return None
    return round(float(np.mean(excess)) / std * np.sqrt(252), 3)


def sortino_ratio(returns: list, rf_annual: float = 0.05) -> Optional[float]:
    if len(returns) < 20:
        return None
    arr = np.array(returns, dtype=float)
    excess = arr - rf_annual / 252
    downside = excess[excess < 0]
    if len(downside) < 2:
        return None
    downside_std = float(np.std(downside, ddof=1))
    if downside_std == 0:
        return None
    return round(float(np.mean(excess)) / downside_std * np.sqrt(252), 3)


def max_drawdown(returns: list) -> Optional[float]:
    if not returns:
        return None
    cumulative = np.cumprod(1 + np.array(returns, dtype=float))
    peak = np.maximum.accumulate(cumulative)
    dd = (cumulative - peak) / peak
    return round(float(np.min(dd)), 4)


def beta_vs_benchmark(holding_returns: list, bench_returns: list) -> Optional[float]:
    n = min(len(holding_returns), len(bench_returns))
    if n < 20:
        return None
    h = np.array(holding_returns[-n:], dtype=float)
    b = np.array(bench_returns[-n:], dtype=float)
    cov_matrix = np.cov(h, b)
    bench_var = cov_matrix[1, 1]
    if bench_var == 0:
        return None
    return round(float(cov_matrix[0, 1] / bench_var), 3)


def kelly_fraction_capped(returns: list) -> float:
    """
    Double-capped Kelly: min(0.25 * full_kelly, 0.05).
    Never returns more than 5% position size.
    """
    if len(returns) < 20:
        return 0.01  # Minimum floor for unknown assets

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    if not wins or not losses:
        return 0.01

    W = len(wins) / len(returns)
    avg_win = float(np.mean(wins))
    avg_loss = abs(float(np.mean(losses)))
    if avg_loss == 0:
        return 0.05

    R = avg_win / avg_loss
    raw_kelly = W - (1 - W) / R
    raw_kelly = max(0.0, raw_kelly)

    # Cap 1: 25% of full Kelly (beginner safety)
    # Cap 2: 5% of portfolio (absolute max)
    return round(min(0.25 * raw_kelly, 0.05), 4)


# ---------------------------------------------------------------------------
# Per-holding bundle
# ---------------------------------------------------------------------------

def compute_math_metrics(ticker: str, price_data: dict, spus_price_data: dict) -> dict:
    """Return all quant metrics for one holding. Never raises."""
    try:
        prices = _price_history(price_data)
        spus_prices = _price_history(spus_price_data)
        rets = _returns(prices)
        spus_rets = _returns(spus_prices)

        return {
            "sharpe_1y": sharpe_ratio(rets[-252:] if len(rets) > 252 else rets),
            "sortino_1y": sortino_ratio(rets[-252:] if len(rets) > 252 else rets),
            "max_drawdown_1y": max_drawdown(rets[-252:] if len(rets) > 252 else rets),
            "beta_to_spus": beta_vs_benchmark(rets, spus_rets),
            "kelly_fraction_capped": kelly_fraction_capped(rets[-252:] if len(rets) > 252 else rets),
        }
    except Exception as e:
        return {
            "sharpe_1y": None, "sortino_1y": None, "max_drawdown_1y": None,
            "beta_to_spus": None, "kelly_fraction_capped": 0.01, "_error": str(e),
        }


# ---------------------------------------------------------------------------
# Portfolio-level correlation matrix
# ---------------------------------------------------------------------------

def compute_correlation_matrix(price_cache: dict) -> dict:
    """Pairwise correlation across all tickers with enough history."""
    try:
        rets_map = {}
        for ticker, pd in price_cache.items():
            prices = _price_history(pd)
            rets = _returns(prices)
            if len(rets) >= 60:
                rets_map[ticker] = rets

        if len(rets_map) < 2:
            return {}

        tickers = sorted(rets_map.keys())
        min_len = min(len(rets_map[t]) for t in tickers)
        arr = np.array([rets_map[t][-min_len:] for t in tickers], dtype=float)
        corr = np.corrcoef(arr)

        matrix: dict = {}
        for i, t1 in enumerate(tickers):
            matrix[t1] = {}
            for j, t2 in enumerate(tickers):
                matrix[t1][t2] = round(float(corr[i, j]), 3)

        return matrix
    except Exception as e:
        return {"_error": str(e)}


def save_correlations(matrix: dict) -> None:
    """Write correlation matrix to output/correlations.json."""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        path = os.path.join(OUTPUT_DIR, "correlations.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(matrix, f, indent=2)
    except Exception:
        pass
