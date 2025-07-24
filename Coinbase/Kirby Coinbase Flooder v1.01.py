############################################################################################################################
# 
# Kirby Coinbase Flooder v1.01
#
# This script combines orderbook scanning and limit order flooding functionality to:
# 1. Monitor the orderbook for a selected trading pair
# 2. Detect spread gaps between bid and ask prices
# 3. Fill any gaps with flood orders
# 4. Continue flooding orders to targeted price levels
#
# Important Note: Running this script carries the risk of your Coinbase account being flagged for suspicious
# activity, which may require you to re-complete KYC verification. It is recommended to set up a separate
# portfolio on Coinbase to avoid inadvertently using large balances.
#
# Configuration Parameters are available below and in README.md
#
# Revision Notes:
#
# v1.01 - Added SHOW_SPREAD_INFO option (default: False) to reduce console clutter by conditionally displaying spread analysis information
#       - Improved log formatting by removing USD suffix from pair names and restructuring timestamp display for cleaner output
#
# v1.00 - Initial release
#
############################################################################################################################

###########################################
#### Start of Configuration Parameters ####
###########################################

# Orderbook scanner settings
SCAN_INTERVAL = 3
SPREAD_ORDER_DELAY = 0.2
MAX_SPREAD_ORDERS = 3
FILL_SPREAD = True
FILL_BUYSELL_DISABLE = True
SHOW_SPREAD_INFO = False

# Order flooding settings
PAIR = "BTC-USD"
ENABLE_BUYING = True
ENABLE_SELLING = False
USE_MAIN_WALLS = False
USE_FLOOD_SPAM = True
MAIN_SELL_PRICE = 125000.00
MAIN_BUY_PRICE = 105000.00
STOP_ON_INSUFFICIENT_FUNDS = True

# Flood settings
FORCE_FLOOD_BASE_INCREMENT = True
FLOOD_BASE_AMOUNT = 0.0000001
MAIN_BASE_AMOUNT = 0.0001

# System settings
SLEEP_DURATION = 0.2
RATE_LIMIT_DELAY = 1
DEBUG = False
SHOW_TIMESTAMP = False
SHOW_HTTP_ERRORS = False
SHOW_INSUFFICIENT_FUNDS = True
STOP_ON_BASE_AMOUNT_ERROR = True

# Products file configuration
PRODUCTS_FILE = "products.json"
PRODUCTS_MAX_AGE_HOURS = 72

#########################################
#### End of Configuration Parameters ####
#########################################

import os
import time
import uuid
import requests
import datetime
import sys
import logging
import json
import io
import sys
from contextlib import redirect_stderr
from json import dumps
from dotenv import load_dotenv
from coinbase.rest import RESTClient
from decimal import Decimal, getcontext, ROUND_DOWN

# Load environment variables from .env file
load_dotenv()

# Get script directory for relative file paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define logging function first
def suppress_coinbase_logs():
    logger = logging.getLogger("coinbase.RESTClient")
    logger.setLevel(logging.CRITICAL)
    handler = logging.NullHandler()
    logger.addHandler(handler)

# Call log suppression before creating client
suppress_coinbase_logs()

# API setup
api_key = os.getenv("COINBASE_API_KEY")
api_secret = os.getenv("COINBASE_API_SECRET")
client = RESTClient(api_key=api_key, api_secret=api_secret)

# Set decimal precision
getcontext().prec = 16

# Global variables
order_count = 0
spread_orders = []
debug = DEBUG
product_id = PAIR

# Function to get formatted timestamp for logging
def get_timestamp():
    if SHOW_TIMESTAMP:
        return f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] - "
    return ""

# Helper function for logging with timestamp
def log(message):
    """Log a message with timestamp if configured"""
    print(f"{get_timestamp()}{message}")

# API request function for orderbook data
def make_api_request(url, resource_name="resource"):
    """Make an API request to Coinbase"""
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        
        log(f"Error fetching {resource_name}: {response.status_code} {response.text}")
        return None
        
    except Exception as e:
        log(f"Exception fetching {resource_name}: {e}")
        return None

# Format number with specified decimal precision
def format_with_precision(num, decimals):
    """Format number with specified decimal precision"""
    if isinstance(num, str):
        num = float(num)
    format_str = f"{{:.{decimals}f}}"
    return format_str.format(num)

