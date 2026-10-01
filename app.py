import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from config import DEFAULTS
from data_loader import get_nifty500_symbols, fetch_ohlcv, fetch_nifty_index
from scanner import check_momentum_breakout, check_mean_reversion_pullback
from backtest import run_backtest, calculate_metrics

st.set_page_config(
    page_title="Nifty 500 Pro Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ===== MOBILE-FRIENDLY CSS =====
st.markdown("""
<style>
    .main > div { padding: 1rem 0.5rem; }
    .stButton > button { width: 100%; padding: 0.6rem; font-size: 1rem; }
    .metric-card {
        background: #f0f2f6; border-radius: 10px;
        padding: 10px; margin: 5px 0;
    }
    @media (max-width: 768px) {
        .stMetric { font-size: 0.9rem; }
    }
</style>
""", unsafe_allow_html=True)

# ===== SIDEBAR SETTINGS =====
st.sidebar.header("⚙️ Settings")

capital = st.sidebar.number_input("Capital (₹)", value=100000, step=10000)
risk_pct = st.sidebar.slider("Risk per trade %", 0.5, 3.0, 1.0, 0.1)

st.sidebar.subheader("Scanner Filters")
min_score = st.sidebar.slider("Min Score", 40, 100, 70)
max_stocks = st.sidebar.slider("Max stocks to scan", 20, 501, 100)
nifty_filter = st.sidebar.checkbox("Nifty Regime Filter (50 EMA)", value=True)

st.sidebar.subheader("Backtest Settings")
backtest_years = st.sidebar.slider("Backtest Period (years)", 1, 5, 2)
exit_style = st.sidebar.selectbox("Exit Style", ["Target + Trail", "Target Only"])
max_hold = st.sidebar.slider("Max Hold Days", 5, 60, 15)
cost_pct = st.sidebar.slider("Cost per side %", 0.05, 0.50, 0.20, 0.05)

# ===== MAIN TABS =====
tab1, tab2, tab3 = st.tabs(["🔍 Scanner", "🧪 Backtest", "ℹ️ Rules"])

# ===== TAB 1: SCANNER =====
with tab1:
    st.header("📈 Nifty 500 Pro Scanner")

    if st.button("🚀 Run Scanner", type="primary"):
        symbols = get_nifty500_symbols()[:max_stocks]
        nifty_df = fetch_nifty_index(period=f"{backtest_years+1}y")

        # Nifty regime check
        nifty_above_ema = True
        if nifty_filter and nifty_df is not None and len(nifty_df) > 50:
            nifty_df["ema50"] = nifty_df["close"].ewm(span=50, adjust=False).mean()
            nifty_above_ema = nifty_df["close"].iloc[-1] > nifty_df["ema50"].iloc[-1]

        st.info(f"Nifty Regime: {'✅ Above 50 EMA' if nifty_above_ema else '⚠️ Below 50 EMA'}")

        results = []
        progress = st.progress(0)
        status = st.empty()

        for idx, sym in enumerate(symbols):
            status.text(f"Scanning {sym} ({idx+1}/{len(symbols)})...")
            df = fetch_ohlcv(sym, period="1y")
            if df is None or len(df) < 210:
                progress.progress((idx + 1) / len(symbols))
                continue

            m = check_momentum_breakout(df, nifty_above_ema)
            r = check_mean_reversion_pullback(df)

            if m:
                results.append({
                    "Symbol": sym.replace(".NS", ""),
                    "Setup": m["setup"],
                    "Entry": m["entry"],
                    "Stop": round(m["stop"], 2),
                    "RSI": m["rsi"],
                    "ATR": m["atr"],
                    "Score": 85,
                })
            if r:
                results.append({
                    "Symbol": sym.replace(".NS", ""),
                    "Setup": r["setup"],
                    "Entry": r["entry"],
                    "Stop": round(r["stop"], 2),
                    "RSI": r["rsi"],
                    "ATR": r["atr"],
                    "Score": 75,
                })

            progress.progress((idx + 1) / len(symbols))

        progress.empty()
        status.empty()

        if results:
            rdf = pd.DataFrame(results)
            rdf = rdf[rdf["Score"] >= min_score]
            rdf = rdf.sort_values("Score", ascending=False)

            st.success(f"✅ {len(rdf)} stocks mile!")
            st.dataframe(
                rdf,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Entry": st.column_config.NumberColumn(format="₹%.2f"),
                    "Stop": st.column_config.NumberColumn(format="₹%.2f"),
                }
            )

            # Chart for top pick
            if len(rdf) > 0:
                top = rdf.iloc[0]["Symbol"] + ".NS"
                st.subheader(f"📊 Top Pick: {top.replace('.NS','')}")
                df = fetch_ohlcv(top, period="6mo")
                if df is not None:
                    fig = go.Figure(data=[go.Candlestick(
                        x=df.index, open=df["open"], high=df["high"],
                        low=df["low"], close=df["close"]
                    )])
                    fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Koi stock nahi mila current filters se. Filters adjust karo.")

