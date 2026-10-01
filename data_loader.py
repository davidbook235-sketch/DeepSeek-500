import pandas as pd
import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta

NIFTY500_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

@st.cache_data(ttl=86400)
def get_nifty500_symbols():
    """NSE se Nifty 500 list fetch karta hai."""
    try:
        df = pd.read_csv(NIFTY500_URL)
        df.columns = [c.strip() for c in df.columns]
        symbols = df["Symbol"].dropna().astype(str).str.strip().tolist()
        return [s + ".NS" for s in symbols]
    except Exception as e:
        st.warning(f"NSE se list nahi mili, fallback use kar rahe hain: {e}")
        return [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
            "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS",
            "LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS","TITAN.NS",
            "SUNPHARMA.NS","BAJFINANCE.NS","WIPRO.NS","ONGC.NS","NTPC.NS",
            "TATAMOTORS.NS","TATASTEEL.NS","POWERGRID.NS","COALINDIA.NS",
            "ADANIENT.NS","ADANIPORTS.NS","JSWSTEEL.NS","GRASIM.NS",
            "HCLTECH.NS","TECHM.NS","ULTRACEMCO.NS","NESTLEIND.NS",
            "DRREDDY.NS","CIPLA.NS","DIVISLAB.NS","EICHERMOT.NS",
            "HEROMOTOCO.NS","BAJAJ-AUTO.NS","BRITANNIA.NS","INDUSINDBK.NS",
        ]

@st.cache_data(ttl=3600)
def fetch_ohlcv(symbol, period="2y", interval="1d"):
    """Single stock ka OHLCV data fetch karta hai."""
    try:
        df = yf.download(symbol, period=period, interval=interval,
                         progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.lower)
        df.index = pd.to_datetime(df.index)
        return df.dropna()
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_nifty_index(period="2y"):
    """Nifty 50 index data for regime filter."""
    return fetch_ohlcv("^NSEI", period=period)
