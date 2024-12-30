# Kirby Christmas Lights Buy/Sell Limit Order Flooder (v0.07) for Coinbase Advanced

This script automates the process of placing buy/sell limit orders on Coinbase using **Coinbase’s current (non-legacy) API keys**, simulating a dynamic trading pattern that can incorporate both Main Walls and a Flood Spam of smaller orders.

**Tested on Python 3.12** for maximum compatibility and performance.

---

## Features

1. **Main Walls and Flood Spam**  
   - **Main Walls**: Place large, static buy or sell orders at your defined boundaries.  
   - **Flood Spam**: Rapidly places a series of smaller orders just inside the main walls to create additional liquidity.

2. **User-Configurable**  
   - Toggle buying, selling, or both.  
   - Stop on insufficient funds or continue anyway.  
   - Adjust base amount/increment thresholds with ease.

3. **Decimal Precision Handling**  
   - Automatically adapts to the correct quote increment and base increment for your chosen `product_id`.  
   - Option to stop the script if the base amount is too small or to ignore and keep running.

4. **Debug Mode**  
   - Toggle `debug = True` for detailed console outputs regarding order placement and error handling.

---

## Installation Requirements

1. **Python 3.12**  
   Make sure you have Python **3.12** installed (earlier Python 3 versions may still work, but v3.12 is recommended).

2. **Libraries**  
   - `coinbase`  
   - `coinbase-advanced-py`  
   - `python-dotenv`  

(These provide API interaction with Coinbase Advanced and environment variable loading.)

---

## How to Install and Run

1. **Clone the Repository**  
   - Example:
     
         git clone https://github.com/xa-io/kirby-coinbase-flooder.git
         cd kirby-coinbase-flooder

2. **Install Dependencies**  
   - Example:
     
         pip install python-dotenv coinbase coinbase-advanced-py

3. **Create a `.env` File**  
   In the root directory, create a file named `.env` containing your **current** (non-legacy) Coinbase API key and secret:
   
       COINBASE_API_KEY=organizations/xxxxxxxxxxxxxxxxxx/apiKeys/xxxxxxxxxxxxxxxxxx
       COINBASE_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

   Retrieve these from your [Coinbase API Settings](https://www.coinbase.com/settings/api). Make sure you have appropriate permissions for placing trades.

4. **Run the Script**  
   - Example:
     
         python kirby-coinbase-flooder.py

---

## Configuration

Open the script and look for the following **configuration parameters** at the top:

### Global Configuration

- `sleep_duration = 0.2`  
  Delay (in seconds) between each order placement. Less than 0.2 may skip orders.  
- `rate_limit_delay = 0`  
  Number of seconds to wait if a rate-limit error occurs.  
- `debug = False`  
  Set to `True` for verbose output.

### Funds Management

- `show_insufficient_funds = True`  
  Toggle to display an insufficient funds message.  
- `stop_on_insufficient_funds = False`  
  If `True`, the script stops on insufficient funds.

### Base Amount & Precision

- `stop_on_base_amount_error = True`  
  If `True`, the script stops on a base-size or increment error.

### Trade Flow

- `enable_buying = True`  
  If `False`, no buy orders are placed.  
- `enable_selling = True`  
  If `False`, no sell orders are placed.

### Strategies

- `use_main_walls = False`  
  Set to `True` to place large orders at `main_buy_price` and `main_sell_price`.  
- `use_flood_spam = True`  
  Set to `True` to place smaller “flood” orders just inside your main walls.

### Prices & Amounts

- `product_id = "BTC-USD"`  
- `main_sell_price = 100000`  
- `main_buy_price = 85000`  
- `flood_base_amount = 0.00001`  
- `main_base_amount = 1`

After adjusting these values as needed, run the script again.

---

## Example Flow

When both `use_main_walls` **and** `use_flood_spam` are enabled:

1. Places a **Main Buy** at `main_buy_price`.  
2. Places a **Flood Buy** slightly below `main_sell_price`.  
3. Places a **Main Sell** at `main_sell_price`.  
4. Places a **Flood Sell** slightly above `main_buy_price`.  
5. Repeats this cycle continuously.

---

## Consider a Donation

If you’ve found this script useful and end up buying a Lambo:

- **BTC**: `bc1qwjy0hl4z9c930kgy4nud2fp0nw8m6hzknvumgg`  
- **ETH**: `0x0941D41Cd0Ee81bd79Dbe34840bB5999C124D3F0`  
- **SOL**: `4cpdbmmp1hyTAstA3iUYdFbqeNBwjFmhQLfL5bMgf77z`

**Thank you for your support!**
