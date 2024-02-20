
# Cryptocurrency Trading Bot

This trading bot is designed to automate cryptocurrency trading on the Binance exchange. It utilizes technical indicators like Relative Strength Index (RSI) and Exponential Moving Average (EMA) to make trading decisions. The bot fetches real-time market data, calculates indicators, and executes buy or sell orders based on predefined conditions.

## Requirements

- Python 3.x
- Pip (Python package installer)
- API Key and Secret from Binance

## Installation

1. Clone this repository or download the code to your local machine.
2. Install the required Python packages:

```bash
pip install ccxt pandas numpy
```

3. Set your Binance API Key and Secret as environment variables:

```bash
export BINANCE_API_KEY='your_api_key_here'
export BINANCE_API_SECRET='your_api_secret_here'
```

## Configuration

Before running the bot, ensure that your API key and secret are set correctly as environment variables. The bot uses these credentials to interact with the Binance API.

## Usage

To start the trading bot, run the following command in your terminal:

```bash
python trading_bot.py
```

## How It Works

### Data Fetching

The bot fetches historical candlestick data for a specified cryptocurrency pair using the `fetch_data` function. This data includes open, high, low, close prices, and volume for each candlestick.

### Indicator Calculation

- **RSI Calculation**: The `calculate_rsi` function computes the Relative Strength Index (RSI), a momentum indicator measuring the magnitude of recent price changes to evaluate overbought or oversold conditions.
- **EMA Calculation**: The `calculate_ema` function calculates the Exponential Moving Average (EMA), which is a type of moving average that places a greater weight and significance on the most recent data points.

### Buy and Sell Logic

- **Buy Orders**: The bot places a buy order when the RSI is above a threshold (62.8 in this case) and the last closing price is above the 3-period EMA. This is intended to identify upward momentum and ensure the price is above a short-term average.
- **Sell Orders**: Sell orders are executed when the RSI falls below the buy threshold (62.8) or exceeds a higher threshold (69.33), indicating potential overbought conditions.

### Order Execution

The `check_and_execute_buy_order_rsi_ema` and `check_and_execute_sell_order_rsi` functions are responsible for executing buy and sell orders, respectively. They use the calculated indicators to evaluate conditions and place orders through the Binance API.

### Error Handling and Retries

The `retry` decorator is applied to key functions to handle potential network or API errors by retrying the operation. It implements exponential backoff to avoid overwhelming the server.

## Important Notes

- This bot is for educational purposes only. Use it at your own risk. Trading cryptocurrencies can be risky, and there's no guarantee of profit.
- The parameters used for RSI and EMA calculations, as well as the buy/sell thresholds, are just examples. Adjust them according to your trading strategy.
- Ensure you are compliant with Binance's API usage policies.

## License

This project is open-sourced under the MIT License.
