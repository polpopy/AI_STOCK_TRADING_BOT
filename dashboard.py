import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import config
import analyst  # <-- We are importing your Brain file here!
from alpaca.trading.client import TradingClient
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Polpo & Klamo nite AI Trading Hub", layout="wide", page_icon="📈")

# --- 2. CONNECT TO ALPACA ---
# This uses the same 'Hands' we set up for your bot
trading_client = TradingClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, paper=True)

# --- 3. SIDEBAR (Control Panel) ---
# UPGRADED: Button is now connected to analyst.py (Crash-proof version)
if st.sidebar.button("Run Manual Scan Now"):
    st.sidebar.info("⏳ Scanning Markets... Please wait.")
    scan_results = analyst.run_full_scan() # Triggers the logic
    
    st.sidebar.write("---")
    st.sidebar.write("### 📡 Scan Results:")
    for res in scan_results:
        if res['signal'] == "ERROR":
            st.sidebar.error(f"{res['ticker']}: Data Error")
        else:
            st.sidebar.write(f"**{res['ticker']}**: {res['signal']} (${res['price']:.2f})")

# --- 4. TOP ROW: LIVE METRICS ---
st.title("📊 Portfolio Overview")

try:
    account = trading_client.get_account()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cash Balance", f"${float(account.cash):,.2f}")
    col2.metric("Buying Power", f"${float(account.buying_power):,.2f}")
    col3.metric("Equity", f"${float(account.equity):,.2f}")
except Exception as e:
    st.error(f"Alpaca Connection Error: {e}")
    col1, col2, col3, col4 = st.columns(4) # Fallback columns

# Check Market Shield Status (S&P 500)
try:
    # UPGRADED: Added threads=False to prevent cloud freeze
    spy = yf.download("SPY", period="5d", interval="1d", progress=False, threads=False)
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    market_price = spy['Close'].iloc[-1]
    market_status = "🟢 BULL" if market_price > spy['Close'].mean() else "🔴 BEAR"
    col4.metric("Market Shield", market_status)
except:
    col4.metric("Market Shield", "⚠️ ERROR")

# --- 5. MIDDLE ROW: LIVE CHARTS ---
st.write("### 🕯️ Watchlist Technicals")
selected_stock = st.selectbox("Select a stock to inspect:", config.WATCHLIST)

clean_ticker = selected_stock.strip()

# Fetch the data
data = yf.download(clean_ticker, period="60d", interval="1d", progress=False, threads=False)

if data.empty:
    st.error(f"⚠️ Yahoo Finance returned no data for {clean_ticker}.")
else:
    # Flatten any weird Yahoo column structures
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    # Force the index (dates) to be standard and timezone-naive
    data.index = pd.to_datetime(data.index).tz_localize(None)

    # Draw the chart (Bug fixed: Removed the float() wrappers!)
    try:
        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'], 
            high=data['High'],
            low=data['Low'], 
            close=data['Close'],
            name="Price"
        )])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart Drawing Error: {e}")
# --- 6. BOTTOM ROW: POSITIONS ---
st.write("### 📁 Active Positions")
try:
    positions = trading_client.get_all_positions()

    if not positions:
        st.write("No active trades. Bot is waiting for signals.")
    else:
        # Convert Alpaca positions to a clean table
        pos_data = []
        for p in positions:
            pos_data.append({
                "Symbol": p.symbol,
                "Qty": p.qty,
                "Entry Price": f"${float(p.avg_entry_price):.2f}",
                "Current Price": f"${float(p.current_price):.2f}",
                "P/L ($)": f"${float(p.unrealized_pl):.2f}"
            })
        st.table(pos_data)
except Exception as e:
    st.error(f"Error fetching positions: {e}")





