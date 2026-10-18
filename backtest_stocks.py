import yfinance as yf
import ta
import pandas as pd
import numpy as np
from colorama import Fore, init

init(autoreset=True)

WATCHLIST = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD", "PLTR", "SMCI"]
STARTING_BALANCE = 100000.0 
RSI_WIN = 21             
EMA_WIN = 50          
STOP_MULT = 4              

print(f"{Fore.CYAN}[*] Downloading 3-year data for all stocks...")
all_data = {s: yf.download(s, period="3y", interval="1d", progress=False) for s in WATCHLIST}

for s in WATCHLIST:
    if isinstance(all_data[s].columns, pd.MultiIndex):
        all_data[s].columns = all_data[s].columns.get_level_values(0)

balance = STARTING_BALANCE
portfolio = {} 
total_trades = 0
wins = 0

all_dates = sorted(set(all_data[WATCHLIST[0]].index))

print(f"{Fore.YELLOW}[*] Starting 3-Year Portfolio Simulation... 🚀\n")

for date in all_dates:
    symbols_to_sell = []
    for symbol, info in portfolio.items():
        if date not in all_data[symbol].index: continue
        row = all_data[symbol].loc[date]

        if row['High'] > info['hi_price']:
            info['hi_price'] = row['High']
            vol = all_data[symbol]['Close'][:date].pct_change().rolling(20).std().iloc[-1] * 100
            new_stop = info['hi_price'] * (1 - (vol/100 * STOP_MULT))
            if new_stop > info['stop']: info['stop'] = new_stop

        if row['Low'] <= info['stop']:
            balance += info['shares'] * info['stop']
            profit = (info['shares'] * info['stop']) - (info['shares'] * info['buy_price'])
            if profit > 0: wins += 1
            symbols_to_sell.append(symbol)
            print(f"{Fore.RED}[{date.date()}] EXIT {symbol} @ ${info['stop']:,.2f} | Profit: ${profit:,.2f}")

    for s in symbols_to_sell: portfolio.pop(s)

    if balance >= TRADE_CASH:
        for symbol in WATCHLIST:
            if symbol in portfolio or date not in all_data[symbol].index: continue
            
            df = all_data[symbol][:date] 
            if len(df) < 50: continue
            
            ema = ta.trend.ema_indicator(df['Close'], window=EMA_WIN).iloc[-1]
            rsi = ta.momentum.rsi(df['Close'], window=RSI_WIN).iloc[-1]
            macd = ta.trend.macd(df['Close']).iloc[-1]
            macd_s = ta.trend.macd_signal(df['Close']).iloc[-1]
            price = df['Close'].iloc[-1]
            vol = df['Close'].pct_change().rolling(20).std().iloc[-1] * 100
            
            score = 0
            if price > ema: score += 50           
            if macd > macd_s: score += 30         
            if rsi < 55: score += 20             
            if score >= 80:
                shares = int(TRADE_CASH / price)
                if shares > 0:
                    balance -= (shares * price)
                    portfolio[symbol] = {
                        'shares': shares,
                        'buy_price': price,
                        'hi_price': price,
                        'stop': price * (1 - (vol/100 * STOP_MULT))
                    }
                    total_trades += 1
                    print(f"{Fore.GREEN}[{date.date()}] ENTRY {symbol} @ ${price:,.2f}")

current_holdings_val = sum(info['shares'] * all_data[s]['Close'].iloc[-1] for s, info in portfolio.items())
final_val = balance + current_holdings_val
total_profit = final_val - STARTING_BALANCE
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

print(f"\n{Fore.WHITE}=========================================")
print(f"{Fore.MAGENTA}📊 FINAL PORTFOLIO RESULTS")
print(f"{Fore.WHITE}=========================================")
print(f"Watchlist:      {WATCHLIST}")
print(f"Final Value:    ${final_val:,.2f}")
print(f"Total Profit:   ${total_profit:,.2f}")
print(f"Win Rate:       {win_rate:.1f}%")
print(f"Total Trades:   {total_trades}")
