############################################################################################################################
# 
# Fuji's Kirby Christmas Lights Buy/Sell Limit Flooder For Coinbase Advanced
#
# This script floods the market with buy and sell limit orders, creating a vibrant trading pattern akin to the twinkling
# lights of a Christmas tree. Ensure that your buy and sell prices are within your primary order walls. The script uses
# limit orders to mimic market orders since market orders may not always be available in newer markets. Make sure your
# orders meet the minimum order size if using force_base_amount to avoid the script from stopping. If your buy or sell
# price is flooding and hits one of your walls, it will cancel your larger order.
# 
# Enjoy the light show and happy trading!
# 
# Important Note: Running this script carries the risk of your Coinbase account being flagged for suspicious activity,
# which may require you to re-complete KYC verification based on prior experience. Additionally, it is recommended to 
# set up a separate portfolio (a new feature on Coinbase) to avoid accidentally using large balances.
#
# There are two flooder types:
#  - Normal: Executes buy/sell orders with the specified base_amount.
#  - Waves: Executes buy/sell orders with a pattern: base_amount x1/x3/x5/x7/x5/x3, repeating continuously.
#      * You can use both flooders to have a normal rotation within the waves.
#
# Additional Features:
#  - force_base_amount: If set to True, the specified_base_amount will be used for orders instead of calculated amounts.
#  -  ^ use force_base_amount, if the script is failing to pull the base amount and not firing orders.
#  - specified_base_amount: The specific base amount to use for orders when force_base_amount is True.
#
# Example: With a base_amount of 1:
#  - Normal: Repeatedly executes orders with base_amount 1.
#  - Waves: Executes orders with amounts 1, 3, 5, 7, 5, 3, and repeats.
#
# Configuration Parameters:
# - sleep_duration: Delay between placing each order, measured in seconds. Default is 0.01 seconds.
# - rate_limit_delay: Wait time in seconds when a rate limit is exceeded. Default is 1 second.
# - debug: Toggle for debugging mode. If set to True, detailed debug information will be printed. Default is False.
# - stop_on_insufficient_funds: Stops the script if insufficient funds are detected. Default is True.
# - enable_buying: Enables or disables placing buy orders. Default is True.
# - enable_selling: Enables or disables placing sell orders. Default is True.
# - product_id: The ID of the trading pair to use. Default is "BTC-USD".
# - buy_price: The price at which to place buy orders. Default is 80000.
# - sell_price: The price at which to place sell orders. Default is 50000.
# - enable_waves: Enables the wave strategy, placing orders in a patterned sequence (e.g., 1x, 3x, 5x, 7x). Default is True.
# - enable_normal: Enables the normal strategy, placing orders with the specified base_amount repeatedly. Default is False.
# - specified_base_amount: The specific base amount to use for orders when force_base_amount is True. Default is 0.
# - force_base_amount: If set to True, the specified_base_amount will be used for orders instead of calculated amounts. Default is False.
# - enable_staggered: Enables the staggered strategy, placing orders with incremented prices. Default is False.
# - staggered_amount: The number of staggered orders to place. Default is 10.
# 
# How to install:
#     pip install python-dotenv coinbase coinbase-advanced-py
#
# Environment Variables: Load your Coinbase API key and secret from the .env file.
# Uses Legacy keys - https://www.coinbase.com/settings/legacy_api
#     Placeholders for the .env file
#        COINBASE_API_KEY=organizations/xxxxxxxxxxxxxxxxxx/apiKeys/xxxxxxxxxxxxxxxxxx
#        COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\nxxxxxxxxxxxxxxxxxx\nxxxxxxxxxxxxxxxxxx\nxxxxxxxxxxxxxxxxxx\n-----END EC PRIVATE KEY-----\n
#
# - Updates -
#
#  v0.06
#  - Added enable_staggered and staggered_amount settings.
#  - Implemented staggered orders with incremented prices.
#
#  v0.05
#  - Moved `enable_waves` and `enable_normal` to global settings.
#  - Added `enabled-true/false` flag for individual trading pair configurations.
#  - Added support for listing multiple coins for trading.
#
#  v0.04
# - Added force_base_amount configuration to optionally use a specified base amount for orders.
# - Introduced specified_base_amount parameter to define the base amount when force_base_amount is True.
# - Updated wave sizes calculation to respect the force_base_amount setting.
# - Enhanced descriptions for configuration parameters.
#
#  v0.03
# - Converted buy/sell prices to float in strategies.
# - Introduced normal and waves strategies.
# - Consolidated strategy parameters into individual variables.
# - Enhanced decimal handling for limit orders and base price.
# - Improved error handling.
# - Removed redundant code.
#
#  v0.02
# - Enhanced order ID generation to ensure no orders fail.
# - Refactored error handling to include restriction and maintenance.
#
############################################################################################################################