# ===== TAB 2: BACKTEST =====
with tab2:
    st.header("🧪 Portfolio Backtest")

    if st.button("▶️ Run Backtest", type="primary"):
        symbols = get_nifty500_symbols()[:max_stocks]
        nifty_df = fetch_nifty_index(period=f"{backtest_years+1}y")

        nifty_above_ema = True
        if nifty_filter and nifty_df is not None and len(nifty_df) > 50:
            nifty_df["ema50"] = nifty_df["close"].ewm(span=50, adjust=False).mean()
            nifty_above_ema = nifty_df["close"].iloc[-1] > nifty_df["ema50"].iloc[-1]

        all_trades = []
        progress = st.progress(0)
        status = st.empty()

        for idx, sym in enumerate(symbols):
            status.text(f"Backtesting {sym} ({idx+1}/{len(symbols)})...")
            df = fetch_ohlcv(sym, period=f"{backtest_years}y")
            if df is None or len(df) < 220:
                progress.progress((idx + 1) / len(symbols))
                continue

            trades = run_backtest(
                df, sym.replace(".NS", ""),
                capital=capital, risk_pct=risk_pct,
                max_hold_days=max_hold, cost_pct=cost_pct
            )
            all_trades.extend(trades)
            progress.progress((idx + 1) / len(symbols))

        progress.empty()
        status.empty()

        if all_trades:
            metrics = calculate_metrics(all_trades, capital)

            st.subheader("📊 Results")
            cols = st.columns(2)
            for i, (k, v) in enumerate(metrics.items()):
                with cols[i % 2]:
                    st.metric(k, v)

            st.subheader("📋 Trade Log")
            tdf = pd.DataFrame(all_trades)
            st.dataframe(tdf, use_container_width=True, hide_index=True)

            # Equity curve
            if len(tdf) > 0:
                tdf["cum_pnl"] = tdf["pnl"].cumsum()
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    y=tdf["cum_pnl"], mode="lines",
                    name="Cumulative PnL", line=dict(color="green")
                ))
                fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0))
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Koi trade nahi mila. Parameters adjust karo.")

# ===== TAB 3: RULES =====
with tab3:
    st.header("ℹ️ Strategy Rules")

    st.markdown("""
    ### Setup A: Momentum Breakout
    - RSI(14) between **55–70**
    - MACD zero line cross (recent)
    - 20-day high breakout with volume > 1.5x average
    - Price above 200 EMA
    - Nifty 50 above 50 EMA

    ### Setup B: Mean Reversion Pullback
    - RSI(14) between **30–40** and rising
    - Price near 20 EMA (within 2%)
    - Bullish candle confirmation
    - Volume > 0.8x average

    ### Position Sizing
    - Risk per trade: **1%** of capital
    - Max 8 positions
    - Stop loss: **1.5 × ATR** below entry

    ### Exit Rules
    - Target 1: **+1.5R** → 50% exit
    - Target 2: **+3R** → remaining exit
    - Trailing stop: **2 × ATR**
    - Max hold: **15 days**

    ### Nifty Regime Filter
    - Nifty > 50 EMA → Full exposure
    - Nifty < 50 EMA → No new entries
    """)
