# kraken-kirby

A Python trading bot for the Kraken cryptocurrency exchange, designed for automated limit order placement with advanced configuration options. This script supports both "main wall" and "flood spam" trading strategies, allowing for flexible buying and selling with robust error handling and logging.

## Features
- Places limit buy and sell orders on Kraken
- Supports two strategies: main walls and flood spam
- Configurable via script variables
- Handles Kraken API errors and rate limits
- Reads API credentials from a `.env` file
- Prints detailed debug information if enabled
- Enforces minimum order sizes and increments
- Clean exit and error prompts for user intervention

## Requirements
- Python 3.12.4 (tested and confirmed)
- [krakenex](https://github.com/veox/python3-krakenex)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

Install dependencies:
```bash
pip install krakenex python-dotenv
```

## Setup
1. Clone this repository or copy the script to your local machine.
2. Create a `.env` file in the same directory with your Kraken API credentials:
    ```env
    KRAKEN_API_KEY=your_api_key_here
    KRAKEN_API_SECRET=your_api_secret_here
    ```
3. Edit the configuration section at the top of `kraken-kirby.py` to set your trading preferences:
    - Trading pair (e.g., `OMUSD`)
    - Order sizes, prices, and strategy flags
    - Debug and error handling options

## Usage
Run the script from the terminal:
```bash
python kraken-kirby.py
```

The script will:
- Connect to Kraken using your API key/secret
- Validate and quantize your order amounts and prices
- Place buy/sell limit orders according to your configuration
- Handle errors and print status updates

## Configuration Options
Edit these variables at the top of the script:
- `enable_buying`, `enable_selling`: Enable/disable buying/selling
- `use_main_walls`, `use_flood_spam`: Select trading strategies
- `product_id`: Kraken trading pair (e.g., `OMUSD`)
- `main_buy_price`, `main_sell_price`, `flood_base_amount`, `main_base_amount`: Prices and order sizes
- `debug`: Enable verbose output
- Error handling flags: `show_insufficient_funds`, `stop_on_insufficient_funds`, `stop_on_base_amount_error`

## Disclaimer
This script is for educational and personal use only. Use at your own risk. Trading cryptocurrencies involves significant risk of loss. Always test with small amounts and review the code before running with real funds.