#######################################
#### ONLY CHANGE THINGS UNDER THIS ####
#######################################

# Global settings
sleep_duration = 0.25
rate_limit_delay = 10
debug = False
delay_on_insufficient_funds = 20
stop_on_insufficient_funds = True
show_insignificant_balance_message = True
show_insignificant_balance_delay_message = False

# Buying Selling
enable_buying = True
enable_selling = False

# Strategies
enable_waves = False
enable_normal = True

# Staggered
enable_staggered = False
staggered_amount = 10

# Configuration parameters for multiple trading pairs
# Adjust these parameters as needed
configurations = [
    {
        "product_id": "BTC-USD",
        "buy_price": "80000",
        "sell_price": "20000",
        "enabled": True,
        "force_base_amount": False,
        "specified_base_amount": 0.001
    }
]

#######################################
#### ONLY CHANGE THINGS ABOVE THIS ####
#######################################

import uuid
import time
import os
from datetime import datetime
import sys
import logging
from json import dumps
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from decimal import Decimal, getcontext, InvalidOperation, ROUND_DOWN

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("COINBASE_API_KEY")
api_secret = os.getenv("COINBASE_API_SECRET")

client = RESTClient(api_key=api_key, api_secret=api_secret)

# Set the precision for decimal operations
getcontext().prec = 16  # Increase precision to avoid rounding issues

def fetch_product_list(client):
    try:
        response = client.get_products()
        products = response.get('products')  # Adjust this based on the actual API response structure
        if isinstance(products, list):
            return products
        else:
            raise TypeError("API response does not contain a list of products.")
    except Exception as e:
        print(f"Error fetching product list: {e}")
        sys.exit(1)

def get_base_increment(product_list, product_id):
    for product in product_list:
        if product['product_id'] == product_id:
            return Decimal(product['base_increment'])
    raise ValueError(f"Product ID {product_id} not found in product list.")

# Updated get_decimal_places function to handle small decimal values
def get_decimal_places(value):
    value_str = str(value)
    if '.' in value_str:
        return len(value_str.split('.')[1])
    return 0

def format_decimal(number, decimal_places):
    try:
        if not isinstance(number, Decimal):
            number = Decimal(str(number))
        decimal_format = Decimal('1.' + '0' * decimal_places)
        decimal_number = number.quantize(decimal_format, rounding=ROUND_DOWN)
        return f"{decimal_number:.{decimal_places}f}"
    except InvalidOperation as e:
        print(f"Error formatting decimal: {e}")
        return None

# Fetch the product list from the API
product_list = fetch_product_list(client)

