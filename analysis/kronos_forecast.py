# -*- coding: utf-8 -*-
"""
kronos_forecast.py — Factor #13: volatility forecasting.

Uses Kronos transformer (vendor/kronos) when available.
Falls back to EWMA realized-vol when torch/Kronos is not installed.

DO NOT use directional output as a buy/sell signal — it overfits.
Volatility percentile drives position sizing ONLY.
"""
import os
import sys
import numpy as np
from typing import Optional

_KRONOS_CHECKED: Optional[bool] = None
_model_cache: dict = {}

NEUTRAL = {
    "expected_volatility_pct": None,
    "volatility_percentile": 50,
    "signal": 0,
    "method": "neutral",
}


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def _kronos_available() -> bool:
    global _KRONOS_CHECKED
    if _KRONOS_CHECKED is not None:
        return _KRONOS_CHECKED
    try:
        import torch  # noqa: F401
        vendor = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "kronos"
        )
        if os.path.isdir(vendor) and vendor not in sys.path:
            sys.path.insert(0, vendor)
        _KRONOS_CHECKED = True
    except ImportError:
        _KRONOS_CHECKED = False
    return _KRONOS_CHECKED


# ---------------------------------------------------------------------------
# Realized-vol fallback (EWMA-style)
# ---------------------------------------------------------------------------

def _ewma_vol(returns: list, span: int = 30, horizon: int = 7) -> dict:
    """EWMA realized volatility + percentile ranking."""
    if len(returns) < 30:
        return NEUTRAL.copy()

    arr = np.array(returns, dtype=float)
    alpha = 2 / (span + 1)

    # EWMA variance
    var = float(arr[-span:].var())
    for r in arr[-span:]:
        var = alpha * r ** 2 + (1 - alpha) * var

    recent_vol = float(np.sqrt(var) * np.sqrt(252) * 100)  # annualized %

    # Rolling 30-day window vols for percentile
    window = 30
    rolling = []
    for i in range(window, len(arr)):
        rolling.append(float(np.std(arr[i - window: i], ddof=1) * np.sqrt(252) * 100))

    percentile = 50
    if rolling:
        percentile = int(np.mean(np.array(rolling) <= recent_vol) * 100)

    signal = 1 if percentile <= 40 else (-1 if percentile >= 80 else 0)

    return {
        "expected_volatility_pct": round(recent_vol, 2),
        "volatility_percentile": percentile,
        "signal": signal,
        "method": "ewma_realized_vol",
    }


# ---------------------------------------------------------------------------
# Kronos path
# ---------------------------------------------------------------------------

def _kronos_vol(ticker: str, returns: list, lookback: int, horizon: int) -> dict:
    """Attempt to use Kronos; fall back on any error."""
    try:
        import torch

        if "model" not in _model_cache:
            vendor = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "kronos"
            )
            # Dynamic import from vendor directory
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "kronos_model", os.path.join(vendor, "model.py")
            )
            if spec is None:
                raise ImportError("kronos model.py not found")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            model = mod.KronosModel()
            model.eval()
            _model_cache["model"] = model

        model = _model_cache["model"]
        window = returns[-lookback:] if len(returns) >= lookback else returns
        x = torch.tensor(window, dtype=torch.float32).unsqueeze(0).unsqueeze(-1)
        with torch.no_grad():
            out = model(x)
        # Extract volatility from residual std of forecast errors (NOT directional)
        forecast_vals = out.squeeze().numpy() if hasattr(out, "numpy") else np.array(out)
        vol_pct = float(np.std(forecast_vals) * np.sqrt(252) * 100)

        arr = np.array(returns[-252:], dtype=float)
        rolling = [
            float(np.std(arr[i - 30: i], ddof=1) * np.sqrt(252) * 100)
            for i in range(30, len(arr))
        ]
        percentile = int(np.mean(np.array(rolling) <= vol_pct) * 100) if rolling else 50
        signal = 1 if percentile <= 40 else (-1 if percentile >= 80 else 0)

        return {
            "expected_volatility_pct": round(vol_pct, 2),
            "volatility_percentile": percentile,
            "signal": signal,
            "method": "kronos",
        }
    except Exception:
        return _ewma_vol(returns, horizon=horizon)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def forecast(ticker: str, price_data: dict, lookback: int = 120, horizon: int = 7) -> dict:
    """
    Forecast volatility. Returns dict with:
        expected_volatility_pct, volatility_percentile, signal (-1/0/+1), method.
    Never raises.
    """
    try:
        history = price_data.get("history") or []
        prices = [float(p) for p in history if p is not None and float(p) > 0]
        if len(prices) < 30:
            return NEUTRAL.copy()
        returns = [(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
        if not returns:
            return NEUTRAL.copy()

        if _kronos_available():
            return _kronos_vol(ticker, returns, lookback, horizon)
        return _ewma_vol(returns, horizon=horizon)
    except Exception as e:
        return {**NEUTRAL, "_error": str(e)}
