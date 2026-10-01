import pandas as pd
import numpy as np
from indicators import add_indicators

def run_backtest(df, symbol, capital=100000, risk_pct=1.0,
                 atr_stop_mult=1.5, atr_trail_mult=2.0,
                 target1_r=1.5, target2_r=3.0,
                 max_hold_days=15, cost_pct=0.20):
    """
    Simple R-based backtest engine.
    Returns list of trade dicts.
    """
    d = add_indicators(df)
    if len(d) < 220:
        return []

    trades = []
    position = None
    nifty_above = True  # Simplification; real app mein Nifty filter add karo

    for i in range(200, len(d)):
        row = d.iloc[i]
        prev = d.iloc[i-1]

        # === ENTRY LOGIC ===
        if position is None:
            # Setup A: Momentum Breakout
            momentum = (
                row["close"] > row["high20"] and
                row["volume"] > 1.5 * row["vol_sma20"] and
                55 <= row["rsi"] <= 70 and
                row["macd"] > 0 and
                row["close"] > row["ema200"]
            )
            # Setup B: Mean Reversion
            reversion = (
                30 <= row["rsi"] <= 40 and
                row["rsi"] > prev["rsi"] and
                row["close"] > row["open"] and
                abs(row["close"] - row["ema20"]) / row["ema20"] < 0.02
            )

            if momentum or reversion:
                entry = row["close"]
                stop = entry - atr_stop_mult * row["atr"]
                risk = entry - stop
                qty = int((capital * risk_pct / 100) / risk) if risk > 0 else 0
                if qty > 0:
                    position = {
                        "entry": entry, "stop": stop, "qty": qty,
                        "risk": risk, "entry_idx": i,
                        "target1": entry + target1_r * risk,
                        "target2": entry + target2_r * risk,
                        "half_exited": False,
                        "entry_date": d.index[i],
                    }

        # === EXIT LOGIC ===
        elif position is not None:
            entry = position["entry"]
            stop = position["stop"]
            risk = position["risk"]
            qty = position["qty"]
            days_held = i - position["entry_idx"]

            exit_price = None
            exit_reason = None

            # Stop loss
            if row["low"] <= stop:
                exit_price = stop
                exit_reason = "Stop Loss"

            # Target 1 (half exit)
            elif not position["half_exited"] and row["high"] >= position["target1"]:
                position["half_exited"] = True
                # Trail stop to breakeven
                position["stop"] = entry

            # Target 2
            elif position["half_exited"] and row["high"] >= position["target2"]:
                exit_price = position["target2"]
                exit_reason = "Target 2"

            # Trailing stop
            elif position["half_exited"]:
                new_stop = row["close"] - atr_trail_mult * row["atr"]
                if new_stop > position["stop"]:
                    position["stop"] = new_stop
                if row["low"] <= position["stop"]:
                    exit_price = position["stop"]
                    exit_reason = "Trailing Stop"

            # Time stop
            elif days_held >= max_hold_days:
                exit_price = row["close"]
                exit_reason = "Max Hold"

            if exit_price:
                gross_pnl = (exit_price - entry) * qty
                cost = (entry + exit_price) * qty * (cost_pct / 100)
                net_pnl = gross_pnl - cost
                r_multiple = net_pnl / (risk * qty) if risk * qty > 0 else 0

                trades.append({
                    "symbol": symbol,
                    "entry_date": position["entry_date"],
                    "exit_date": d.index[i],
                    "entry": round(entry, 2),
                    "exit": round(exit_price, 2),
                    "qty": qty,
                    "pnl": round(net_pnl, 2),
                    "r_multiple": round(r_multiple, 2),
                    "exit_reason": exit_reason,
                    "days_held": days_held,
                })
                position = None

    return trades

def calculate_metrics(trades, capital=100000):
    """Backtest metrics calculate karta hai."""
    if not trades:
        return {}
    tdf = pd.DataFrame(trades)
    wins = tdf[tdf["pnl"] > 0]
    losses = tdf[tdf["pnl"] <= 0]

    total_return = tdf["pnl"].sum() / capital * 100
    win_rate = len(wins) / len(tdf) * 100 if len(tdf) > 0 else 0
    avg_win = wins["pnl"].mean() if len(wins) > 0 else 0
    avg_loss = losses["pnl"].mean() if len(losses) > 0 else 0
    profit_factor = abs(wins["pnl"].sum() / losses["pnl"].sum()) if len(losses) > 0 and losses["pnl"].sum() != 0 else float("inf")
    avg_r = tdf["r_multiple"].mean()

    return {
        "Total Trades": len(tdf),
        "Win Rate %": round(win_rate, 1),
        "Total Return %": round(total_return, 2),
        "Avg Win ₹": round(avg_win, 2),
        "Avg Loss ₹": round(avg_loss, 2),
        "Profit Factor": round(profit_factor, 2),
        "Avg R": round(avg_r, 2),
        "Avg Hold Days": round(tdf["days_held"].mean(), 1),
    }
