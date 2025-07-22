# Kirby Christmas Lights Buy/Sell Limit Order Flooder for Coinbase Advanced

This script automates the process of placing buy/sell limit orders on Coinbase Advanced, simulating a vibrant trading pattern similar to the twinkling lights of a Christmas tree. It was created as a fun project to experiment with trading automation while also pushing the limits of market order flooding.

## Features

1. **Limit Orders**: Automatically places buy/sell limit orders instead of market orders, which may not always be available in newer markets.
2. **Normal and Waves Strategies**: Choose between a fixed base size (`Normal`) or varying wave sizes (`Waves`) for order placement.
    - **Normal**: Executes buy/sell orders with a specified base amount.
    - **Waves**: Executes orders in a sequence of increasing and then decreasing sizes (e.g., `1x, 3x, 5x, 7x, 5x, 3x`).
3. **Staggered Orders**: Implements staggered order placement with incremented prices to mimic market depth and liquidity.
4. **force_base_amount**: If enabled, forces the script to use a specific base amount for all orders instead of calculating it dynamically.
5. **Debug Mode**: Toggle detailed debug information to monitor script behavior.

## Installation Requirements

1. **Python 3.8+**: Ensure you have Python 3.8 or higher installed.
2. **Libraries**:
    - `coinbase`: For interacting with the Coinbase API.
    - `python-dotenv`: Used for loading environment variables from a `.env` file.

## How to Install and Run

1. **Clone the Repository**:
    ```bash
    git clone https://github.com/yourusername/kirby-christmas-lights.git
    cd kirby-christmas-lights
    ```
2. **Install Dependencies**:
    ```bash
    pip install python-dotenv coinbase coinbase-advanced-py
    ```
3. **Create a `.env` File**:
    Create a `.env` file in the root directory with your Coinbase API key and secret:
    ```
    COINBASE_API_KEY=organizations/xxxxxxxxxxxxxxxxxx/apiKeys/xxxxxxxxxxxxxxxxxx
    COINBASE_API_SECRET=-----BEGIN EC PRIVATE KEY-----\nxxxxxxxxxxxxxxxxxx\nxxxxxxxxxxxxxxxxxx\nxxxxxxxxxxxxxxxxxx\n-----END EC PRIVATE KEY-----\n
    ```
    - Ensure your API keys are from the [Coinbase Legacy API Settings](https://www.coinbase.com/settings/legacy_api).
4. **Run the Script**:
    ```bash
    python kirby_lights.py
    ```

## Configuration

- **Global Settings**:
  - `sleep_duration`: Delay between placing each order, measured in seconds. Default is `0.25`.
  - `rate_limit_delay`: Wait time in seconds when a rate limit is exceeded. Default is `10`.
  - `debug`: Toggle for debugging mode. Default is `False`.
  - `stop_on_insufficient_funds`: Stops the script if insufficient funds are detected. Default is `True`.
  
- **Buying/Selling**:
  - `enable_buying`: Enables or disables placing buy orders. Default is `True`.
  - `enable_selling`: Enables or disables placing sell orders. Default is `False`.

- **Strategies**:
  - `enable_waves`: Enables the wave strategy. Default is `False`.
  - `enable_normal`: Enables the normal strategy. Default is `True`.

- **Staggered Orders**:
  - `enable_staggered`: Enables staggered order placement. Default is `False`.
  - `staggered_amount`: The number of staggered orders to place. Default is `10`.

- **Example Configuration for Multiple Trading Pairs**:
  ```python
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


## Consider a donation after you buy your lambo.

BTC: `bc1qwjy0hl4z9c930kgy4nud2fp0nw8m6hzknvumgg`

ETH: `0x0941D41Cd0Ee81bd79Dbe34840bB5999C124D3F0`

SOL: `4cpdbmmp1hyTAstA3iUYdFbqeNBwjFmhQLfL5bMgf77z`