# Fetch product information
def get_product_info(product_id):
    """Fetch product information to determine appropriate decimal precision"""
    return client.get_product(product_id)

# Products.json handling functions
def get_products_from_api():
    """Fetch all product information from Coinbase Exchange API"""
    url = "https://api.exchange.coinbase.com/products"
    return make_api_request(url, "products")

def ensure_products_file():
    """Ensure the products file exists and is up-to-date"""
    products_file = os.path.join(SCRIPT_DIR, PRODUCTS_FILE)
    max_age_hours = PRODUCTS_MAX_AGE_HOURS
    current_datetime = datetime.datetime.now()
    
    # Check products file status
    products_file_exists = os.path.isfile(products_file)
    products_file_outdated = True
    
    if products_file_exists:
        # Check products file age
        products_file_timestamp = os.path.getmtime(products_file)
        products_file_age = (current_datetime.timestamp() - products_file_timestamp) / 3600  # Convert to hours
        products_file_outdated = products_file_age > max_age_hours
        
        if debug:
            log(f"Products file age: {products_file_age:.1f} hours (max: {max_age_hours})")
    
    # Case 1: Products file doesn't exist or is outdated
    if not products_file_exists or products_file_outdated:
        if debug:
            status = "doesn't exist" if not products_file_exists else "is outdated"
            log(f"Products file {status}. Fetching from API...")
        
        try:
            # Fetch products from API
            products = get_products_from_api()
            if not products:
                log("Failed to fetch products from API")
                if products_file_exists:
                    # Fall back to existing file if API fails
                    log("Using existing products file as fallback")
                    with open(products_file, 'r') as f:
                        return json.load(f)
                return None
            
            # Save products to file
            with open(products_file, 'w') as f:
                json.dump(products, f, indent=2)
            log(f"Updated products file with {len(products)} products")
            return products
            
        except Exception as e:
            log(f"Error updating products file: {e}")
            if products_file_exists:
                # Fall back to existing file if update fails
                try:
                    with open(products_file, 'r') as f:
                        return json.load(f)
                except Exception as e2:
                    log(f"Error loading existing products file: {e2}")
            return None
    
    # Case 2: Products file exists and is up-to-date
    else:
        try:
            with open(products_file, 'r') as f:
                products = json.load(f)
            if debug:
                log(f"Loaded {len(products)} products from existing file")
            return products
        except Exception as e:
            log(f"Error loading products file: {e}")
            return None

def get_product_from_list(products_data, product_id):
    """Get information about a specific product from the products data"""
    if not products_data:
        return None
    
    # Find the product in the data
    for product in products_data:
        if product.get("id") == product_id:
            return product
    
    return None

def get_base_increment_for_pair(product_id):
    """Get the base_increment for a trading pair, updating products.json if needed"""
    # First, try to load existing products data
    products_data = ensure_products_file()
    
    if products_data:
        product_info = get_product_from_list(products_data, product_id)
        if product_info:
            base_increment = product_info.get("base_increment")
            if base_increment:
                if debug:
                    log(f"Found base_increment for {product_id}: {base_increment}")
                return float(base_increment)
    
    # If we couldn't find the product, try to refresh the products file
    log(f"Product {product_id} not found in products file. Refreshing...")
    
    # Force refresh by fetching from API
    try:
        products = get_products_from_api()
        if products:
            # Save updated products to file
            products_file = os.path.join(SCRIPT_DIR, PRODUCTS_FILE)
            with open(products_file, 'w') as f:
                json.dump(products, f, indent=2)
            log(f"Refreshed products file with {len(products)} products")
            
            # Try to find the product again
            product_info = get_product_from_list(products, product_id)
            if product_info:
                base_increment = product_info.get("base_increment")
                if base_increment:
                    log(f"Found base_increment for {product_id} after refresh: {base_increment}")
                    return float(base_increment)
    except Exception as e:
        log(f"Error refreshing products data: {e}")
    
    # If we still can't find it, return None
    log(f"Unable to find base_increment for {product_id}")
    return None

# Fetch the orderbook
def get_orderbook(product_id, level=1):
    """Fetch the orderbook for a given product using public API
    Level 1 only returns the best bid and ask"""
    url = f"https://api.exchange.coinbase.com/products/{product_id}/book?level={level}"
    return make_api_request(url, f"orderbook for {product_id}")

