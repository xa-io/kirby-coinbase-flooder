############################################################################################################################
# 
# Kirby Christmas Lights Buy/Sell Limit Flooder For Coinbase Advanced
#
# This script floods the market with buy and sell limit orders, creating a vibrant trading pattern akin to
# the twinkling lights of a Christmas tree. It uses limit orders to mimic market orders, since market orders
# may not be available in all markets. Ensure that your buy and sell prices are within your intended ranges
# and that your base amounts meet the minimum order size requirements on Coinbase.
#
# Important Note: Running this script carries the risk of your Coinbase account being flagged for suspicious
# activity, which may require you to re-complete KYC verification. It is recommended to set up a separate
# portfolio on Coinbase to avoid inadvertently using large balances.
#
# - Primary Features:
#    * Main Walls: Large buy/sell orders set at defined boundaries (e.g., main_buy_price, main_sell_price).
#    * Flood Spam: Rapid, smaller orders placed just inside your main walls (flood_base_amount).
#
# Configuration Parameters:
#  - sleep_duration: Delay between placing each order, in seconds. Default is 0.2.
#  - rate_limit_delay: Wait time in seconds if a rate limit is exceeded. Default is 0.
#  - debug: Toggle debug mode. If True, prints detailed debug info. Default is False.
#  - stop_on_insufficient_funds: If True, stops the script when insufficient funds are encountered.
#  - stop_on_base_amount_error: If True, stops the script when a base-size or increment error occurs.
#  - enable_buying: Enables or disables placing buy orders. Default is True.
#  - enable_selling: Enables or disables placing sell orders. Default is True.
#  - use_main_walls: If True, places large orders at main_buy_price and main_sell_price.
#  - use_flood_spam: If True, places smaller “flood” orders just inside your main walls.
#  - product_id: Trading pair to use (e.g., "BTC-USD").
#  - main_buy_price: Large buy wall price. Default is 50000 (in this example).
#  - main_sell_price: Large sell wall price. Default is 100000 (in this example).
#  - flood_base_amount: The smaller order size used in Flood Spam.
#  - main_base_amount: The large order size used in Main Walls.
#  - force_flood_base_increment: If True, the script overrides user-configured flood_base_amount with the product's base_increment.
#
# How to install:
#    pip install python-dotenv coinbase coinbase-advanced-py
#
# Environment Variables (Current Coinbase API keys):
#    COINBASE_API_KEY=organizations/xxxxxxxxxxxxxx/apiKeys/xxxxxxxxxxxxxx
#    COINBASE_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
#
# - Updates -
#   v0.07:
#     * Removed older 'Waves' and 'Normal' strategies in favor of Main Walls and Flood Spam.
#     * Transitioned to Coinbase’s current (non-legacy) API keys.
#     * Added optional toggles to stop the script on insufficient funds or base amount errors.
#     * Verified script compatibility with Python 3.12.
#     * Cleaned up code for simpler configuration and improved decimal handling.
#
#   v0.08:
#     * Added 'force_flood_base_increment' parameter to optionally override flood_base_amount with the
#       product's base_increment. This helps ensure flood orders meet Coinbase's minimum size requirements.
#
############################################################################################################################


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
rate_limit_delay = 0
debug = False
show_insufficient_funds = True
stop_on_insufficient_funds = False
stop_on_base_amount_error = True
force_flood_base_increment = True

# Trading parameters
sleep_duration = 0.2
enable_buying = True
enable_selling = True
use_main_walls = False
use_flood_spam = True
product_id = "BTC-USD"
main_sell_price = 100000
main_buy_price = 50000
flood_base_amount = 0.001
main_base_amount = 5

#######################################
#### ONLY CHANGE THINGS ABOVE THIS ####
#######################################

getcontext().prec = 16

def fetch_product_list(client):
    try:
        response = client.get_products()
        products = response.get('products')
        if isinstance(products, list):
            return products
        else:
            raise TypeError("API response does not contain a list of products.")
    except Exception as e:
        print(f"Error fetching product list: {e}")
        sys.exit(1)

