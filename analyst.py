import os
import yfinance as yf
import ta
import pandas as pd
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from colorama import Fore, init

# --- 1. CLOUD-READY INITIALIZATION ---
init(autoreset=True)

# This section checks if we are on GitHub or your Laptop
try:
    import config
    ALPACA_KEY = config.ALPACA_API_KEY
    ALPACA_SECRET = config.ALPACA_SECRET_KEY
    RSI_W = config.RSI_WINDOW
    EMA_W = config.EMA_WINDOW
    WATCHLIST = config.WATCHLIST
    TRADE_AMT = config.TRADE_AMOUNT
except ImportError:
    # We are on GitHub Actions - use the Secrets we added
    ALPACA_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET = os.getenv('ALPACA_SECRET_KEY')
    # Default values if config is missing on GitHub
    RSI_W = 21
    EMA_W = 50
    WATCHLIST = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "PLTR", "SMCI"]
    TRADE_AMT = 5000

# Connect to Alpaca
trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

# --- 2. TRADING LOGIC AGENTS ---

def get_market_regime():
    """Checks the overall market weather."""
    try:
        spy = yf.download("SPY", period="250d", progress=False, threads=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)
        
        current_price = spy['Close'].iloc[-1]
        ema_200 = ta.trend.ema_indicator(spy['Close'], window=200).iloc[-1]
        return "BULL" if current_price > ema_200 else "BEAR"
    except:
        return "BEAR" # Safety default

def analyze_and_trade():
    """The core engine that scans and trades."""
    print(f"{Fore.CYAN}🚀 Starting AI Market Scan...")
    
    if get_market_regime() == "BEAR":
        print(f"{Fore.RED}[!] Market is BEARish. New buys disabled for safety.")
        return

    # Check what we already own
    current_holdings = [p.symbol for p in trading_client.get_all_positions()]
    
    for symbol in WATCHLIST:
        if symbol in current_holdings:
            continue
            
        try:
            df = yf.download(symbol, period="100d", progress=False, threads=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # Calculate Indicators
            price = df['Close'].iloc[-1]
            ema = ta.trend.ema_indicator(df['Close'], window=EMA_W).iloc[-1]
            rsi = ta.momentum.rsi(df['Close'], window=RSI_W).iloc[-1]
            macd = ta.trend.macd(df['Close']).iloc[-1]
            macd_s = ta.trend.macd_signal(df['Close']).iloc[-1]
            
            # Scoring Logic
            score = 0
            if price > ema: score += 50
            if macd > macd_s: score += 30
            if rsi < 55: score += 20
            
            print(f" > {symbol}: Score {score} (RSI: {rsi:.1f})")

            # Execute Buy if High Conviction (Score 80+)
            if score >= 80:
                qty = int(TRADE_AMT / price)
                if qty > 0:
                    order = MarketOrderRequest(
                        symbol=symbol, qty=qty, 
                        side=OrderSide.BUY, time_in_force=TimeInForce.DAY
                    )
                    trading_client.submit_order(order)
                    print(f"{Fore.GREEN}✅ BOUGHT {qty} shares of {symbol}")
        except Exception as e:
            print(f"Error scanning {symbol}: {e}")

# --- 3. THE DASHBOARD BRIDGE ---
def run_full_scan():
    """This function is specifically for the Streamlit website button."""
    results = []
    for symbol in WATCHLIST:
        try:
            df = yf.download(symbol, period="100d", progress=False, threads=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            price = float(df['Close'].iloc[-1])
            rsi = float(ta.momentum.rsi(df['Close'], window=RSI_W).iloc[-1])
            
            # Simplified Dashboard Signal
            signal = "HOLD 🟡"
            if rsi < 35: signal = "BUY 🟢"
            elif rsi > 70: signal = "SELL 🔴"
            
            results.append({"ticker": symbol, "price": price, "signal": signal})
        except:
            results.append({"ticker": symbol, "price": 0, "signal": "ERROR"})
    return results

# --- 4. EXECUTION ---
if __name__ == "__main__":
    # This runs when GitHub Actions wakes up
    analyze_and_trade()