# Determine the appropriate decimal precision
def determine_precision(product_info):
    """Determine the appropriate decimal precision based on product details"""
    # Default precision for edge cases
    precision = 8
    
    try:
        if product_info and "quote_increment" in product_info:
            # Count decimal places in the quote increment
            quote_increment = product_info["quote_increment"]
            decimal_str = quote_increment.split('.')[-1]
            # Count non-zero decimal places
            precision = len(decimal_str.rstrip('0'))
            # If precision is somehow 0, use reasonable default
            if precision == 0:
                precision = 8
    except Exception as e:
        log(f"Error determining precision: {e}, using default precision: 8")
        precision = 8
        
    return precision

# Coinbase API Functions
def fetch_product_list(client):
    """Fetch the list of products from Coinbase API"""
    try:
        products_response = client.get_products()
        return products_response.get("products", [])
    except Exception as e:
        print(f"Error fetching product list: {e}")
        wait_for_user()
        sys.exit(1)

# Get product increments from the product list
def get_increments_from_list(product_list, product_id):
    """Get the base and quote increments for a product"""
    for product in product_list:
        if product.get("product_id") == product_id:
            return product.get("base_increment"), product.get("quote_increment")
    print(f"Product {product_id} not found in product list.")
    return None, None

# Generate unique client order ID
def get_unique_client_order_id():
    """Generate a unique client order ID"""
    return str(uuid.uuid4())

# Pause execution for user input
def wait_for_user():
    """Wait for user to press Enter"""
    input("Press Enter to continue...")

# Handle order errors
def handle_order_error(order_result, order_type):
    """Handle errors from order placement"""
    # Approach to check for success and error_response directly
    if not order_result.get("success", True) and "error_response" in order_result:
        error_message = order_result["error_response"].get("message", "Unknown error")
        error_preview_failure_reason = order_result["error_response"].get("preview_failure_reason", "")
        
        # Debug logging
        if debug:
            print(f"{order_type} order error:", error_message)

        # Handle base_min_size errors
        if ("PREVIEW_INVALID_BASE_SIZE_TOO_SMALL" in error_preview_failure_reason or
            "Too many decimals in order price" in str(error_message).lower()):
            print(f"Error encountered: Base size or increment issue: {error_message}")
            if STOP_ON_BASE_AMOUNT_ERROR:
                print("Stopping script due to base amount/increment error.")
                wait_for_user()
                sys.exit(1)
            else:
                print("Continuing despite the base amount/increment error, as STOP_ON_BASE_AMOUNT_ERROR=False")
                return "size_error"
        
        # Handle insufficient funds errors
        elif "Insufficient balance in source account" in error_message:
            if SHOW_INSUFFICIENT_FUNDS:
                print("Insufficient balance detected.")
                print(f"Full error: {error_message}")
            
            if STOP_ON_INSUFFICIENT_FUNDS:
                print("Stopping the script due to insufficient funds. Please fund your account and try again.")
                wait_for_user()
                sys.exit(1)
            else:
                print("Continuing despite insufficient funds, as STOP_ON_INSUFFICIENT_FUNDS=False")
                return "insufficient_funds"
        
        # Handle known HTTP error codes
        elif any(code in str(error_message) for code in ["429", "403", "400", "401", "500", "502", "503"]):
            return handle_specific_errors(str(error_message))
        
        # Other errors
        else:
            print(f"{order_type} Order Error: {error_message}")
            return "other_error"
    
    # Legacy handling for direct exceptions caught by try/except (may not be needed with new approach)
    elif isinstance(order_result, dict) and "error" in order_result:
        error_message = order_result.get("error", "Unknown error")
        error_message_str = str(error_message).lower()
        
        # Handle insufficient funds errors through exception message
        if any(phrase in error_message_str for phrase in ["insufficient", "not enough", "balance", "funds"]):
            if SHOW_INSUFFICIENT_FUNDS:
                print(f"{order_type} Order Error: Insufficient funds")
                print(f"Full error: {error_message}")
            
            if STOP_ON_INSUFFICIENT_FUNDS:
                print("Stopping due to insufficient funds. Please fund your account and try again.")
                wait_for_user()
                sys.exit(1)
            
            return "insufficient_funds"

        # Other exception-based errors
        print(f"{order_type} Order Exception: {error_message}")
        return "exception_error"
    
    # Return False for successful orders (no error)
    return False