product_list = fetch_product_list(client)

def get_increments_from_list(product_list, product_id):
    for product in product_list:
        # Check both "id" and "product_id" just in case
        if product.get("id") == product_id or product.get("product_id") == product_id:
            quote_increment = Decimal(product['quote_increment'])
            base_increment = Decimal(product['base_increment'])
            return quote_increment, base_increment
    raise ValueError(f"Product {product_id} not found in product list.")

# Convert user-specified floats/ints to Decimal
main_sell_price = Decimal(str(main_sell_price))
main_buy_price = Decimal(str(main_buy_price))
flood_base_amount = Decimal(str(flood_base_amount))
main_base_amount = Decimal(str(main_base_amount))

quote_increment, base_increment = get_increments_from_list(product_list, product_id)

# Flood base amount: use either user config or product's base_increment
if force_flood_base_increment:
    flood_base_amount_str = str(base_increment)
else:
    flood_base_amount_str = str(flood_base_amount)

# Main base amount is always from config
main_base_amount_str = str(main_base_amount)

# Compute flood prices using Decimal and quantize to the quote_increment
flood_buy_price = (main_sell_price - quote_increment).quantize(quote_increment, rounding=ROUND_DOWN)
flood_sell_price = (main_buy_price + quote_increment).quantize(quote_increment, rounding=ROUND_DOWN)

main_buy_price_str = str(main_buy_price)
main_sell_price_str = str(main_sell_price)
flood_buy_price_str = str(flood_buy_price)
flood_sell_price_str = str(flood_sell_price)

if debug:
    print("Debug info:")
    print("main_buy_price_str:", main_buy_price_str)
    print("main_sell_price_str:", main_sell_price_str)
    print("flood_buy_price_str:", flood_buy_price_str)
    print("flood_sell_price_str:", flood_sell_price_str)
    print("main_base_amount_str:", main_base_amount_str)
    print("flood_base_amount_str:", flood_base_amount_str)

def get_unique_client_order_id():
    return str(uuid.uuid4())

def get_timestamp():
    return datetime.now().strftime('%m-%d-%y %H:%M:%S.%f')[:-3]

def wait_for_user():
    input("Press Enter to exit...")

def handle_order_error(order_response, order_type):
    if not order_response["success"] and "error_response" in order_response:
        error_message = order_response["error_response"]["message"]
        error_preview_failure_reason = order_response["error_response"].get("preview_failure_reason", "")
        if debug:
            print(f"{order_type} order error:", error_message)

        if ("PREVIEW_INVALID_BASE_SIZE_TOO_SMALL" in error_preview_failure_reason or 
            "Too many decimals in order price" in error_message):
            print("Error encountered: Base size or increment issue.")
            if stop_on_base_amount_error:
                print("Stopping script due to base amount/increment error.")
                wait_for_user()
                sys.exit()
            else:
                print("Continuing despite the base amount/increment error, as stop_on_base_amount_error=False")
                return

        if "Insufficient balance in source account" in error_message:
            if show_insufficient_funds:
                print("Insufficient balance detected.")
            if stop_on_insufficient_funds:
                print("Stopping the script due to insufficient funds.")
                wait_for_user()
                sys.exit()
            else:
                return

        if not order_response["success"]:
            print("Order not successful. Error message:", error_message)
            print("Continuing despite the error.")
            return

