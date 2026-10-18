import streamlit as st


try:
    ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
except:
    ALPACA_API_KEY = "" 
    ALPACA_SECRET_KEY = ""

WATCHLIST = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "PLTR", "SMCI"]
RSI_WINDOW = 21   
EMA_WINDOW = 50   
TRADE_AMOUNT = 5000