# Handle specific API errors
def handle_specific_errors(error_message):
    """Handle specific API errors by HTTP status code"""
    if "429" in error_message:  # Rate limiting
        # For rate limiting, use a longer delay than the configured one
        rate_limit_delay = max(RATE_LIMIT_DELAY, 0.0)
        # Only print the message if SHOW_HTTP_ERRORS is enabled
        if SHOW_HTTP_ERRORS:
            print(f"Rate limit hit, pausing for {rate_limit_delay} seconds...")
        time.sleep(rate_limit_delay)
        # Increase sleep duration for future calls within this cycle
        return True  # Return True to indicate rate limiting was handled
    elif "403" in error_message:  # Forbidden
        print("Access denied. Check your API permissions.")
    elif "401" in error_message:  # Unauthorized
        print("Unauthorized. Check your API credentials.")
    elif "500" in error_message or "502" in error_message or "503" in error_message:  # Server errors
        print(f"Server error. Will retry. Error: {error_message}")
        time.sleep(1)  # Wait a bit before retrying
    elif "400" in error_message:  # Bad request
        print(f"Bad request: {error_message}")
        # Don't exit, some 400 errors can be recovered from
    else:
        print(f"Unknown error: {error_message}")

# Intercept API calls by adding a print statement to the place_limit_order function
# Create a filtered stderr class to suppress HTTP error messages
class FilteredStderr:
    def __init__(self, real_stderr):
        self.real_stderr = real_stderr
        self.show_http_errors = SHOW_HTTP_ERRORS
    
    def write(self, message):
        # Filter out HTTP error messages if configured
        if not self.show_http_errors and "HTTP Error" in message and "429" in message:
            return  # Silently drop the message
        # Otherwise, write to the real stderr
        self.real_stderr.write(message)
    
    def flush(self):
        self.real_stderr.flush()
    
    # Ensure other attributes are passed through
    def __getattr__(self, name):
        return getattr(self.real_stderr, name)

# Apply the stderr filter if configured
if not SHOW_HTTP_ERRORS:
    sys.stderr = FilteredStderr(sys.stderr)

def place_limit_order(order_type, product_id, base_size, price):
    """Place a limit order with the Coinbase Advanced API"""
    client_order_id = get_unique_client_order_id()
    
    # Return the direct response from API without try/except
    if debug:
        print(f"Placing {order_type} order for {product_id} with base size {base_size} and price {price}")
    
    # Capture stderr during API calls if configured
    if not SHOW_HTTP_ERRORS:
        # Use stderr redirection to capture any HTTP errors
        f = io.StringIO()
        with redirect_stderr(f):
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
    else:
        # Normal flow without stderr capture
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

# Calculate price levels between bid and ask
def calculate_price_levels(bid_price, ask_price, tick_size, precision):
    """Calculate price levels between bid and ask with the given tick size"""
    price_levels = []
    current_price = bid_price + Decimal(tick_size)
    
    while current_price < ask_price:
        price_levels.append(current_price)
        current_price += Decimal(tick_size)
        
    return price_levels

# Format price for API
def format_price_for_order(price, precision):
    """Format price with proper precision for order placement"""
    return format_with_precision(price, precision)

