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

def calculate_rsi(df, period=14):
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Period must be an integer greater than 0")
    delta = df['close'].diff(1)
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    df['rsi'] = rsi
    return df

def calculate_ema(df, period=3):
    if not isinstance(period, int) or period <= 0:
        raise ValueError("Period must be an integer greater than 0")
    df['ema'] = df['close'].ewm(span=period, adjust=False).mean()
    logger.debug(f"Calculated EMA")
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
    # Define RSI range
    rsi_lower_bound = 62
    rsi_upper_bound = 69

    # Get the last two RSI values to check for crossover
    last_rsi = df.iloc[-2:]['rsi'].values

    # Check for upward crossover into the range
    if last_rsi[0] < rsi_lower_bound and rsi_lower_bound <= last_rsi[1] <= rsi_upper_bound:
        try:
            balance = exchange.fetch_balance()
            usdt_balance = balance['free']['USDT'] * 0.98
            last_price = df.iloc[-1]['close']
            price = adjust_price(symbol, last_price)
            amount = usdt_balance / price
            adjusted_amount = adjust_amount(symbol, amount)
            adjusted_amount = ensure_notional_value(symbol, adjusted_amount, price)
            logger.debug(f"Buy signal detected for {symbol}, placing order")
            return exchange.create_limit_buy_order(symbol, adjusted_amount, price)
        except ccxt.InsufficientFunds as e:
            logger.warning(f"Insufficient funds for buying {symbol}: {str(e)}")
            return None

def check_sell_conditions(df, symbol, amount):
    # Define RSI range
    rsi_lower_bound = 62
    rsi_upper_bound = 69

    # Check if the RSI is outside the range
    last_rsi = df.iloc[-1]['rsi']
    if last_rsi < rsi_lower_bound or last_rsi > rsi_upper_bound:
        try:
            last_price = df.iloc[-1]['close']
            price = adjust_price(symbol, last_price)
            adjusted_amount = adjust_amount(symbol, amount)
            adjusted_amount = ensure_notional_value(symbol, adjusted_amount, price)
            logger.debug(f"Sell signal detected for {symbol}, placing order")
            return exchange.create_limit_sell_order(symbol, adjusted_amount, price)
        except ccxt.InsufficientFunds as e:
            logger.warning(f"Insufficient funds for selling {symbol}: {str(e)}")
            return None

def cancel_pending_buy_orders(symbol):
    # Fetch open orders for the symbol
    open_orders = exchange.fetch_open_orders(symbol)
    for order in open_orders:
        if order['side'] == 'buy':
            logger.debug(f"Cancelling pending buy order for {symbol}: {order['id']}")
            exchange.cancel_order(order['id'], symbol)

def main():
    symbol = 'BTC/USDT'
    while True:
        df = fetch_data(symbol)
        df = calculate_rsi(df)  # Corrected the call to calculate_rsi without the symbol argument
        df = calculate_ema(df)  # Removed the symbol argument
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