def handle_specific_errors(error_message):
    if "Rate limit exceeded" in error_message:
        print("Rate limit exceeded. Waiting for", rate_limit_delay, "seconds.")
        time.sleep(rate_limit_delay)
    elif "HTTP Error: 400" in error_message:
        print("Bad Request: The request was too complex for Coinbase to handle. Waiting for", rate_limit_delay, "seconds.")
        time.sleep(rate_limit_delay)
    elif "HTTP Error: 401" in error_message:
        print("Unauthorized: Check your API keys.")
        wait_for_user()
        sys.exit()
    elif "HTTP Error: 403" in error_message:
        print("Forbidden: Re-KYC might be required.")
        wait_for_user()
        sys.exit()
    elif ("HTTP Error: 500" in error_message or 
          "HTTP Error: 502" in error_message or 
          "HTTP Error: 503" in error_message):
        print("Server error at Coinbase.")
        wait_for_user()
        sys.exit()

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

def suppress_coinbase_logs():
    logger = logging.getLogger("coinbase.RESTClient")
    logger.setLevel(logging.CRITICAL)
    handler = logging.NullHandler()
    logger.addHandler(handler)

def main():
    global order_count
    order_count = 0

    suppress_coinbase_logs()

    if not use_main_walls and not use_flood_spam:
        print("You need to enable Main Walls or Flood Spam to start the script.")
        wait_for_user()
        sys.exit()

    if not enable_buying and not enable_selling:
        print("You need to enable buying or selling to start. Stopping the script.")
        wait_for_user()
        sys.exit()

    try:
        while True:
            try:
                # Order flow: Main Buy, Flood Buy, Main Sell, Flood Sell

                # Main Buy
                if use_main_walls and enable_buying:
                    main_buy_order = place_limit_order("buy", product_id, main_base_amount_str, main_buy_price_str)
                    if debug:
                        print("Main Buy Order Response:", dumps(main_buy_order, indent=2))
                    handle_order_error(main_buy_order, "Main Buy")
                    if not debug:
                        order_count += 1
                        print("{} - {} - {} - {} - Main Buy".format(
                            get_timestamp(), product_id, order_count, main_buy_price_str))

                time.sleep(sleep_duration)

                # Flood Buy
                if use_flood_spam and enable_buying:
                    flood_buy_order = place_limit_order("buy", product_id, flood_base_amount_str, flood_buy_price_str)
                    if debug:
                        print("Flood Buy Order Response:", dumps(flood_buy_order, indent=2))
                    handle_order_error(flood_buy_order, "Flood Buy")
                    if not debug:
                        order_count += 1
                        print("{} - {} - {} - {} - Flood Buy".format(
                            get_timestamp(), product_id, order_count, flood_buy_price_str))

                time.sleep(sleep_duration)

                # Main Sell
                if use_main_walls and enable_selling:
                    main_sell_order = place_limit_order("sell", product_id, main_base_amount_str, main_sell_price_str)
                    if debug:
                        print("Main Sell Order Response:", dumps(main_sell_order, indent=2))
                    handle_order_error(main_sell_order, "Main Sell")
                    if not debug:
                        order_count += 1
                        print("{} - {} - {} - {} - Main Sell".format(
                            get_timestamp(), product_id, order_count, main_sell_price_str))

                time.sleep(sleep_duration)

                # Flood Sell
                if use_flood_spam and enable_selling:
                    flood_sell_order = place_limit_order("sell", product_id, flood_base_amount_str, flood_sell_price_str)
                    if debug:
                        print("Flood Sell Order Response:", dumps(flood_sell_order, indent=2))
                    handle_order_error(flood_sell_order, "Flood Sell")
                    if not debug:
                        order_count += 1
                        print("{} - {} - {} - {} - Flood Sell".format(
                            get_timestamp(), product_id, order_count, flood_sell_price_str))

                time.sleep(sleep_duration)

            except Exception as e:
                error_message = str(e)
                # Handle known HTTP error codes
                if any(code in error_message for code in ["429", "403", "400", "401", "500", "502", "503"]):
                    handle_specific_errors(error_message)
                else:
                    print("Order error:", error_message)
                    # Continue on other errors

    except KeyboardInterrupt:
        print("Script stopped by user.")
    except Exception as e:
        print("An error occurred:", str(e))
        wait_for_user()

if __name__ == "__main__":
    main()
