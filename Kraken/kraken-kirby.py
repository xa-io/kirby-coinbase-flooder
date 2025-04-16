
# KIRBY KRAKEN FLOODER - TESTING PHASE
# WARNING: This script is in testing phase and should be used with caution.
# This implementation includes bare minimum functions and should ALWAYS be
# monitored when in use. Message me if you break things. :)

import uuid
import time
import os
from datetime import datetime
import sys
import logging
import random
from json import dumps
from dotenv import load_dotenv
import krakenex
from decimal import Decimal, getcontext, ROUND_DOWN

# Load environment variables from .env file
load_dotenv()

# Retrieve Kraken API key/secret from environment
api_key = os.getenv("KRAKEN_API_KEY")
api_secret = os.getenv("KRAKEN_API_SECRET")

# Initialize krakenex client
k = krakenex.API(key=api_key, secret=api_secret)

#######################################
#### ONLY CHANGE THINGS UNDER THIS ####
#######################################

# Configuration parameters
rate_limit_delay = 5   # Some small default to avoid spamming, adjust as needed
debug = False
show_insufficient_funds = True
stop_on_insufficient_funds = False
stop_on_base_amount_error = True

# Trading parameters
enable_buying = True
enable_selling = False
use_main_walls = False
use_flood_spam = True

# On Kraken, product pairs are named differently, e.g.:
product_id = "OMUSD"

# Adjust prices and volumes as desired
#
# *** YOU MUST ENTER A BASE AMOUNT ***
# Go figure out the minumum order size probably around $0.50 worth, and change your flood base amount to be slightly higher
#
sleep_duration = 1.15 # I wouldn't go faster than 0.1 :D
main_sell_price = 0.8376
main_buy_price = 0.1472
flood_base_amount = 0.000000001 # Update me
main_base_amount = 0.02

#######################################
#### ONLY CHANGE THINGS ABOVE THIS ####
#######################################

# Set higher decimal precision if needed
getcontext().prec = 16

def fetch_asset_pairs(client):
    """
    Fetch the list of asset pairs from Kraken.
    Returns a dict containing asset pair info keyed by pair name.
    """
    try:
        resp = client.query_public('AssetPairs')
        error = resp.get('error')
        if error:
            # If there's any error text, handle or raise it
            raise Exception(f"Error fetching asset pairs: {error}")
        return resp.get('result', {})
    except Exception as e:
        print(f"Error fetching asset pairs: {e}")
        sys.exit(1)

def get_pair_info(pair_data, product_id):
    """
    Return (price_increment, base_increment, ordermin) for the given product_id.
    On Kraken:
        - 'pair_decimals' = allowed decimals in price
        - 'lot_decimals'  = allowed decimals in volume
        - 'ordermin'      = minimum volume allowed for an order
    """
    if product_id not in pair_data:
        raise ValueError(f"Pair {product_id} not found in Kraken AssetPairs result.")

    info = pair_data[product_id]
    
    price_decimals = info['pair_decimals']    # e.g. 5
    lot_decimals   = info['lot_decimals']     # e.g. 8
    ordermin_str   = info['ordermin']         # e.g. "0.05"
    
    # Create a Decimal representing the smallest price increment
    price_increment = Decimal('1') / (Decimal('10') ** Decimal(price_decimals))
    # Create a Decimal representing the smallest volume increment
    base_increment  = Decimal('1') / (Decimal('10') ** Decimal(lot_decimals))
    
    ordermin = Decimal(ordermin_str)
    return price_increment, base_increment, ordermin

# 1) Fetch pair data from Kraken
pair_data = fetch_asset_pairs(k)

# 2) Convert user-specified floats/ints to Decimals
main_sell_price   = Decimal(str(main_sell_price))
main_buy_price    = Decimal(str(main_buy_price))
flood_base_amount = Decimal(str(flood_base_amount))
main_base_amount  = Decimal(str(main_base_amount))

# 3) Compute increments and minimum
quote_increment, base_increment, ordermin = get_pair_info(pair_data, product_id)

# 4) Enforce that base amounts are at least the minimum
if flood_base_amount < ordermin:
    flood_base_amount = ordermin
if main_base_amount < ordermin:
    main_base_amount = ordermin

# 5) Quantize volumes to the base_increment
flood_base_amount = flood_base_amount.quantize(base_increment, rounding=ROUND_DOWN)
main_base_amount  = main_base_amount.quantize(base_increment,  rounding=ROUND_DOWN)

# 6) Compute flood buy/sell prices (1 tick away from main prices)
flood_buy_price  = (main_sell_price - quote_increment).quantize(quote_increment, rounding=ROUND_DOWN)
flood_sell_price = (main_buy_price  + quote_increment).quantize(quote_increment, rounding=ROUND_DOWN)