# Main orderbook scanning and spread filling function
def scan_and_fill_spread():
    """Continuously scan orderbook and fill spread gaps with orders"""
    global order_count
    
    # Get product information to determine appropriate precision
    product_info = get_product_info(product_id)
    decimals = determine_precision(product_info)
    
    # Get base increment from products.json
    base_increment_value = get_base_increment_for_pair(product_id)
    
    if base_increment_value is None:
        error_msg = f"Unable to get base_increment for {product_id} from products.json"
        log(error_msg)
        if STOP_ON_BASE_AMOUNT_ERROR:
            log("STOP_ON_BASE_AMOUNT_ERROR is True. Stopping script.")
            wait_for_user()
            sys.exit(1)
        else:
            log("STOP_ON_BASE_AMOUNT_ERROR is False. Using configured FLOOD_BASE_AMOUNT.")
            base_increment_value = FLOOD_BASE_AMOUNT
    
    # Get product increments using the old method as fallback for quote_increment
    product_list = fetch_product_list(client)
    _, quote_increment = get_increments_from_list(product_list, product_id)
    
    if not quote_increment:
        log(f"Couldn't fetch quote_increment for {product_id}. Exiting.")
        wait_for_user()
        sys.exit(1)
        
    # Convert increments to Decimal
    base_increment = Decimal(str(base_increment_value))
    quote_increment = Decimal(quote_increment)
    
    # Convert user-specified floats to Decimal
    main_sell_price = Decimal(str(MAIN_SELL_PRICE))
    main_buy_price = Decimal(str(MAIN_BUY_PRICE))
    main_base_amount = Decimal(str(MAIN_BASE_AMOUNT))
    
    # Format for API
    main_sell_price_str = format_price_for_order(main_sell_price, decimals)
    main_buy_price_str = format_price_for_order(main_buy_price, decimals)
    
    # Determine flood base amount based on FORCE_FLOOD_BASE_INCREMENT setting
    if FORCE_FLOOD_BASE_INCREMENT:
        flood_base_amount = base_increment
        log(f"Using base_increment for flood orders: {flood_base_amount}")
    else:
        flood_base_amount = Decimal(str(FLOOD_BASE_AMOUNT))
        log(f"Using configured FLOOD_BASE_AMOUNT: {flood_base_amount}")
        
        # Validate that the configured amount meets minimum requirements
        if flood_base_amount < base_increment:
            error_msg = f"FLOOD_BASE_AMOUNT ({flood_base_amount}) is smaller than base_increment ({base_increment}) for {product_id}"
            log(error_msg)
            if STOP_ON_BASE_AMOUNT_ERROR:
                log("STOP_ON_BASE_AMOUNT_ERROR is True. Stopping script.")
                wait_for_user()
                sys.exit(1)
            else:
                log("STOP_ON_BASE_AMOUNT_ERROR is False. Using base_increment instead.")
                flood_base_amount = base_increment
    
    # Format base amounts for API - determine proper decimal places for base_increment
    # Handle scientific notation properly
    base_increment_str = f"{base_increment:.12f}".rstrip('0').rstrip('.')
    if '.' in base_increment_str:
        base_decimals = len(base_increment_str.split('.')[-1])
    else:
        base_decimals = 0
    
    # Ensure we have enough precision for very small amounts like BTC (0.00000001)
    base_decimals = max(base_decimals, 8)  # At least 8 decimal places for crypto
    
    flood_base_amount_str = f"{flood_base_amount:.{base_decimals}f}".rstrip('0').rstrip('.')
    main_base_amount_str = f"{main_base_amount:.{base_decimals}f}".rstrip('0').rstrip('.')
    
    # Display config info
    symbol = product_id.split('-')[0]
    log(f"Coinbase Orderbook Spread-Filling Flooder")
    log(f"=============================================")
    log(f"Trading Pair: {product_id}")
    log(f"Scan Interval: {SCAN_INTERVAL} second(s)")
    log(f"Fill Spread: {'Enabled' if FILL_SPREAD else 'Disabled'}")
    log(f"Spread Order Delay: {SPREAD_ORDER_DELAY} second(s)")
    log(f"Precision: {decimals} decimals")
    log(f"Tick Size: {quote_increment}")
    log(f"Main Buy Price: {main_buy_price_str}")
    log(f"Main Sell Price: {main_sell_price_str}")
    log(f"Flood Base Amount: {flood_base_amount_str}")
    log(f"=============================================")
    log(f"Press Ctrl+C to exit")
    log("=============================================")
    
    try:
        # Track the time of the last orderbook scan
        last_scan_time = 0
        
        # Store orderbook data
        top_bid = None
        top_ask = None
        spread = None
        price_levels = []
        
        while True:
            current_time = time.time()
            
            # Check if it's time to scan orderbook (every SCAN_INTERVAL seconds)
            if current_time - last_scan_time >= SCAN_INTERVAL:
                try:
                    # Get the orderbook
                    orderbook = get_orderbook(product_id, level=1)
                    if not orderbook or "bids" not in orderbook or "asks" not in orderbook:
                        log(f"Error fetching orderbook for {product_id}")
                    else:    
                        bids = orderbook["bids"]
                        asks = orderbook["asks"]
                        
                        if not bids or not asks:
                            log(f"Empty orderbook for {product_id}")
                        else:
                            # Get the top bid and ask
                            top_bid = Decimal(bids[0][0])
                            top_ask = Decimal(asks[0][0])
                            
                            # Calculate spread
                            spread = top_ask - top_bid
                            spread_pct = (spread / top_bid) * 100
                            
                            # Format values for display
                            bid_str = format_with_precision(top_bid, decimals)
                            ask_str = format_with_precision(top_ask, decimals)
                            spread_str = f"{format_with_precision(spread, decimals)} ({format_with_precision(spread_pct, 2)}%)"
                            
                            # Get current timestamp for display
                            display_time = datetime.datetime.now().strftime('%H:%M:%S')
                            
                            # Display the data
                            if SHOW_SPREAD_INFO:
                                log(f"{display_time:^20} | {bid_str:^12} | {ask_str:^12} | {spread_str:^12}")
                            
                            # Determine if we should fill spread based on settings
                            should_fill_spread = FILL_SPREAD
                            
                            # If both buying and selling are enabled and FILL_BUYSELL_DISABLE is True,
                            # override FILL_SPREAD to False to prevent orders from canceling each other
                            if ENABLE_BUYING and ENABLE_SELLING and FILL_BUYSELL_DISABLE:
                                should_fill_spread = False
                                if debug:
                                    log("Spread filling disabled because both buying and selling are enabled (FILL_BUYSELL_DISABLE=True)")
                            
                            # If fill spread is enabled and there's a spread larger than one tick
                            if should_fill_spread and spread > quote_increment:
                                # Calculate price levels to fill
                                price_levels = calculate_price_levels(top_bid, top_ask, quote_increment, decimals)
                                original_level_count = len(price_levels)
                                if SHOW_SPREAD_INFO:
                                    log(f"Spread detected with {original_level_count} price levels to fill")
                                
                                # Place spread filling orders - alternating buy/sell to fill spread
                                spread_mid = (top_bid + top_ask) / 2  # Middle of the spread
                                
                                # Initialize price_levels_with_type
                                price_levels_with_type = []
                                
                                # Limit price levels to MAX_SPREAD_ORDERS if needed
                                if len(price_levels) > MAX_SPREAD_ORDERS:
                                    # For buy orders: we want the highest price levels just below the ask
                                    # For sell orders: we want the lowest price levels just above the bid
                                    buy_levels = []
                                    sell_levels = []
                                    
                                    # The calculated price levels are already between bid and ask (exclusive)
                                    # For buy side: get all price levels (they're all below ask)
                                    buy_levels = price_levels.copy()
                                    # For sell side: get all price levels (they're all above bid)
                                    sell_levels = price_levels.copy()
                                    
                                    # Sort buy levels in descending order (highest first) to get closest to ask
                                    buy_levels.sort(reverse=True)
                                    # Sort sell levels in ascending order (lowest first) to get closest to bid
                                    sell_levels.sort()
                                    
                                    # Debug sorting
                                    if debug:
                                        log(f"Top ask: {top_ask}, Top bid: {top_bid}, Mid: {spread_mid}")
                                        if buy_levels:
                                            log(f"Buy levels (sorted by closeness to ask): {[format_price_for_order(p, decimals) for p in buy_levels[:5]]}")
                                        if sell_levels:
                                            log(f"Sell levels (sorted by closeness to bid): {[format_price_for_order(p, decimals) for p in sell_levels[:5]]}")
                                    
                                    # Account for enabled/disabled buying and selling
                                    if not ENABLE_BUYING:
                                        buy_levels = []
                                    if not ENABLE_SELLING:
                                        sell_levels = []
                                    
                                    # Distribute MAX_SPREAD_ORDERS based on what's enabled
                                    if ENABLE_BUYING and ENABLE_SELLING:
                                        # Both enabled - split between them
                                        buy_count = min(len(buy_levels), MAX_SPREAD_ORDERS // 2 + MAX_SPREAD_ORDERS % 2)  # Slightly more on buy side if odd
                                        sell_count = min(len(sell_levels), MAX_SPREAD_ORDERS // 2)
                                        
                                        # Redistribute if one side doesn't use its full allocation
                                        if buy_count < MAX_SPREAD_ORDERS // 2 + MAX_SPREAD_ORDERS % 2:
                                            sell_count = min(len(sell_levels), MAX_SPREAD_ORDERS - buy_count)
                                        elif sell_count < MAX_SPREAD_ORDERS // 2:
                                            buy_count = min(len(buy_levels), MAX_SPREAD_ORDERS - sell_count)
                                    elif ENABLE_BUYING:
                                        # Only buying enabled - use all slots for buy
                                        buy_count = min(len(buy_levels), MAX_SPREAD_ORDERS)
                                        sell_count = 0
                                    elif ENABLE_SELLING:
                                        # Only selling enabled - use all slots for sell
                                        buy_count = 0
                                        sell_count = min(len(sell_levels), MAX_SPREAD_ORDERS)
                                    else:
                                        # Neither enabled - shouldn't reach here, but just in case
                                        buy_count = 0
                                        sell_count = 0
                                        
                                    # Create a list of (price, order_type) tuples so we know which prices were buy vs sell
                                    price_levels_with_type = [(price, "buy") for price in buy_levels[:buy_count]] + \
                                                             [(price, "sell") for price in sell_levels[:sell_count]]
                                    
                                    # For logging, just show prices without order types
                                    price_levels = [price for price, _ in price_levels_with_type]
                                    if SHOW_SPREAD_INFO:
                                        log(f"Limited to {len(price_levels)} price levels due to MAX_SPREAD_ORDERS={MAX_SPREAD_ORDERS} (Buy: {buy_count}, Sell: {sell_count})")
                                else:
                                    # Use all price levels, determine buy/sell based on position relative to spread mid
                                    price_levels_with_type = []
                                    for price in price_levels:
                                        if ENABLE_BUYING and ENABLE_SELLING:
                                            # Alternate between buy and sell orders based on price position
                                            if price < spread_mid:
                                                price_levels_with_type.append((price, "buy"))
                                            else:
                                                price_levels_with_type.append((price, "sell"))
                                        elif ENABLE_BUYING:
                                            price_levels_with_type.append((price, "buy"))
                                        elif ENABLE_SELLING:
                                            price_levels_with_type.append((price, "sell"))
                                
                                # Debug output to confirm price levels
                                if debug:
                                    log(f"Price levels to fill: {[format_price_for_order(price, decimals) for price in price_levels]}")
                                
                                # Place spread filling orders - alternating buy/sell to fill spread
                                spread_mid = (top_bid + top_ask) / 2  # Middle of the spread
                                
                                # Use a dynamic sleep duration that can be increased if rate limiting occurs
                                current_sleep_duration = SLEEP_DURATION
                                rate_limited = False
                                
                                for price, order_type in price_levels_with_type:
                                    price_str = format_price_for_order(price, decimals)
                                    
                                    # Skip based on enabled buying/selling
                                    if order_type == "buy":
                                        if not ENABLE_BUYING:
                                            if debug:
                                                log(f"Skipping buy order at {price_str} (buying disabled)")
                                            continue
                                    else:  # order_type == "sell"
                                        if not ENABLE_SELLING:
                                            if debug:
                                                log(f"Skipping sell order at {price_str} (selling disabled)")
                                            continue
                                    
                                    if debug:
                                        log(f"Placing {order_type} order at {price_str} to fill spread")
                                    
                                    # If we previously hit rate limits, use a longer sleep before next order
                                    if rate_limited:
                                        time.sleep(max(current_sleep_duration * 2, 0.5))  # Double sleep time with minimum 0.5s
                                        rate_limited = False  # Reset flag
                                    
                                    # Place the order
                                    order = place_limit_order(order_type, product_id, flood_base_amount_str, price_str)
                                    error_result = handle_order_error(order, f"Spread {order_type.capitalize()}")
                                    
                                    # Check for different error types
                                    if error_result == True:  # True is returned when rate limit is hit
                                        rate_limited = True
                                        continue  # Skip logging this order as it wasn't placed
                                    elif error_result in ["insufficient_funds", "size_error", "other_error"]:
                                        # Do not increment order count for failed orders
                                        continue  # Skip logging this order as it wasn't placed successfully
                                    
                                    # Only increment counter and log if order was successful
                                    order_count += 1
                                    symbol = product_id.split('-')[0]  # Extract symbol without -USD
                                    log(f"{get_timestamp()}{symbol} - #{order_count} - {price_str} - Spread {order_type.capitalize()}")
                                    
                                    # Use spread order delay between orders when no rate limiting
                                    time.sleep(SPREAD_ORDER_DELAY)
                    
                    # Update the last scan time
                    last_scan_time = current_time
                    
                except Exception as e:
                    log(f"Error during orderbook scan: {str(e)}")
            
            # Place regular flood orders regardless of spread (this runs every loop iteration)
            try:
                # Main Buy Wall
                if USE_MAIN_WALLS and ENABLE_BUYING:
                    main_buy_order = place_limit_order("buy", product_id, main_base_amount_str, main_buy_price_str)
                    error_result = handle_order_error(main_buy_order, "Main Buy")
                    if not error_result:  # Only proceed if no error
                        order_count += 1
                        symbol = product_id.split('-')[0]  # Extract symbol without -USD
                        log(f"{get_timestamp()}{symbol} - #{order_count} - {main_buy_price_str} - Main Buy")
                        time.sleep(SLEEP_DURATION)

                # Flood Buy - ALWAYS run this at SLEEP_DURATION interval
                if USE_FLOOD_SPAM and ENABLE_BUYING:
                    # Calculate flood buy price (one tick below main sell price)
                    flood_buy_price = main_sell_price - quote_increment
                    flood_buy_price_str = format_price_for_order(flood_buy_price, decimals)
                    
                    flood_buy_order = place_limit_order("buy", product_id, flood_base_amount_str, flood_buy_price_str)
                    error_result = handle_order_error(flood_buy_order, "Flood Buy")
                    if not error_result:  # Only proceed if no error
                        order_count += 1
                        symbol = product_id.split('-')[0]  # Extract symbol without -USD
                        log(f"{get_timestamp()}{symbol} - #{order_count} - {flood_buy_price_str} - Flood Buy")
                        time.sleep(SLEEP_DURATION)

                # Main Sell Wall
                if USE_MAIN_WALLS and ENABLE_SELLING:
                    main_sell_order = place_limit_order("sell", product_id, main_base_amount_str, main_sell_price_str)
                    error_result = handle_order_error(main_sell_order, "Main Sell")
                    if not error_result:  # Only proceed if no error
                        order_count += 1
                        symbol = product_id.split('-')[0]  # Extract symbol without -USD
                        log(f"{get_timestamp()}{symbol} - #{order_count} - {main_sell_price_str} - Main Sell")
                        time.sleep(SLEEP_DURATION)

                # Flood Sell
                if USE_FLOOD_SPAM and ENABLE_SELLING:
                    # Calculate flood sell price (one tick above main buy price)
                    flood_sell_price = main_buy_price + quote_increment
                    flood_sell_price_str = format_price_for_order(flood_sell_price, decimals)
                    
                    flood_sell_order = place_limit_order("sell", product_id, flood_base_amount_str, flood_sell_price_str)
                    error_result = handle_order_error(flood_sell_order, "Flood Sell")
                    if not error_result:  # Only proceed if no error
                        order_count += 1
                        symbol = product_id.split('-')[0]  # Extract symbol without -USD
                        log(f"{get_timestamp()}{symbol} - #{order_count} - {flood_sell_price_str} - Flood Sell")
                        time.sleep(SLEEP_DURATION)
                    
            except Exception as e:
                error_message = str(e)
                # Handle known HTTP error codes
                if any(code in error_message for code in ["429", "403", "400", "401", "500", "502", "503"]):
                    handle_specific_errors(error_message)
                else:
                    log(f"Order error: {error_message}")
                    
                # Brief pause to avoid hammering the API in case of errors
                time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        wait_for_user()

# Main function
def main():
    global order_count
    order_count = 0

    # Log suppression already applied at startup

    if not USE_MAIN_WALLS and not USE_FLOOD_SPAM:
        log("You need to enable Main Walls or Flood Spam to start the script.")
        wait_for_user()
        sys.exit(1)

    if not ENABLE_BUYING and not ENABLE_SELLING:
        log("You need to enable buying or selling to start. Stopping the script.")
        wait_for_user()
        sys.exit(1)

    scan_and_fill_spread()

if __name__ == "__main__":
    main()
