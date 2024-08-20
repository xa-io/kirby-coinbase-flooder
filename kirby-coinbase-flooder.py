#####################################################################################
# 
# Kirby Christmas Lights Buy/Sell Limit Order Flooder for Coinbase Advanced
#
# Just a fun project I decided to create out of boredom.
# Why use limit orders instead of market orders?
# Because market orders aren't always available.
#
# Enjoy!
#
# Other revisions coming soon once stable.
#
# Installation Instructions:
# 
# Install the required packages:
#     pip install python-dotenv coinbase
#
# Environment Variables: Load your Coinbase API key and secret from the .env file.
# Uses Legacy keys - https://www.coinbase.com/settings/legacy_api
#     Placeholders for the .env file
#        COINBASE_API_KEY=organizations/xxxxxxxxxxxxxxxxxx/apiKeys/xxxxxxxxxxxxxxxxxx
#        COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\nxxxxxxxxxxxxxxxxxx\nxxxxxxxxxxxxxxxxxx\nxxxxxxxxxxxxxxxxxx\n-----END EC PRIVATE KEY-----\n
#
# trading_pairs: List of dictionaries containing trading pairs and their parameters.
# Each dictionary should have specific values based on price: "product_id", "buy_price", "sell_price", "base_size".
# sleep_duration: Delay between orders (in seconds).
#
# Updates
#  - v0.03 -
#   - Converted buy/sell prices into strings to float in strategies
#   - Created normal and waves strategies
#   - Consolidated strategy parameters into individual variables
#   - Improved error handling
#   - Removed redundant code
#
#  - v0.02 -
#   - Improved order ID generation to ensure no orders are failing
#   - Refactored error handling to include restriction and maintenance
#####################################################################################

import uuid
import time
import os
from datetime import datetime
import sys
import logging
from json import dumps
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from decimal import Decimal, getcontext, ROUND_DOWN

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("COINBASE_API_KEY")
api_secret = os.getenv("COINBASE_API_SECRET")

client = RESTClient(api_key=api_key, api_secret=api_secret)

#######################################
#### ONLY CHANGE THINGS UNDER THIS ####
#######################################

# Configuration parameters
sleep_duration = 1
rate_limit_delay = 1
debug = False
stop_on_insufficient_funds = True

# Trading rules
enable_buying = True
enable_selling = True

# Strategy configuration
product_id = "BTC-USD"
buy_price = 80000
sell_price = 50000
base_amount = 0.00000001
enable_waves = True
enable_normal = False

#######################################
#### ONLY CHANGE THINGS ABOVE THIS ####
#######################################

# Set the precision for decimal operations
getcontext().prec = 16  # Increase precision to avoid rounding issues

def format_decimal(number, decimal_places):
    """Formats a number using Decimal's capabilities to avoid scientific notation and limit decimal places."""
    decimal_number = Decimal(number).quantize(Decimal(10) ** -decimal_places, rounding=ROUND_DOWN)
    return format(decimal_number, 'f').rstrip('0').rstrip('.') if '.' in format(decimal_number, 'f') else format(decimal_number, 'f')

# Determine the appropriate number of decimal places for the given pair
price_decimal_places = 8  # Assuming a default of 8 decimal places for price

# Determine the appropriate number of decimal places for base size (common for BTC-USD)
base_size_decimal_places = 8

# Convert configuration values to Decimal for calculations
buy_price_str = format_decimal(buy_price, price_decimal_places)
sell_price_str = format_decimal(sell_price, price_decimal_places)
base_amount_str = format_decimal(base_amount, base_size_decimal_places)

# Ensure the limit prices are not zero after formatting
if Decimal(buy_price_str) == 0 or Decimal(sell_price_str) == 0:
    raise ValueError("One of the limit prices is zero after formatting. Please check the buy and sell prices.")

# Calculate wave sizes based on the base amount and round to the correct decimal places
wave_sizes = [Decimal(base_amount).quantize(Decimal(10) ** -base_size_decimal_places) * Decimal(x) for x in [1, 3, 5, 7, 5, 3]]

# Trading pairs configuration
trading_pairs = []

if enable_waves:
    trading_pairs.extend([
        {
            "product_id": product_id,
            "buy_price": buy_price_str,
            "sell_price": sell_price_str,
            "base_size": format_decimal(size, base_size_decimal_places)
        }
        for size in wave_sizes
    ])

if enable_normal:
    normal_strategy_pair = {
        "product_id": product_id,
        "buy_price": buy_price_str,
        "sell_price": sell_price_str,
        "base_size": base_amount_str  # Use base_amount_str directly as a string
    }
    trading_pairs.append(normal_strategy_pair)

# Debugging information
if debug:
    print(f"buy_price_str: {buy_price_str}")
    print(f"sell_price_str: {sell_price_str}")
    print(f"base_amount_str: {base_amount_str}")
    print(f"wave_sizes: {[format_decimal(size, base_size_decimal_places) for size in wave_sizes]}")
    print(f"trading_pairs: {dumps(trading_pairs, indent=2)}")

# Generate a unique client order ID.
def get_unique_client_order_id():
    return str(uuid.uuid4())

# Return the current timestamp.
def get_timestamp():
    return datetime.now().strftime('%m-%d-%y %H:%M:%S.%f')[:-3]

# Handle errors from order responses.
def handle_order_error(order_response, order_type):
    if not order_response["success"] and "error_response" in order_response:
        error_message = order_response["error_response"]["message"]
        if debug:
            print(f"{order_type} order error:", error_message)
        if "Insufficient balance in source account" in error_message:
            print("Insufficient balance detected.")
            if stop_on_insufficient_funds:
                print("Stopping the script due to insufficient funds.")
                sys.exit()  # Stop the script

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
        sys.exit()  # Stop the script
    elif "HTTP Error: 403" in error_message:
        print("Forbidden: Re-KYC might be required.")
        sys.exit()  # Stop the script
    elif "HTTP Error: 500" in error_message or "HTTP Error: 502" in error_message or "HTTP Error: 503" in error_message:
        print("Server error at Coinbase.")
        sys.exit()  # Stop the script

# Place a limit order.
def place_limit_order(order_type, product_id, base_size, price):
    client_order_id = get_unique_client_order_id()
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

# Main function to run the script.
def main():
    global order_count
    order_count = 0

    suppress_coinbase_logs()  # Suppress Coinbase logs

    if not enable_buying and not enable_selling:
        print("You need to enable buying or selling to start. Stopping the script.")
        sys.exit()

    try:
        while True:
            try:
                for pair in trading_pairs:
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
                            print("{} - {} - {} - Buy".format(get_timestamp(), product_id, order_count))

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
                            print("{} - {} - {} - Sell".format(get_timestamp(), product_id, order_count))

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

if __name__ == "__main__":
    main()
