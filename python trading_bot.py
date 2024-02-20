import os
import ccxt
import math
import time
import pandas as pd
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
api_key = os.getenv('BINANCE_API_KEY')
secret_key = os.getenv('BINANCE_API_SECRET')

exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': secret_key,
    'enableRateLimit': True,
})

def adjust_amount(symbol, amount):
    market = exchange.market(symbol)
    amount_precision = market['precision']['amount']
    adjusted_amount = round(amount, amount_precision)
    return max(adjusted_amount, market['limits']['amount']['min'])

def adjust_price(symbol, price):
    market = exchange.market(symbol)
    price_precision = market['precision']['price']
    return round(price, price_precision)

def fetch_data(symbol, timeframe='5m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    logger.debug(f"Fetched data for {symbol}: {df.head()}")
    return df

def calculate_rsi(df, symbol, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi.rolling(window=14).mean()
    logger.debug(f"Calculated RSI for {symbol}")
    return df

def calculate_ema(df, symbol, period=3):
    df['ema'] = df['close'].ewm(span=period, adjust=False).mean()
    logger.debug(f"Calculated EMA for {symbol}")
    return df

def ensure_notional_value(symbol, amount, price):
    market = exchange.market(symbol)
    min_notional = market['limits']['cost']['min']
    notional_value = amount * price
    if notional_value < min_notional:
        required_amount = min_notional / price
        return adjust_amount(symbol, required_amount)
    return amount

def check_buy_conditions(df, symbol):
    last_rsi = df.iloc[-1]['rsi']
    if last_rsi > 62.8:
        balance = exchange.fetch_balance()
        usdt_balance = balance['free']['USDT'] * 0.98
        last_ema = df.iloc[-1]['ema']
        price = adjust_price(symbol, last_ema)
        amount = usdt_balance / price
        adjusted_amount = adjust_amount(symbol, amount)
        adjusted_amount = ensure_notional_value(symbol, adjusted_amount, price)
        logger.debug(f"Buy conditions met for {symbol}, placing order")
        return exchange.create_limit_buy_order(symbol, adjusted_amount, price)

def check_sell_conditions(df, symbol, amount):
    last_rsi = df.iloc[-1]['rsi']
    if last_rsi >= 69.33 or last_rsi <= 62.8:
        last_ema = df.iloc[-1]['ema']
        price = adjust_price(symbol, last_ema)
        adjusted_amount = adjust_amount(symbol, amount)
        adjusted_amount = ensure_notional_value(symbol, adjusted_amount, price)
        logger.debug(f"Sell conditions met for {symbol}, placing order")
        return exchange.create_limit_sell_order(symbol, adjusted_amount, price)

def main():
    symbol = 'XRP/USDT'
    while True:
        df = fetch_data(symbol)
        df = calculate_rsi(df, symbol)
        df = calculate_ema(df, symbol)
        buy_order = check_buy_conditions(df, symbol)
        if buy_order:
            logger.info(f"Buy Order: {buy_order}")
            amount = buy_order['filled']
            sell_order = check_sell_conditions(df, symbol, amount)
            if sell_order:
                logger.info(f"Sell Order: {sell_order}")
        time.sleep(60)

if __name__ == "__main__":
    main()
