import uuid
import time
import os
from datetime import datetime
import sys
import logging
from json import dumps
from dotenv import load_dotenv
from kucoin.client import Client  # Kucoin's Client
from decimal import Decimal, getcontext, ROUND_DOWN

# Load environment variables from .env file
load_dotenv()

# Kucoin API credentials
api_key = os.getenv("KUCOIN_API_KEY")
api_secret = os.getenv("KUCOIN_API_SECRET")
api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")  # Kucoin requires a passphrase

# Initialize Kucoin client
client = Client(api_key=api_key, api_secret=api_secret, passphrase=api_passphrase)

#######################################
#### ONLY CHANGE THINGS UNDER THIS ####
#######################################

# Configuration parameters
sleep_duration = 0.01
rate_limit_delay = 1  # Adjusted for Kucoin's rate limits
debug = False
stop_on_insufficient_funds = False

# Trading rules
force_base_amount = True 
enable_waves = False
enable_normal = True
enable_buying = True
enable_selling = False

# Strategy configuration - Only use one

product_id = "ZEN-USDT"
sell_price = 26.129
buy_price = 28.936
specified_base_amount = 0.01

# Define product-specific parameters manually
# These values should be set according to the product's requirements on Kucoin
price_decimal_places = 3  # Number of decimal places for the price (e.g., 0.01)
size_decimal_places = 2   # Number of decimal places for the base size (e.g., 0.1)
size_increment = Decimal('0.1')  # Minimum order size increment

# True to use a specific amount
# False to set the minimum base amount automatically

#######################################
#### ONLY CHANGE THINGS ABOVE THIS ####
#######################################

# Set the precision for decimal operations
getcontext().prec = 16  # Increase precision to avoid rounding issues

def format_decimal(number, decimal_places):
    """
    Formats a decimal number to the specified number of decimal places,
    rounding down to avoid exceeding the required precision.
    """
    decimal_number = Decimal(number).quantize(Decimal(10) ** -decimal_places, rounding=ROUND_DOWN)
    formatted_number = f"{decimal_number:.{decimal_places}f}"
    return formatted_number

# Directly assign buy_price_str, sell_price_str, and base_amount_str to their values
buy_price_str = format_decimal(buy_price, price_decimal_places)
sell_price_str = format_decimal(sell_price, price_decimal_places)
base_amount_str = format_decimal(specified_base_amount, size_decimal_places) if force_base_amount else format_decimal(size_increment, size_decimal_places)

# Ensure the limit prices are not zero after formatting
if Decimal(buy_price_str) == 0 or Decimal(sell_price_str) == 0:
    raise ValueError("One of the limit prices is zero after formatting. Please check the buy and sell prices.")

# Calculate wave sizes based on the forced amount if required
base_amount_to_use = Decimal(specified_base_amount) if force_base_amount else Decimal(size_increment)

wave_sizes = [format_decimal(base_amount_to_use * Decimal(x), size_decimal_places) for x in [1, 3, 5, 7, 5, 3]]
# wave_sizes = [format_decimal(base_amount_to_use * Decimal(x), size_decimal_places) for x in [69,420,24,7,365]]

# Trading pairs configuration
trading_pairs = []

if enable_waves:
    trading_pairs.extend([
        {
            "symbol": product_id,
            "buy_price": buy_price_str,
            "sell_price": sell_price_str,
            "size": size.rstrip('0').rstrip('.') if '.' in size else size  # Remove unnecessary trailing zeros
        }
        for size in wave_sizes
    ])

if enable_normal:
    # Calculate the base size based on force_base_amount
    if force_base_amount:
        base_size = Decimal(specified_base_amount)
    else:
        base_size = Decimal(size_increment)

    # Format the base size to the correct precision
    base_size_str = format_decimal(base_size, size_decimal_places)

    # Create and append the normal strategy pair
    normal_strategy_pair = {
        "symbol": product_id,
        "buy_price": buy_price_str,
        "sell_price": sell_price_str,
        "size": base_size_str.rstrip('0').rstrip('.') if '.' in base_size_str else base_size_str
    }
    trading_pairs.append(normal_strategy_pair)

# Debugging information
if debug:
    print(f"buy_price_str: {buy_price_str}")
    print(f"sell_price_str: {sell_price_str}")
    print(f"base_amount_str: {base_amount_str}")
    print(f"wave_sizes: {wave_sizes}")
    print(f"trading_pairs: {dumps(trading_pairs, indent=2)}")

# Generate a unique client order ID.
def get_unique_client_order_id():
    return str(uuid.uuid4())

# Return the current timestamp.
def get_timestamp():
    return datetime.now().strftime('%m-%d-%y %H:%M:%S.%f')[:-3]

