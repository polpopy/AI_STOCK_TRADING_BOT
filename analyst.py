import os
import yfinance as yf
import ta
import pandas as pd
import schedule
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from colorama import Fore, init

# Try to import config, but don't crash if it's missing (it will be missing on GitHub)
try:
    import config
    ALPACA_KEY = config.ALPACA_API_KEY
    ALPACA_SECRET = config.ALPACA_SECRET_KEY
except ImportError:
    # On GitHub Actions, we pull from the Secrets you just added
    ALPACA_KEY = os.getenv('ALPACA_API_KEY')
    ALPACA_SECRET = os.getenv('ALPACA_SECRET_KEY')

# Initialize colorama
init(autoreset=True)

# ---------------------------------------------------------
# 1. INITIALIZATION: Setting up the 'Hands'
# ---------------------------------------------------------
trading_client = TradingClient(ALPACA_KEY, ALPACA_SECRET, paper=True)

def get_market_regime():
    """Checks the 'Weather' of the overall US Stock Market."""
    # UPGRADED: Added threads=False
    spy = yf.download("SPY", period="250d", interval="1d", progress=False, threads=False)
    
    if spy.empty:
        return "ERROR"

    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    
    current_spy_price = spy['Close'].iloc[-1]
    spy_ema_200 = ta.trend.ema_indicator(spy['Close'], window=200).iloc[-1]
    
    return "BULL" if current_spy_price > spy_ema_200 else "BEAR"

def manage_exits():
    """Looks at the stocks we currently own and decides if we should sell."""
    positions = trading_client.get_all_positions()
    
    for position in positions:
        symbol = position.symbol
        
        # UPGRADED: Added threads=False
        df = yf.download(symbol, period="20d", interval="1d", progress=False, threads=False)
        if df.empty:
            continue
            
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        current_price = float(position.current_price)
        entry_price = float(position.avg_entry_price)
        
        vol = (df['Close'].pct_change().rolling(20).std().iloc[-1]) * 100
        stop_price = entry_price * (1 - (vol/100 * 4)) 
        
        if current_price <= stop_price:
            print(f"{Fore.RED}[!] EXIT SIGNAL: {symbol} hit stop loss at ${current_price:,.2f}")
            trading_client.close_position(symbol)

def analyze_and_trade():
    """The main 'Brain' that scans for new buying opportunities."""
    if get_market_regime() == "BEAR":
        print(f"{Fore.RED}[!] Market is in BEAR regime. No new buys today.")
        return

    current_holdings = [p.symbol for p in trading_client.get_all_positions()]
    
    best_candidate = None
    highest_score = -100
    
    for symbol in config.WATCHLIST:
        if symbol in current_holdings:
            continue 
        
        try:
            # UPGRADED: Added threads=False
            df = yf.download(symbol, period="100d", interval="1d", progress=False, threads=False)
            if df.empty:
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            ema = ta.trend.ema_indicator(df['Close'], window=config.EMA_WINDOW).iloc[-1]
            rsi = ta.momentum.rsi(df['Close'], window=config.RSI_WINDOW).iloc[-1]
            macd = ta.trend.macd(df['Close']).iloc[-1]
            macd_s = ta.trend.macd_signal(df['Close']).iloc[-1]
            price = df['Close'].iloc[-1]
            
            score = 0
            if price > ema: score += 50      
            if macd > macd_s: score += 30    
            if rsi < 55: score += 20         
            
            print(f"   > {symbol:<6} | Score: {score} | RSI: {rsi:.1f}")

            if score >= 80 and score > highest_score:
                highest_score = score
                best_candidate = {'symbol': symbol, 'price': price}
        except Exception as e:
            continue 
        
    if best_candidate:
        qty = int(config.TRADE_AMOUNT / best_candidate['price'])
        if qty > 0:
            order_request = MarketOrderRequest(
                symbol=best_candidate['symbol'],
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            trading_client.submit_order(order_data=order_request)
            print(f"{Fore.GREEN}✅ BOUGHT {qty} shares of {best_candidate['symbol']} at ${best_candidate['price']:.2f}")

# ---------------------------------------------------------
# 2. THE STREAMLIT BRIDGE: Used only by dashboard.py
# ---------------------------------------------------------
def run_full_scan():
    """
    This function is explicitly for the Streamlit Dashboard button.
    It runs your scoring engine and returns the results to the website 
    without actually executing any trades.
    """
    results = []
    for symbol in config.WATCHLIST:
        try:
            df = yf.download(symbol, period="100d", interval="1d", progress=False, threads=False)
            if df.empty:
                results.append({"ticker": symbol, "signal": "ERROR", "price": 0.0})
                continue
                
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            price = float(df['Close'].iloc[-1])
            ema = float(ta.trend.ema_indicator(df['Close'], window=config.EMA_WINDOW).iloc[-1])
            rsi = float(ta.momentum.rsi(df['Close'], window=config.RSI_WINDOW).iloc[-1])
            macd = float(ta.trend.macd(df['Close']).iloc[-1])
            macd_s = float(ta.trend.macd_signal(df['Close']).iloc[-1])
            
            # Use your exact scoring engine
            score = 0
            if price > ema: score += 50
            if macd > macd_s: score += 30
            if rsi < 55: score += 20
            
            # Translate score into a signal for the dashboard
            if score >= 80:
                signal = f"STRONG BUY 🟢 (Score: {score})"
            elif score >= 50:
                signal = f"HOLD 🟡 (Score: {score})"
            else:
                signal = f"WEAK 🔴 (Score: {score})"
                
            results.append({"ticker": symbol, "price": price, "signal": signal})
        except Exception:
            results.append({"ticker": symbol, "signal": "ERROR", "price": 0.0})
            
    return results

# ---------------------------------------------------------
# 3. SCHEDULER: Keeping the bot alive
# ---------------------------------------------------------
def main_loop():
    print(f"\n{Fore.CYAN}--- 🤖 BOT CYCLE START ({time.strftime('%H:%M:%S')}) ---")
    if not trading_client.get_clock().is_open:
        print(f"{Fore.YELLOW}[i] Market is currently closed. Going to sleep...")
        return
        
    manage_exits()       
    analyze_and_trade()  

if __name__ == "__main__":
    main_loop() 
    schedule.every(1).hours.do(main_loop)
    while True:
        schedule.run_pending()
        time.sleep(1)

