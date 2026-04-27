"""
Enhanced Macro Intelligence — VIX, DXY, yields, BTC dominance, oil, sector rotation.
Replaces basic macro.py in data_sources/.
"""
import yfinance as yf
from datetime import datetime


def get_macro_intelligence() -> dict:
    """
    Fetch comprehensive macro data.
    Returns: {vix, dxy, ten_year_yield, btc_dominance, oil, gold, sp500_trend,
              regime, risk_status, sector_rotation_signal}
    """
    result = {}

    symbols = {
        "VIX": "^VIX",
        "DXY": "DX-Y.NYB",
        "TNX": "^TNX",  # 10Y treasury yield
        "SPY": "SPY",
        "OIL": "CL=F",
        "GOLD": "GC=F",
    }

    SECTOR_ETFS = {
        "Technology": "XLK",
        "Healthcare": "XLV",
        "Financials": "XLF",
        "Energy": "XLE",
        "Consumer Discretionary": "XLY",
        "Consumer Staples": "XLP",
        "Industrials": "XLI",
        "Utilities": "XLU",
        "Materials": "XLB",
        "Real Estate": "XLRE",
        "Communication Services": "XLC",
    }

    try:
        tickers = list(symbols.values()) + list(SECTOR_ETFS.values())
        data = {}
        for sym in tickers:
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="5d")
                if not hist.empty:
                    data[sym] = hist["Close"].iloc[-1]
            except Exception:
                pass

        vix = data.get("^VIX", 20)
        result["vix"] = round(vix, 1)

        # VIX-based risk regime
        if vix < 15:
            result["risk_regime"] = "LOW_FEAR"
            result["risk_status"] = "RISK_ON"
        elif vix < 20:
            result["risk_regime"] = "CALM"
            result["risk_status"] = "RISK_ON"
        elif vix < 25:
            result["risk_regime"] = "ELEVATED"
            result["risk_status"] = "NEUTRAL"
        elif vix < 35:
            result["risk_regime"] = "HIGH_FEAR"
            result["risk_status"] = "RISK_OFF"
        else:
            result["risk_regime"] = "EXTREME_FEAR"
            result["risk_status"] = "RISK_OFF"

        dxy = data.get("DX-Y.NYB", 100)
        result["dxy"] = round(dxy, 2)

        ten_yr = data.get("^TNX", 4.5)
        result["ten_year_yield"] = round(ten_yr, 2)

        oil = data.get("CL=F", 70)
        result["oil_price"] = round(oil, 1)

        gold = data.get("GC=F", 3000)
        result["gold_price"] = round(gold, 0)

        # SP500 trend (5d return of SPY as simple proxy)
        spy_now = data.get("SPY", 500)
        try:
            spy_hist = yf.Ticker("SPY").history(period="5d")["Close"]
            if len(spy_hist) >= 2:
                spy_5d_ret = (spy_hist.iloc[-1] - spy_hist.iloc[0]) / spy_hist.iloc[0] * 100
                if spy_5d_ret > 1.5:
                    result["sp500_trend"] = "BULLISH"
                elif spy_5d_ret < -1.5:
                    result["sp500_trend"] = "BEARISH"
                else:
                    result["sp500_trend"] = "NEUTRAL"
                result["sp500_5d_return"] = round(spy_5d_ret, 2)
        except Exception:
            result["sp500_trend"] = "NEUTRAL"

        # Sector rotation (1-month returns for SPDR ETFs)
        sector_returns = {}
        for sector_name, etf in SECTOR_ETFS.items():
            try:
                hist = yf.Ticker(etf).history(period="1mo")["Close"]
                if len(hist) >= 2:
                    ret = (hist.iloc[-1] - hist.iloc[0]) / hist.iloc[0] * 100
                    sector_returns[sector_name] = round(ret, 2)
            except Exception:
                pass

        if sector_returns:
            sorted_sectors = sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)
            leading = sorted_sectors[:3]
            lagging = sorted_sectors[-3:]

            signal = {}
            for sector, ret in sector_returns.items():
                if ret > 3:
                    signal[sector] = "FAVORABLE"
                elif ret < -3:
                    signal[sector] = "UNFAVORABLE"
                else:
                    signal[sector] = "NEUTRAL"

            result["sector_rotation_signal"] = signal
            result["leading_sectors"] = [s[0] for s in leading]
            result["lagging_sectors"] = [s[0] for s in lagging]
            result["sector_returns"] = sector_returns

        result["generated_at"] = datetime.utcnow().isoformat() + "Z"

    except Exception as e:
        result["error"] = str(e)
        result["vix"] = 20
        result["sp500_trend"] = "NEUTRAL"
        result["risk_status"] = "NEUTRAL"
        result["sector_rotation_signal"] = {}

    return result