# Convert everything back to strings for the final order calls
main_buy_price_str      = str(main_buy_price)
main_sell_price_str     = str(main_sell_price)
main_base_amount_str    = str(main_base_amount)
flood_buy_price_str     = str(flood_buy_price)
flood_sell_price_str    = str(flood_sell_price)
flood_base_amount_str   = str(flood_base_amount)

if debug:
    print("Debug info:")
    print("main_buy_price_str:", main_buy_price_str)
    print("main_sell_price_str:", main_sell_price_str)
    print("flood_buy_price_str:", flood_buy_price_str)
    print("flood_sell_price_str:", flood_sell_price_str)
    print("main_base_amount_str:", main_base_amount_str)
    print("flood_base_amount_str:", flood_base_amount_str)
    print("Kraken pair minimum volume (ordermin):", ordermin)

def get_timestamp():
    return datetime.now().strftime('%m-%d-%y %H:%M:%S.%f')[:-3]

def wait_for_user():
    input("Press Enter to exit...")

def handle_order_error(order_response, order_type):
    """
    Krakenex response structure typically:
       {
         "error": [...],
         "result": {...}
       }
    If "error" is non-empty, there's an error.
    Otherwise "result" holds success info.
    """
    errors = order_response.get("error", [])
    if errors:
        error_str = "; ".join(errors)
        if debug:
            print(f"{order_type} order error: {error_str}")

        # Example error patterns on Kraken:
        # EOrder:Insufficient funds
        # EAPI:Rate limit exceeded
        # EOrder:Invalid price
        # EGeneral:Permission denied
        # ...
        if "Insufficient funds" in error_str:
            if show_insufficient_funds:
                print("Insufficient balance detected.")
            if stop_on_insufficient_funds:
                print("Stopping the script due to insufficient funds.")
                wait_for_user()
                sys.exit()
            else:
                return

        if "volume minimum not met" in error_str or "Invalid volume" in error_str or "lot size" in error_str:
            print("Error encountered: base amount or increment issue.")
            if stop_on_base_amount_error:
                print("Stopping script due to base amount/increment error.")
                wait_for_user()
                sys.exit()
            else:
                print("Continuing despite the base amount/increment error.")
                return

        print(f"Order not successful. Error message: {error_str}")
        print("Continuing despite the error.")

def handle_specific_errors(error_message):
    """
    You can expand logic for specific Kraken error strings.
    For example:
    - 'EAPI:Rate limit exceeded'
    - 'EGeneral:Permission denied'
    - ...
    """
    if "Rate limit exceeded" in error_message:
        print("Rate limit exceeded. Waiting for", rate_limit_delay, "seconds.")
        time.sleep(rate_limit_delay)
    elif "EAPI:Invalid key" in error_message:
        print("Unauthorized: Check your API keys.")
        wait_for_user()
        sys.exit()
    elif "EGeneral:Permission denied" in error_message:
        print("Forbidden: Possibly need more API permissions.")
        wait_for_user()
        sys.exit()
    else:
        # For other HTTP or API errors, handle as needed
        print("Order error:", error_message)

def place_limit_order(order_type, product_id, base_size, price):
    """
    Places a limit order on Kraken.
    - order_type: 'buy' or 'sell'
    - product_id: e.g. 'TRUMPUSD'
    - base_size: decimal string for quantity
    - price: decimal string for limit price
    """
    # userref must be an integer for Kraken. We'll randomly generate a valid 32-bit int
    userref = random.randint(1, 2_147_483_647)

    if debug:
        print(f"Placing {order_type} limit order: pair={product_id}, volume={base_size}, price={price}")

    data = {
        'pair': product_id,
        'type': order_type,
        'ordertype': 'limit',
        'price': price,
        'volume': base_size,
        'userref': userref
    }

    response = k.query_private('AddOrder', data)
    return response

def suppress_krakenex_logs():
    """
    By default, krakenex might not be super chatty, but if you want to
    suppress or redirect logs, you can adjust logging here.
    """
    logger = logging.getLogger("krakenex")
    logger.setLevel(logging.CRITICAL)
    handler = logging.NullHandler()
    logger.addHandler(handler)

def main():
    global order_count
    order_count = 0

    suppress_krakenex_logs()

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
                            get_timestamp(), product_id, order_count, main_buy_price_str
                        ))
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
                            get_timestamp(), product_id, order_count, flood_buy_price_str
                        ))
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
                            get_timestamp(), product_id, order_count, main_sell_price_str
                        ))
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
                            get_timestamp(), product_id, order_count, flood_sell_price_str
                        ))
                time.sleep(sleep_duration)

            except Exception as e:
                error_message = str(e)
                # If it matches typical Kraken error strings
                if any(x in error_message for x in ["EAPI:", "EOrder:", "EGeneral:"]):
                    handle_specific_errors(error_message)
                else:
                    print("Order error:", error_message)
                    # Decide whether to continue or break
                    # continue

    except KeyboardInterrupt:
        print("Script stopped by user.")
    except Exception as e:
        print("An error occurred:", str(e))
        wait_for_user()

if __name__ == "__main__":
    main()