# Define the wait_for_user function
def wait_for_user():
    input("Press Enter to exit...")  # Wait for user input before exiting

# Handle errors from order responses.
def handle_order_error(order_response, order_type):
    if not order_response.get("success", False):
        error_message = order_response.get("msg", "")
        if debug:
            print(f"{order_type} order error:", error_message)
        if "price increment invalid" in error_message.lower():
            print("Error: The price increment is invalid. Please ensure your price aligns with Kucoin's price increment requirements.")
            wait_for_user()  # Call the function
            sys.exit()  # Stop the script
        if "base size too small" in error_message.lower():
            print("Error: The base size is too small. Please check the minimum base size and adjust your configuration.")
            wait_for_user()  # Call the function
            sys.exit()  # Stop the script
        if "insufficient balance" in error_message.lower():
            print("Insufficient balance detected.")
            if stop_on_insufficient_funds:
                print("Stopping the script due to insufficient funds.")
                wait_for_user()  # Call the function
                sys.exit()  # Stop the script

# Handle specific errors based on error messages.
def handle_specific_errors(error_message):
    if "rate limit" in error_message.lower():
        print("Rate limit exceeded. Waiting for", rate_limit_delay, "seconds.")
        time.sleep(rate_limit_delay)
    elif "bad request" in error_message.lower():
        print("Bad Request: The request was invalid. Waiting for", rate_limit_delay, "seconds.")
        time.sleep(rate_limit_delay)
    elif "unauthorized" in error_message.lower():
        print("Unauthorized: Check your API keys.")
        wait_for_user()  # Call the function
        sys.exit()  # Stop the script
    elif "forbidden" in error_message.lower():
        print("Forbidden: Check your API permissions.")
        wait_for_user()  # Call the function
        sys.exit()  # Stop the script
    elif any(code in error_message.lower() for code in ["server error", "gateway timeout"]):
        print("Server error at Kucoin.")
        wait_for_user()  # Call the function
        sys.exit()  # Stop the script

# Place a limit order.
def place_limit_order(order_type, symbol, size, price):
    client_order_id = get_unique_client_order_id()
    if debug:
        print(f"Placing {order_type} order for {symbol} with size {size} and price {price}")
    try:
        if order_type == "buy":
            order = client.create_limit_order(symbol, Client.SIDE_BUY, size=size, price=price, time_in_force='GTC')
            return {"success": True, "data": order}
        elif order_type == "sell":
            order = client.create_limit_order(symbol, Client.SIDE_SELL, size=size, price=price, time_in_force='GTC')
            return {"success": True, "data": order}
        else:
            raise ValueError("Invalid order type. Use 'buy' or 'sell'.")
    except Exception as e:
        return {"success": False, "msg": str(e)}

# Suppress Kucoin REST client logs.
def suppress_kucoin_logs():
    logger = logging.getLogger("kucoin")
    logger.setLevel(logging.CRITICAL)  # Suppress messages below CRITICAL level
    handler = logging.NullHandler()
    logger.addHandler(handler)

# Main function to run the script.
def main():
    global order_count
    order_count = 0

    suppress_kucoin_logs()  # Suppress Kucoin logs

    if not enable_buying and not enable_selling:
        print("You need to enable buying or selling to start. Stopping the script.")
        wait_for_user()  # Call the function
        sys.exit()

    try:
        while True:
            try:
                for pair in trading_pairs:
                    symbol = pair["symbol"]
                    buy_price = pair["buy_price"]
                    sell_price = pair["sell_price"]
                    size = pair["size"]

                    if enable_buying:
                        # Place buy limit order
                        buy_order = place_limit_order("buy", symbol, size, buy_price)
                        if debug:
                            print("Buy Order Response:", dumps(buy_order, indent=2))
                        handle_order_error(buy_order, "Buy")

                        if buy_order.get("success", False) and not debug:
                            order_count += 1
                            print("{} - {} - {} - Buy".format(get_timestamp(), symbol, order_count))

                    # Short wait before placing the sell order
                    time.sleep(sleep_duration)

                    if enable_selling:
                        # Place sell limit order
                        sell_order = place_limit_order("sell", symbol, size, sell_price)
                        if debug:
                            print("Sell Order Response:", dumps(sell_order, indent=2))
                        handle_order_error(sell_order, "Sell")

                        if sell_order.get("success", False) and not debug:
                            order_count += 1
                            print("{} - {} - {} - Sell".format(get_timestamp(), symbol, order_count))

                    # Short wait to avoid flooding requests
                    time.sleep(sleep_duration)

            except Exception as e:
                error_message = str(e)
                if any(code in error_message.lower() for code in ["rate limit", "forbidden", "bad request", "unauthorized", "server error", "gateway timeout"]):
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