# Corrected approach for staggering buy and sell prices
def generate_trading_pairs(configurations, product_list):
    all_trading_pairs = []
    for config in configurations:
        if not config.get("enabled", True):
            continue
        
        product_id = config["product_id"]
        try:
            buy_price = Decimal(str(config["buy_price"]))
            sell_price = Decimal(str(config["sell_price"]))
            specified_base_amount = Decimal(str(config["specified_base_amount"]))
        except InvalidOperation as e:
            print(f"Error initializing decimals: {e}")
            continue

        force_base_amount = config.get("force_base_amount", False)

        # Determine the decimal precision for the current trading pair
        price_decimal_places = max(get_decimal_places(buy_price), get_decimal_places(sell_price))
        price_increment = Decimal('1e-' + str(price_decimal_places))

        trading_pairs = []

        # Initialize min and max prices
        min_buy_price = buy_price
        max_buy_price = buy_price - (staggered_amount - 1) * price_increment
        min_sell_price = sell_price
        max_sell_price = sell_price + (staggered_amount - 1) * price_increment

        # Handle wave sizes and staggered orders
        if enable_waves:
            if force_base_amount:
                wave_sizes = [
                    specified_base_amount * Decimal(1),
                    specified_base_amount * Decimal(3),
                    specified_base_amount * Decimal(5),
                    specified_base_amount * Decimal(7),
                    specified_base_amount * Decimal(5),
                    specified_base_amount * Decimal(3)
                ]
            else:
                base_increment = get_base_increment(product_list, product_id)
                wave_sizes = [
                    base_increment * Decimal(1),
                    base_increment * Decimal(3),
                    base_increment * Decimal(5),
                    base_increment * Decimal(7),
                    base_increment * Decimal(5),
                    base_increment * Decimal(3)
                ]

            if enable_staggered:
                for i in range(staggered_amount):
                    staggered_buy_price = buy_price - i * price_increment
                    staggered_sell_price = sell_price + i * price_increment

                    # Avoid negative prices
                    if staggered_buy_price < 0:
                        staggered_buy_price = Decimal('0.00')

                    # Cycle through wave sizes for staggered orders
                    wave_size = wave_sizes[i % len(wave_sizes)]
                    
                    staggered_pair = {
                        "product_id": product_id,
                        "buy_price": format_decimal(staggered_buy_price, price_decimal_places),
                        "sell_price": format_decimal(staggered_sell_price, price_decimal_places),
                        "base_size": format_decimal(wave_size, get_decimal_places(wave_size)),
                        "price_range": {"buy_range": (format_decimal(min_buy_price, price_decimal_places), format_decimal(max_buy_price, price_decimal_places)),
                                        "sell_range": (format_decimal(min_sell_price, price_decimal_places), format_decimal(max_sell_price, price_decimal_places))}
                    }
                    trading_pairs.append(staggered_pair)
            else:
                for wave_size in wave_sizes:
                    wave_pair = {
                        "product_id": product_id,
                        "buy_price": format_decimal(buy_price, price_decimal_places),
                        "sell_price": format_decimal(sell_price, price_decimal_places),
                        "base_size": format_decimal(wave_size, get_decimal_places(wave_size)),
                        "price_range": {"buy_range": (format_decimal(min_buy_price, price_decimal_places), format_decimal(max_buy_price, price_decimal_places)),
                                        "sell_range": (format_decimal(min_sell_price, price_decimal_places), format_decimal(max_sell_price, price_decimal_places))}
                    }
                    trading_pairs.append(wave_pair)
        elif enable_normal:
            base_size = specified_base_amount if force_base_amount else get_base_increment(product_list, product_id)
            if enable_staggered:
                for i in range(staggered_amount):
                    staggered_buy_price = buy_price - i * price_increment
                    staggered_sell_price = sell_price + i * price_increment

                    # Avoid negative prices
                    if staggered_buy_price < 0:
                        staggered_buy_price = Decimal('0.00')

                    staggered_pair = {
                        "product_id": product_id,
                        "buy_price": format_decimal(staggered_buy_price, price_decimal_places),
                        "sell_price": format_decimal(staggered_sell_price, price_decimal_places),
                        "base_size": format_decimal(base_size, get_decimal_places(base_size)),
                        "price_range": {"buy_range": (format_decimal(min_buy_price, price_decimal_places), format_decimal(max_buy_price, price_decimal_places)),
                                        "sell_range": (format_decimal(min_sell_price, price_decimal_places), format_decimal(max_sell_price, price_decimal_places))}
                    }
                    trading_pairs.append(staggered_pair)
            else:
                normal_strategy_pair = {
                    "product_id": product_id,
                    "buy_price": format_decimal(buy_price, price_decimal_places),
                    "sell_price": format_decimal(sell_price, price_decimal_places),
                    "base_size": format_decimal(base_size, get_decimal_places(base_size)),
                    "price_range": {"buy_range": (format_decimal(min_buy_price, price_decimal_places), format_decimal(max_buy_price, price_decimal_places)),
                                    "sell_range": (format_decimal(min_sell_price, price_decimal_places), format_decimal(max_sell_price, price_decimal_places))}
                }
                trading_pairs.append(normal_strategy_pair)

        all_trading_pairs.extend(trading_pairs)
    return all_trading_pairs

