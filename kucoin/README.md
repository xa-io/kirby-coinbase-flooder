# Kirby - KuCoin Trading Bot

A simple, configurable trading bot for the KuCoin cryptocurrency exchange that automates limit order placement.

## Features

- Automated buy and sell limit order placement
- Configurable trading parameters
- Support for wave-based trading strategy
- Error handling for common API issues
- Rate limit management
- Detailed logging

## Requirements

- Python 3.12.4
- KuCoin API credentials

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/xa-io/kirby-coinbase-flooder/new/main/kucoin
   ```

2. Install the required dependencies:
   ```
   pip install python-kucoin python-dotenv
   ```

3. Create a `.env` file in the project directory with your KuCoin API credentials:
   ```
   KUCOIN_API_KEY=your_api_key
   KUCOIN_API_SECRET=your_api_secret
   KUCOIN_API_PASSPHRASE=your_api_passphrase
   ```

## Configuration

Edit the configuration parameters in `kirby.py` to customize your trading strategy:

### Basic Configuration
```python
# Configuration parameters
sleep_duration = 0.01  # Time between operations
rate_limit_delay = 1   # Delay when rate limit is hit
debug = False          # Enable for detailed logging
stop_on_insufficient_funds = False  # Stop script if funds are insufficient
```

### Trading Rules
```python
# Trading rules
force_base_amount = True  # Use specified amount instead of minimum
enable_waves = False      # Enable wave-based trading
enable_normal = True      # Enable normal trading
enable_buying = True      # Enable buy orders
enable_selling = False    # Enable sell orders
```

### Trading Pair Configuration
```python
product_id = "ZEN-USDT"  # Trading pair
sell_price = 26.129      # Sell price
buy_price = 28.936       # Buy price
specified_base_amount = 0.01  # Amount to trade
```

### Decimal Precision
```python
price_decimal_places = 3  # Decimal places for price
size_decimal_places = 2   # Decimal places for size
size_increment = Decimal('0.1')  # Minimum size increment
```

## Usage

Run the bot:

```
python kirby.py
```

To stop the bot, press `Ctrl+C` in the terminal.

## Trading Strategies

### Normal Trading
Places individual buy and/or sell orders at the specified prices.

### Wave Trading
Places multiple orders with varying sizes based on a wave pattern. Enable this by setting `enable_waves = True`.

## Safety Features

- Error handling for common API issues
- Rate limit management
- Option to stop on insufficient funds
- Validation of price and size parameters

## Disclaimer

This bot is provided for educational purposes only and has not been updated more than twice. Use at your own risk, and please report issues. 
