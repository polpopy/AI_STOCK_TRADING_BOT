import yfinance as yf
import ta
import pandas as pd
import config # Imports your keys and settings from config.py
import schedule
import time
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from colorama import Fore, init

# Initialize colorama to make terminal text colorful and readable
init(autoreset=True)

# ---------------------------------------------------------
# 1. INITIALIZATION: Setting up the 'Hands'
# ---------------------------------------------------------
# We connect to Alpaca using the keys in config.py. 
# paper=True ensures we only use the $100,000 fake money.
trading_client = TradingClient(config.ALPACA_API_KEY, config.ALPACA_SECRET_KEY, paper=True)

def get_market_regime():
    """
    Checks the 'Weather' of the overall US Stock Market.
    If the S&P 500 (SPY) is below its 200-day average, we assume 
    a 'Bear Market' and stop all buying for safety.
    """
    # Download 250 days of data for the S&P 500 ETF (SPY)
    spy = yf.download("SPY", period="250d", interval="1d", progress=False)
    
    # Clean up column names in case yfinance uses a MultiIndex
    if isinstance(spy.columns, pd.MultiIndex):
        spy.columns = spy.columns.get_level_values(0)
    
    current_spy_price = spy['Close'].iloc[-1]
    
    # Calculate the 200-day Exponential Moving Average (EMA)
    spy_ema_200 = ta.trend.ema_indicator(spy['Close'], window=200).iloc[-1]
    
    # If price is above the EMA, the market is 'Healthy' (BULL)
    return "BULL" if current_spy_price > spy_ema_200 else "BEAR"

def manage_exits():
    """
    Looks at the stocks we currently own and decides if we should sell.
    It uses a 'Trailing Stop' logic: if a stock drops too far from 
    its entry price, we cut the loss.
    """
    # Get a list of all stocks we currently hold in Alpaca
    positions = trading_client.get_all_positions()
    
    for position in positions:
        symbol = position.symbol
        
        # Download recent data for the stock we own
        df = yf.download(symbol, period="20d", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        current_price = float(position.current_price)
        entry_price = float(position.avg_entry_price)
        
        # Calculate Volatility (Standard Deviation of daily returns)
        # This tells us how 'jumpy' the stock is.
        vol = (df['Close'].pct_change().rolling(20).std().iloc[-1]) * 100
        
        # DYNAMIC STOP LOSS: We sell if the price drops more than 4x its volatility.
        # This gives high-growth stocks like NVDA room to breathe.
        stop_price = entry_price * (1 - (vol/100 * 4)) 
        
        if current_price <= stop_price:
            print(f"{Fore.RED}[!] EXIT SIGNAL: {symbol} hit stop loss at ${current_price:,.2f}")
            # Sell the entire position immediately
            trading_client.close_position(symbol)

def analyze_and_trade():
    """
    The main 'Brain' that scans for new buying opportunities.
    It uses the Winning Parameters found in our Grid Search.
    """
    # STEP A: Check Market Weather
    if get_market_regime() == "BEAR":
        print(f"{Fore.RED}[!] Market is in BEAR regime. No new buys today.")
        return

    # STEP B: See what we already own so we don't buy the same stock twice
    current_holdings = [p.symbol for p in trading_client.get_all_positions()]
    
    best_candidate = None
    highest_score = -100
    
    # STEP C: Scan every stock in our Watchlist (from config.py)
    for symbol in config.WATCHLIST:
        if symbol in current_holdings:
            continue # Skip stocks we already own
        
        try:
            # Get 100 days of history to calculate our indicators
            df = yf.download(symbol, period="100d", interval="1d", progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            # --- CALCULATE THE THREE AGENTS ---
            # AGENT B: Trend (EMA 50)
            ema = ta.trend.ema_indicator(df['Close'], window=config.EMA_WINDOW).iloc[-1]
            # AGENT A: Value (RSI 21)
            rsi = ta.momentum.rsi(df['Close'], window=config.RSI_WINDOW).iloc[-1]
            # AGENT E: Momentum (MACD)
            macd = ta.trend.macd(df['Close']).iloc[-1]
            macd_s = ta.trend.macd_signal(df['Close']).iloc[-1]
            
            price = df['Close'].iloc[-1]
            
            # --- THE SCORING ENGINE ---
            score = 0
            if price > ema: score += 50      # Weight 50: Is it in an uptrend?
            if macd > macd_s: score += 30    # Weight 30: Is momentum pushing up?
            if rsi < 55: score += 20         # Weight 20: Is it not too expensive?
            
            print(f"   > {symbol:<6} | Score: {score} | RSI: {rsi:.1f}")

            # We only buy if the score is 80 or higher (High Conviction)
            if score >= 80 and score > highest_score:
                highest_score = score
                best_candidate = {'symbol': symbol, 'price': price}
        except Exception as e:
            continue # If data fails for one stock, skip to the next
        
    # STEP D: Execute the trade
    if best_candidate:
        # Calculate shares based on our $5,000 trade limit in config.py
        qty = int(config.TRADE_AMOUNT / best_candidate['price'])
        
        if qty > 0:
            order_request = MarketOrderRequest(
                symbol=best_candidate['symbol'],
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            # Submit the order to Alpaca
            trading_client.submit_order(order_data=order_request)
            print(f"{Fore.GREEN}✅ BOUGHT {qty} shares of {best_candidate['symbol']} at ${best_candidate['price']:.2f}")

def main_loop():
    """
    The orchestrator that runs the bot's workflow.
    """
    print(f"\n{Fore.CYAN}--- 🤖 BOT CYCLE START ({time.strftime('%H:%M:%S')}) ---")
    
    # Stop the bot if the US Market is closed
    if not trading_client.get_clock().is_open:
        print(f"{Fore.YELLOW}[i] Market is currently closed. Going to sleep...")
        return
        
    manage_exits()       # Rule 1: Manage what we have (Sell losers)
    analyze_and_trade()  # Rule 2: Scan for what to get (Buy winners)

# ---------------------------------------------------------
# 3. SCHEDULER: Keeping the bot alive
# ---------------------------------------------------------
if __name__ == "__main__":
    main_loop() # Run immediately when you start the script
    
    # Run the bot every 1 hour during market hours
    schedule.every(1).hours.do(main_loop)
    
    while True:
        schedule.run_pending()
        time.sleep(1) # Sleep to save CPU usage