# Kirby Coinbase Flooder v1.00

This script combines orderbook scanning and limit order flooding functionality to help increase trading activity in crypto markets on Coinbase.

## Features

- **Real-time Orderbook Monitoring**: Scans the Coinbase orderbook for a selected trading pair
- **Spread Gap Detection**: Identifies price gaps between current bid and ask prices
- **Automatic Spread Filling**: Places limit orders to fill any detected spread gaps
- **Continuous Flood Orders**: Maintains order flow at key price levels
- **Dynamic Base Increment Handling**: Automatically fetches and uses correct base_increment values from Coinbase API
- **Products.json Caching**: Caches product information locally with automatic refreshing
- **Configurable Trading Parameters**: Easily customize trading pair, prices, order sizes, and more
- **Enhanced Error Handling**: Comprehensive error handling for API limits, insufficient funds, and base amount validation

## How It Works

1. The script monitors the current orderbook for your selected trading pair
2. When it detects a spread (gap) between bid and ask prices that's larger than one tick:
   - It calculates all the price points between bid and ask
   - Places orders at each price level to fill the gap
3. It also places optional "main wall" orders at defined boundaries
4. It continues with "flood spam" orders to maintain market activity

## Requirements

- Tested on Python 3.12.4
- Coinbase Advanced API credentials
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```
git clone https://github.com/xa-io/kirby-coinbase-flooder/tree/main/Coinbase
cd kirby-coinbase-flooder
```

2. Install required packages:
```
pip install -r requirements.txt
```

3. Set up your Coinbase API keys:
   - Create a .env file in the project directory
   - Add your API credentials in the following format:
```
COINBASE_API_KEY=organizations/xxxxxxxxxxxxxx/apiKeys/xxxxxxxxxxxxxx
COINBASE_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Configuration

Edit the configuration variables at the top of `Kirby Coinbase Flooder v1.00.py` to customize:

```python
# Orderbook scanner settings
SCAN_INTERVAL = 3                       # Seconds to wait between scans
SPREAD_ORDER_DELAY = 0.2                # Delay between each spread order placement
MAX_SPREAD_ORDERS = 3                   # Maximum number of orders to place when filling a spread
FILL_SPREAD = True                      # If True, performs spread-filling
FILL_BUYSELL_DISABLE = True             # Disables spread filling when both buying and selling are enabled
SHOW_TIMESTAMP = True                   # If True, timestamps will be displayed in logs

# Order flooding settings
PAIR = "BTC-USD"                        # Trading pair to monitor and trade
ENABLE_BUYING = True                    # Enables or disables placing buy orders
ENABLE_SELLING = False                  # Enables or disables placing sell orders
USE_MAIN_WALLS = False                  # If True, places large orders at main prices
USE_FLOOD_SPAM = True                   # If True, places smaller "flood" orders
MAIN_SELL_PRICE = 125000.00             # Large sell wall price will flood up to one tick below this price
MAIN_BUY_PRICE = 105000.00              # Large buy wall price will flood down to one tick above this price

# Flood settings
FORCE_FLOOD_BASE_INCREMENT = True       # If True, uses product's base_increment from API
FLOOD_BASE_AMOUNT = 0.0000001           # The smaller order size used in Flood Spam
MAIN_BASE_AMOUNT = 0.0001               # The large order size used in Main Walls

# System settings
SLEEP_DURATION = 0.2                    # Delay between placing each order
RATE_LIMIT_DELAY = 1                    # Wait time if rate limit is exceeded
DEBUG = False                           # Toggle debug mode
SHOW_HTTP_ERRORS = False                # Show HTTP error logs from Coinbase API
SHOW_INSUFFICIENT_FUNDS = True          # Show insufficient funds errors
STOP_ON_INSUFFICIENT_FUNDS = True       # Stop script on insufficient funds errors
STOP_ON_BASE_AMOUNT_ERROR = True        # Stop script on base amount errors

# Products file configuration
PRODUCTS_FILE = "products.json"         # File to store product information
PRODUCTS_MAX_AGE_HOURS = 72             # Maximum age of products file before refresh
```

## Usage

Run the script:

```
python Kirby Coinbase Flooder v1.00.py
```

Press Ctrl+C at any time to stop the script.

## Key Features Explained

### Dynamic Base Increment Handling

The script now automatically fetches and uses the correct `base_increment` values for any trading pair:

- **FORCE_FLOOD_BASE_INCREMENT = True**: Uses the product's actual base_increment from Coinbase API
- **FORCE_FLOOD_BASE_INCREMENT = False**: Uses your configured FLOOD_BASE_AMOUNT (with validation)
- **Automatic Validation**: Ensures your FLOOD_BASE_AMOUNT meets minimum requirements
- **Products.json Caching**: Stores product data locally and refreshes every 72 hours
- **Auto-refresh**: Updates product data when trading pairs are missing

### Error Handling

- **STOP_ON_BASE_AMOUNT_ERROR**: Controls whether script stops on base amount validation errors
- **STOP_ON_INSUFFICIENT_FUNDS**: Controls whether script stops on insufficient balance
- **Comprehensive API Error Handling**: Handles rate limits, authentication, and server errors
- **Fallback Mechanisms**: Graceful degradation when API calls fail

## Important Notes

- **Trading Risk**: Running this script will place real orders using your Coinbase account. Make sure you understand the financial implications.
- **API Limitations**: Coinbase may have rate limits that could affect the script's performance.
- **Account Security**: This script requires API keys with trading permissions. Keep your API credentials secure.
- **Account Flagging**: Rapidly placing and canceling orders may lead to your account being flagged for suspicious activity.
- **File Permissions**: The script creates a `products.json` file in the same directory for caching product data.

## Script Files

- `Kirby Coinbase Flooder v1.00.py`: The main script combining orderbook scanning and spread filling
- `products.json`: Auto-generated cache file containing Coinbase product information (created on first run)
- `.env`: Environment file containing your Coinbase API credentials (you must create this)
- `requirements.txt`: Python package dependencies

## Generated Files

The script will automatically create:
- `products.json`: Contains cached product information from Coinbase API
- This file is refreshed automatically every 72 hours or when missing trading pairs are detected

## Disclaimer

This script is provided for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses or account restrictions that may result from using this script.

## Consider a donation after you buy your lambo.

BTC: `bc1qwjy0hl4z9c930kgy4nud2fp0nw8m6hzknvumgg`

ETH: `0x0941D41Cd0Ee81bd79Dbe34840bB5999C124D3F0`

SOL: `4cpdbmmp1hyTAstA3iUYdFbqeNBwjFmhQLfL5bMgf77z`