# Generate all trading pairs
all_trading_pairs = generate_trading_pairs(configurations, product_list)

# Debugging information
if debug:
    debug_pairs = [{k: str(v) if isinstance(v, Decimal) else v for k, v in pair.items()} for pair in all_trading_pairs]
    print(f"all_trading_pairs: {dumps(debug_pairs, indent=2)}")


# Generate a unique client order ID.
def get_unique_client_order_id():
    return str(uuid.uuid4())

# Return the current timestamp.
def get_timestamp():
    return datetime.now().strftime('%m-%d-%y %H:%M:%S.%f')[:-3]

def format_trade_message(product_id, order_count, action, price, staggered, price_range=None, buy_price=None):
    # Set fixed widths for alignment
    price_width = 7
    percentage_width = 8
    action_width = 6

    message = f"{get_timestamp()}  |  {product_id}  |  #{order_count:<3}  |  {action.capitalize():<{action_width}}  |  {price:<{price_width}}"

    if staggered and price_range:
        if action.lower() == "buy":
            lowest_price = Decimal(price_range['buy_range'][1])
            highest_price = Decimal(price_range['buy_range'][0])
            spread_percentage = ((highest_price - lowest_price) / lowest_price) * 100
            spaces_needed = 9  # Aligns with typical Sell percentage
            message += f"  | {' ' * spaces_needed}[Spread: {spread_percentage:.2f}%]  |  (Range: {lowest_price} - {highest_price})"
        elif action.lower() == "sell":
            lowest_price = Decimal(price_range['sell_range'][0])
            highest_price = Decimal(price_range['sell_range'][1])
            spread_percentage = ((highest_price - lowest_price) / lowest_price) * 100
            if buy_price is not None:
                sell_price = Decimal(price)
                buy_price = Decimal(buy_price)
                percentage_diff = f"+{((sell_price - buy_price) / buy_price * 100):.2f}%"
                message += f"  |  {percentage_diff:<{percentage_width}}[Spread: {spread_percentage:.2f}%]  |  (Range: {lowest_price} - {highest_price})"
            else:
                message += f"  [Spread: {spread_percentage:.2f}%]  |  (Range: {lowest_price} - {highest_price})"
    else:
        if action.lower() == "sell" and buy_price is not None:
            sell_price = Decimal(price)
            buy_price = Decimal(buy_price)
            percentage_diff = f"+{((sell_price - buy_price) / buy_price) * 100:.2f}%"
            message += f"  |  {percentage_diff:<{percentage_width}}"
        elif action.lower() == "buy" and not staggered:
            message += "  |"

    return message

# Define the wait_for_user function
def wait_for_user():
    input("Press Enter to exit...")  # Wait for user input before exiting

# Handle errors from order responses.
def handle_order_error(order_response, order_type):
    if not order_response["success"] and "error_response" in order_response:
        error_message = order_response["error_response"]["message"]
        error_preview_failure_reason = order_response["error_response"].get("preview_failure_reason", "")
        if debug:
            print(f"{order_type} order error:", error_message)
        if "PREVIEW_INVALID_BASE_SIZE_TOO_SMALL" in error_preview_failure_reason:
            print("Error: The base size is too small. Please check the minimum base size and adjust your configuration.")
            wait_for_user()  # Call the function
            sys.exit()  # Stop the script
        if "Insufficient balance in source account" in error_message:
            if show_insignificant_balance_message:
                print("Insufficient balance detected.")
            if stop_on_insufficient_funds:
                print("Stopping the script due to insufficient funds.")
                wait_for_user()  # Call the function
                sys.exit()  # Stop the script
            else:
                if show_insignificant_balance_delay_message:
                    print(f"Insufficient funds, delaying for {delay_on_insufficient_funds} seconds...")
                time.sleep(delay_on_insufficient_funds)

