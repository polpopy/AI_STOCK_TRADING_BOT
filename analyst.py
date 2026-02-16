import os
import yfinance as yf
import ta
import pandas as pd
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from colorama import Fore, init

# --- 1. SMART AUTHENTICATION ---
init(autoreset=True)

# THE SWITCHER: We check GitHub Secrets first, then fall back to config.py
ALPACA_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET = os.getenv('ALPACA_SECRET_KEY')

# If GitHub Secrets are empty (running on your laptop), try the local config file
if not ALPACA_KEY:
    try:
        import config
        ALPACA_KEY = config.ALPACA_API_KEY
        ALPACA_SECRET = config.ALPACA_SECRET_KEY
        print(f"{Fore.CYAN}[i] Running in LOCAL mode using config.py")
    except ImportError:
        pass

# Final check: If both are empty or still the default text, stop for safety
if not ALPACA_KEY or ALPACA_KEY == "YOUR_API_KEY_HERE":
    print(f"{Fore.RED}❌ ERROR: No valid keys found in Secrets OR config.py!")
    exit(1)

# Connect to Alpaca
trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

# --- 2. TRADING ENGINE ---

def get_market_regime():
    """Checks the 'Weather' of the overall US Market."""
    try:
        # threads=False prevents the cloud from freezing the connection
        spy = yf.download("SPY", period="250d", progress=False, threads=False)
        if isinstance(spy.columns, pd.MultiIndex):
            spy.columns = spy.columns.get_level_values(0)
        
        current_price = spy['Close'].iloc[-1]
        ema_200 = ta.trend.ema_indicator(spy['Close'], window=200).iloc[-1]
        
        return "BULL" if current_price > ema_200 else "BEAR"
    except Exception as e:
        print(f"Market Check Error: {e}")
        return "BEAR" # Safety default

def analyze_and_trade():
    """The core brain that scans and executes trades."""
    print(f"{Fore.YELLOW}🚀 Starting AI Market Scan...")
    
    # Check Market Shield Status
    if get_market_regime() == "BEAR":
        print(f"{Fore.RED}[!] Market Shield is RED (BEAR). New buys are locked for safety.")
        return

    # Watchlist parameters (Matches your dashboard)
    watchlist = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "PLTR", "SMCI"]
    
    # Don't buy what you already own
    current_holdings = [p.symbol for p in trading_client.get_all_positions()]
    
    for symbol in watchlist:
        if symbol in current_holdings:
            continue
            
        try:
            df = yf.download(symbol, period="100d", progress=False, threads=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            price = df['Close'].iloc[-1]
            ema = ta.trend.ema_indicator(df['Close'], window=50).iloc[-1]
            rsi = ta.momentum.rsi(df['Close'], window=21).iloc[-1]
            macd = ta.trend.macd(df['Close']).iloc[-1]
            macd_s = ta.trend.macd_signal(df['Close']).iloc[-1]
            
            # --- THE SCORING SYSTEM ---
            score = 0
            if price > ema: score += 50      # Weight 50: Trend is up
            if macd > macd_s: score += 30    # Weight 30: Momentum is up
            if rsi < 55: score += 20         # Weight 20: Not overbought
            
            print(f" > {symbol:<5} | Score: {score} | RSI: {rsi:.1f} | Price: ${price:.2f}")

            # Execution: Buy if Score is 80 or higher
            if score >= 80:
                qty = int(5000 / price) # Buying $5,000 blocks
                if qty > 0:
                    order = MarketOrderRequest(
                        symbol=symbol, qty=qty, 
                        side=OrderSide.BUY, time_in_force=TimeInForce.DAY
                    )
                    trading_client.submit_order(order)
                    print(f"{Fore.GREEN}✅ SUCCESS: Bought {qty} shares of {symbol}")
        except Exception as e:
            print(f"Skipping {symbol} due to error: {e}")

# --- 3. DASHBOARD BRIDGE (For the Streamlit Button) ---
def run_full_scan():
    """Returns signals to the dashboard website without trading."""
    watchlist = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "PLTR", "SMCI"]
    results = []
    for symbol in watchlist:
        try:
            df = yf.download(symbol, period="100d", progress=False, threads=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            price = float(df['Close'].iloc[-1])
            rsi = float(ta.momentum.rsi(df['Close'], window=21).iloc[-1])
            
            # Translate RSI into a simple dashboard signal
            signal = "HOLD 🟡"
            if rsi < 35: signal = "BUY 🟢"
            elif rsi > 70: signal = "SELL 🔴"
            
            results.append({"ticker": symbol, "price": price, "signal": signal})
        except:
            results.append({"ticker": symbol, "price": 0, "signal": "ERROR"})
    return results

# --- 4. EXECUTION ---
if __name__ == "__main__":
    # When GitHub Actions wakes up, it runs this function
    analyze_and_trade()
