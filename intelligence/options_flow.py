"""
Enhanced Options Flow Intelligence.
Detects unusual options activity: volume > 3x OI, large premium bets.
Source: yfinance options chain (free).
"""
import yfinance as yf
from datetime import datetime, timedelta


def get_options_intelligence(ticker: str) -> dict:
    """
    Analyze options flow for unusual activity.
    Returns: {unusual_calls, unusual_puts, put_call_ratio,
              sentiment, signal_strength, largest_bet}
    """
    result = {
        "unusual_calls": False, "unusual_puts": False,
        "put_call_ratio": None, "sentiment": "NEUTRAL",
        "signal_strength": 0, "largest_bet": None,
    }

    # Skip for crypto and commodities
    if "-USD" in ticker or ticker in {"GC=F", "SI=F", "CL=F"}:
        return result

    try:
        t = yf.Ticker(ticker)
        expirations = t.options
        if not expirations:
            return result

        # Use next 2 expirations (most liquid)
        total_call_vol = 0
        total_put_vol = 0
        total_call_oi = 0
        total_put_oi = 0
        unusual_flags = []
        largest_premium = 0

        for exp in expirations[:2]:
            try:
                chain = t.option_chain(exp)
                calls = chain.calls
                puts = chain.puts

                call_vol = calls["volume"].sum() if "volume" in calls else 0
                put_vol = puts["volume"].sum() if "volume" in puts else 0
                call_oi = calls["openInterest"].sum() if "openInterest" in calls else 0
                put_oi = puts["openInterest"].sum() if "openInterest" in puts else 0

                total_call_vol += call_vol
                total_put_vol += put_vol
                total_call_oi += call_oi
                total_put_oi += put_oi

                # Flag unusual: volume > 3x OI
                if call_oi > 0 and call_vol > 3 * call_oi:
                    unusual_flags.append(f"Unusual call vol {exp}: {call_vol:.0f} vs OI {call_oi:.0f}")
                if put_oi > 0 and put_vol > 3 * put_oi:
                    unusual_flags.append(f"Unusual put vol {exp}: {put_vol:.0f} vs OI {put_oi:.0f}")

                # Find largest premium bet
                for df in [calls, puts]:
                    if "lastPrice" in df.columns and "openInterest" in df.columns:
                        df = df.copy()
                        df["premium"] = df["lastPrice"] * df["openInterest"] * 100
                        max_idx = df["premium"].idxmax()
                        if not max_idx is None:
                            p = df.loc[max_idx, "premium"]
                            if p > largest_premium:
                                largest_premium = p

            except Exception:
                continue

        # Put/call ratio
        if total_call_vol > 0:
            pcr = total_put_vol / total_call_vol
            result["put_call_ratio"] = round(pcr, 2)
            if pcr < 0.6:
                result["sentiment"] = "VERY_BULLISH"
            elif pcr < 0.8:
                result["sentiment"] = "BULLISH"
            elif pcr > 1.4:
                result["sentiment"] = "VERY_BEARISH"
            elif pcr > 1.1:
                result["sentiment"] = "BEARISH"

        result["unusual_calls"] = any("Unusual call" in f for f in unusual_flags)
        result["unusual_puts"] = any("Unusual put" in f for f in unusual_flags)
        result["unusual_flags"] = unusual_flags[:3]

        if largest_premium > 1_000_000:
            result["largest_bet"] = f"${largest_premium/1e6:.1f}M"

        # Signal strength
        if result["unusual_calls"] and result["sentiment"] in ("VERY_BULLISH", "BULLISH"):
            result["signal_strength"] = 1
        elif result["unusual_puts"] and result["sentiment"] in ("VERY_BEARISH", "BEARISH"):
            result["signal_strength"] = -1

    except Exception as e:
        result["error"] = str(e)

    return result
