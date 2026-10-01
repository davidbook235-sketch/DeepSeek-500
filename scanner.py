import pandas as pd
from indicators import add_indicators

def check_momentum_breakout(df, nifty_above_ema200=True):
    """
    Setup A: Momentum Breakout (Trend Continuation)
    RSI 55-70, MACD zero line cross, 20-day high breakout, volume surge.
    """
    if len(df) < 210:
        return None
    d = add_indicators(df)
    latest = d.iloc[-1]
    prev = d.iloc[-2]

    if not nifty_above_ema200:
        return None

    # Trend filter
    if pd.isna(latest["ema200"]) or latest["close"] < latest["ema200"]:
        return None

    # RSI condition
    if not (55 <= latest["rsi"] <= 70):
        return None

    # MACD zero line cross (recent)
    macd_cross = (prev["macd"] < 0 and latest["macd"] > 0) or \
                 (prev["macd_hist"] < 0 and latest["macd_hist"] > 0)

    # Breakout condition
    breakout = latest["close"] > latest["high20"]

    # Volume surge
    vol_surge = latest["volume"] > 1.5 * latest["vol_sma20"]

    if macd_cross and breakout and vol_surge:
        return {
            "setup": "Momentum Breakout",
            "entry": latest["close"],
            "stop": latest["close"] - 1.5 * latest["atr"],
            "rsi": round(latest["rsi"], 1),
            "atr": round(latest["atr"], 2),
        }
    return None

def check_mean_reversion_pullback(df):
    """
    Setup B: Mean Reversion Pullback (High Win Rate)
    RSI 30-40 bounce, price near 20-EMA, bullish candle.
    """
    if len(df) < 50:
        return None
    d = add_indicators(df)
    latest = d.iloc[-1]
    prev = d.iloc[-2]

    # RSI bounce condition
    if not (30 <= latest["rsi"] <= 40 and latest["rsi"] > prev["rsi"]):
        return None

    # Price near 20-EMA
    near_ema = abs(latest["close"] - latest["ema20"]) / latest["ema20"] < 0.02

    # Bullish candle (close > open)
    bullish_candle = latest["close"] > latest["open"]

    # Volume confirmation
    vol_ok = latest["volume"] > 0.8 * latest["vol_sma20"]

    if near_ema and bullish_candle and vol_ok:
        return {
            "setup": "Mean Reversion Pullback",
            "entry": latest["close"],
            "stop": latest["close"] - 1.5 * latest["atr"],
            "rsi": round(latest["rsi"], 1),
            "atr": round(latest["atr"], 2),
        }
    return None
