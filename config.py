import streamlit as st

# This logic checks if we are in the cloud (Streamlit) or local
try:
    # CLOUD MODE: Look in Streamlit Secrets
    ALPACA_API_KEY = st.secrets["ALPACA_API_KEY"]
    ALPACA_SECRET_KEY = st.secrets["ALPACA_SECRET_KEY"]
except:
    # LOCAL MODE: Use these blanks or your local keys while testing
    # When you upload to GitHub, keep these as empty strings ""
    ALPACA_API_KEY = "" 
    ALPACA_SECRET_KEY = ""

# Keep your other optimized parameters here!
WATCHLIST = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "PLTR", "SMCI"]
RSI_WINDOW = 21   
EMA_WINDOW = 50   
TRADE_AMOUNT = 5000