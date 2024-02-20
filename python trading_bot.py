import os
import ccxt
import math
import time
import pandas as pd
import functools
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
api_key = os.getenv('BINANCE_API_KEY')
secret_key = os.getenv('BINANCE_API_SECRET')

assert api_key and secret_key, "API keys must be set as environment variables."
logging.info("API keys loaded successfully.")

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'enableRateLimit': True,
})
logging.info("Exchange initialized.")

symbol_info_cache = {}

def get_symbol_info(symbol):
    if symbol not in symbol_info_cache:
        logging.info(f"Fetching trading pair info for {symbol}")
        symbol_info_cache[symbol] = exchange.load_markets()[symbol]
    return symbol_info_cache[symbol]

def adjust_amount(symbol, amount):
    symbol_info = get_symbol_info(symbol)
    precision = symbol_info['precision']['amount']
    adjusted_amount = round(amount, precision)
    return max(adjusted_amount, symbol_info['limits']['amount']['min'])

def retry(exceptions, tries=4, delay=3, backoff=2):
    def deco_retry(func):
        @functools.wraps(func)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    logging.warning(f"{e}, Retrying in {mdelay} seconds...")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return func(*args, **kwargs)
        return f_retry
    return deco_retry

@retry((ccxt.NetworkError, ccxt.ExchangeError), tries=5, delay=2, backoff=2)
def fetch_data(symbol, candle_length='5m', limit=100):
    logging.info(f"Fetching data for {symbol} with candle length {candle_length}...")
    ohlcv = exchange.fetch_ohlcv(symbol, candle_length, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df.set_index('Timestamp', inplace=True)
    logging.info(f"Data fetched successfully. {len(df)} candles received.")
    return df

def calculate_rsi(df, period=14):
    logging.info("Calculating RSI...")
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    df['RSI'] = rsi
    df['RSI_SMA'] = df['RSI'].rolling(window=14).mean()
    logging.info("RSI calculated.")
    return df

def calculate_ema(df, period=3):
    logging.info(f"Calculating EMA_{period}...")
    df[f'EMA_{period}'] = df['Close'].ewm(span=period, adjust=False).mean()
    logging.info(f"EMA_{period} calculated.")
    return df

@retry((ccxt.NetworkError, ccxt.ExchangeError), tries=5, delay=2, backoff=2)
def print_balances():
    logging.info("Fetching balances...")
    balance = exchange.fetch_balance()
    logging.info(f"Available USDT: {balance['total']['USDT']}")

@retry((ccxt.NetworkError, ccxt.ExchangeError), tries=5, delay=2, backoff=2)
def check_and_execute_buy_order_rsi_ema(symbol, df):
    logging.info("Checking buy conditions...")
    current_rsi = df.iloc[-1]['RSI_SMA']
    current_ema3 = df.iloc[-1]['EMA_3']
    if current_rsi >= 62.8 and df.iloc[-1]['Close'] >= current_ema3:
        logging.info("Buy conditions met. Executing buy order...")
        balance = exchange.fetch_balance()
        usdt_balance = balance['total']['USDT']
        order_value = usdt_balance * 0.98  # Using 98% of USDT balance
        if order_value < 10:  # Check if the order value is sufficient
            logging.warning("Insufficient USDT balance for placing a buy order.")
            return
        order_amount = order_value / current_ema3  # Calculate the amount to buy based on EMA_3 price
        order_amount = math.floor(order_amount * 10**5) / 10**5  # Adjusting the amount based on Binance's precision requirements
        order = exchange.create_market_buy_order(symbol, order_amount)
        logging.info(f"Buy order placed: ID {order['id']} for {order_amount} {symbol} at market price.")
    else:
        logging.info("Buy conditions not met.")

@retry((ccxt.NetworkError, ccxt.ExchangeError), tries=5, delay=2, backoff=2)
def check_and_execute_sell_order_rsi_ema_2(symbol, df, amount):
    logging.info("Checking sell conditions...")
    df = calculate_ema(df, 2)  # Ensure the dataframe has the latest EMA_2
    current_rsi = df.iloc[-1]['RSI_SMA']
    current_ema2 = df.iloc[-1]['EMA_2']

    if current_rsi <= 62.8 or current_rsi >= 69.33:
        logging.info("Sell conditions met. Preparing to execute sell order at EMA_2 price...")
        
        # Adjust amount based on precision
        adjusted_amount = adjust_amount(symbol, amount)
        
        # Place a limit sell order at the EMA_2 price
        order = exchange.create_limit_sell_order(symbol, adjusted_amount, current_ema2)
        logging.info(f"Limit sell order placed: ID {order['id']} for {adjusted_amount} {symbol} at EMA_2 price {current_ema2}")
    else:
        logging.info("Sell conditions not met.")

def main():
    symbol = 'XRP/USDT'
    candle_length = '5m'
    print_balances()
    while True:
        df = fetch_data(symbol, candle_length)
        df = calculate_rsi(df)
        df = calculate_ema(df, 3)  # Ensure EMA_3 is calculated for the buy condition
        check_and_execute_buy_order_rsi_ema(symbol, df)
        check_and_execute_sell_order_rsi_ema_2(symbol, df, amount=0.1)  # Updated to use EMA_2 for selling
        logging.info("Sleeping for 60 seconds before the next iteration.")
        time.sleep(60)

if __name__ == "__main__":
    main()
