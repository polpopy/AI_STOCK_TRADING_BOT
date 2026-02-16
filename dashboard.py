import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import config
from alpaca.trading.client import TradingClient
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Polpo & Klamo nite AI Trading Hub", layout="wide", page_icon="📈")

# --- 2. CONNECT TO ALPACA ---
# This uses the same 'Hands' we set up for your bot
trading_client = TradingClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, paper=True)

# --- 3. SIDEBAR (Control Panel) ---
st.sidebar.title("🤖 Bot Controls")
st.sidebar.info(f"Using Strategy: RSI({config.RSI_WINDOW}) + EMA({config.EMA_WINDOW})")
if st.sidebar.button("Run Manual Scan Now"):
    st.sidebar.write("Scan Triggered...") # We can link this to analyst.py later

# --- 4. TOP ROW: LIVE METRICS ---
account = trading_client.get_account()
st.title("📊 Portfolio Overview")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Cash Balance", f"${float(account.cash):,.2f}")
col2.metric("Buying Power", f"${float(account.buying_power):,.2f}")
col3.metric("Equity", f"${float(account.equity):,.2f}")

# Check Market Shield Status (S&P 500)
spy = yf.download("SPY", period="5d", interval="1d", progress=False)
if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
market_price = spy['Close'].iloc[-1]
market_status = "🟢 BULL" if market_price > spy['Close'].mean() else "🔴 BEAR"
col4.metric("Market Shield", market_status)

# --- 5. MIDDLE ROW: LIVE CHARTS ---
st.write("### 🕯️ Watchlist Technicals")
selected_stock = st.selectbox("Select a stock to inspect:", config.WATCHLIST)

# Download data for the chart
data = yf.download(selected_stock, period="60d", interval="1d", progress=False)
if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)

# Create a professional candlestick chart
fig = go.Figure(data=[go.Candlestick(
    x=data.index,
    open=data['Open'], high=data['High'],
    low=data['Low'], close=data['Close'],
    name="Price"
)])
fig.update_layout(template="plotly_dark", height=400)
st.plotly_chart(fig, use_container_width=True)

# --- 6. BOTTOM ROW: POSITIONS ---
st.write("### 📁 Active Positions")
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