# Handle specific errors based on error messages.
def handle_specific_errors(error_message):
    if "Rate limit exceeded" in error_message:
        print("Rate limit exceeded. Waiting for", rate_limit_delay, "seconds.")
        time.sleep(rate_limit_delay)
    elif "HTTP Error: 400" in error_message:
        print("Bad Request: The request was too complex for Coinbase to handle. Waiting for", rate_limit_delay, "seconds.")
        time.sleep(rate_limit_delay)
    elif "HTTP Error: 401" in error_message:
        print("Unauthorized: Check your API keys.")
        wait_for_user()  # Call the function
        sys.exit()  # Stop the script
    elif "HTTP Error: 403" in error_message:
        print("Forbidden: Re-KYC might be required.")
        wait_for_user()  # Call the function
        sys.exit()  # Stop the script
    elif "HTTP Error: 500" in error_message or "HTTP Error: 502" in error_message or "HTTP Error: 503" in error_message:
        print("Server error at Coinbase. Waiting before retrying.")
        time.sleep(rate_limit_delay)

# Place a limit order.
def place_limit_order(order_type, product_id, base_size, price):
    client_order_id = get_unique_client_order_id()
    if debug:
        print(f"Placing {order_type} order for {product_id} with base size {base_size} and price {price}")
    if order_type == "buy":
        return client.limit_order_gtc_buy(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size,
            limit_price=price
        )
    elif order_type == "sell":
        return client.limit_order_gtc_sell(
            client_order_id=client_order_id,
            product_id=product_id,
            base_size=base_size,
            limit_price=price
        )
    else:
        raise ValueError("Invalid order type. Use 'buy' or 'sell'.")

# Suppress Coinbase REST client logs.
def suppress_coinbase_logs():
    logger = logging.getLogger("coinbase.RESTClient")
    logger.setLevel(logging.CRITICAL)  # Suppress messages below CRITICAL level
    handler = logging.NullHandler()
    logger.addHandler(handler)

def main():
    global order_count
    order_count = 0

    suppress_coinbase_logs()  # Suppress Coinbase logs

    if not enable_buying and not enable_selling:
        print("You need to enable buying or selling to start. Stopping the script.")
        wait_for_user()  # Call the function
        sys.exit()

    try:
        while True:
            try:
                for pair in all_trading_pairs:
                    product_id = pair["product_id"]
                    buy_price = pair["buy_price"]
                    sell_price = pair["sell_price"]
                    base_size = pair["base_size"]

                    if enable_buying:
                        # Place buy limit order
                        buy_order = place_limit_order("buy", product_id, base_size, buy_price)
                        if debug:
                            print("Buy Order Response:", dumps(buy_order, indent=2))
                        handle_order_error(buy_order, "Buy")

                        if not debug:
                            order_count += 1
                            print(format_trade_message(product_id, order_count, "buy", buy_price, enable_staggered, pair.get("price_range")))

                    # Short wait before placing the sell order
                    time.sleep(sleep_duration)

                    if enable_selling:
                        # Place sell limit order
                        sell_order = place_limit_order("sell", product_id, base_size, sell_price)
                        if debug:
                            print("Sell Order Response:", dumps(sell_order, indent=2))
                        handle_order_error(sell_order, "Sell")

                        if not debug:
                            order_count += 1
                            print(format_trade_message(product_id, order_count, "sell", sell_price, enable_staggered, pair.get("price_range"), buy_price))

                    # Short wait to avoid flooding requests
                    time.sleep(sleep_duration)

            except Exception as e:
                error_message = str(e)
                if any(code in error_message for code in ["429", "403", "400", "401", "500", "502", "503"]):
                    handle_specific_errors(error_message)
                else:
                    print("Order error:", error_message)

    except KeyboardInterrupt:
        print("Script stopped by user.")
    except Exception as e:
        print("An error occurred:", str(e))
        wait_for_user()  # Call the function

if __name__ == "__main__":
    main()
