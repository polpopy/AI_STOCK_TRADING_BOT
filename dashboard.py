import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import config
import analyst  # <-- We are importing your Brain file here!
from alpaca.trading.client import TradingClient
from datetime import datetime

st.set_page_config(page_title="Polpo & Klamo nite AI Trading Hub", layout="wide", page_icon="📈")

trading_client = TradingClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, paper=True)

if st.sidebar.button("Run Manual Scan Now"):
    st.sidebar.info("⏳ Scanning Markets... Please wait.")
    scan_results = analyst.run_full_scan()
    
    st.sidebar.write("---")
    st.sidebar.write("### 📡 Scan Results:")
    for res in scan_results:
        if res['signal'] == "ERROR":
            st.sidebar.error(f"{res['ticker']}: Data Error")
        else:
            st.sidebar.write(f"**{res['ticker']}**: {res['signal']} (${res['price']:.2f})")

st.title("📊 Portfolio Overview")

try:
    account = trading_client.get_account()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Cash Balance", f"${float(account.cash):,.2f}")
    col2.metric("Buying Power", f"${float(account.buying_power):,.2f}")
    col3.metric("Equity", f"${float(account.equity):,.2f}")
except Exception as e:
    st.error(f"Alpaca Connection Error: {e}")
    col1, col2, col3, col4 = st.columns(4) 

try:

    spy = yf.download("SPY", period="5d", interval="1d", progress=False, threads=False)
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    market_price = spy['Close'].iloc[-1]
    market_status = "🟢 BULL" if market_price > spy['Close'].mean() else "🔴 BEAR"
    col4.metric("Market Shield", market_status)
except:
    col4.metric("Market Shield", "⚠️ ERROR")

st.write("### 🕯️ Watchlist Technicals")
selected_stock = st.selectbox("Select a stock to inspect:", config.WATCHLIST)

clean_ticker = selected_stock.strip()
data = yf.download(clean_ticker, period="60d", interval="1d", progress=False, threads=False)

if data.empty:
    st.error(f"⚠️ Yahoo Finance returned no data for {clean_ticker}.")
else:

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    x_dates = data.index.strftime('%Y-%m-%d').tolist()
    open_data = data['Open'].tolist()
    high_data = data['High'].tolist()
    low_data = data['Low'].tolist()
    close_data = data['Close'].tolist()

    try:
        fig = go.Figure(data=[go.Candlestick(
            x=x_dates,
            open=open_data, 
            high=high_data,
            low=low_data, 
            close=close_data,
            name="Price"
        )])
        fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Chart Drawing Error: {e}")
        
st.write("---")
st.write("### 📁 Active Positions")

try:
   
    positions = trading_client.get_all_positions()

    if not positions:
        st.info("No active trades. Bot is waiting for signals.")
    else:
     
        md_table = "| Symbol | Qty | Entry Price | Current Price | P/L ($) | P/L (%) |\n"
        md_table += "|---|---|---|---|---|---|\n"
        
        for p in positions:
            symbol = str(p.symbol)
            qty = str(p.qty)
            entry = f"${float(p.avg_entry_price):.2f}"
            current = f"${float(p.current_price):.2f}"
            pl_usd = f"${float(p.unrealized_pl):.2f}"
            pl_percent = f"{float(p.unrealized_plpc)*100:.2f}%"
            
            md_table += f"| **{symbol}** | {qty} | {entry} | {current} | {pl_usd} | {pl_percent} |\n"
        

        st.markdown(md_table)

except Exception as e:
    st.error(f"Could not load positions: {e}")
