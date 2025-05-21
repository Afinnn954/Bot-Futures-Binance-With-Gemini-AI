

import time
import json
import logging
import threading
import random
import requests
import hmac
import hashlib
import urllib.parse
import queue
import asyncio
import numpy as np
import pandas as pd
# Import pandas_ta instead of talib
import pandas_ta as ta
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup,  constants
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======== BOT CONFIGURATION ========
# Replace these values with your own
TELEGRAM_BOT_TOKEN = "6125615649:AAEQRhR9OQAuPXEZT_bSHyOJ1icQ4LhfiZE"  # Replace with your bot token
ADMIN_USER_IDS = [1202425609]    # Replace with your Telegram user ID(s)
# ==================================

# Binance API configuration
# !!! CRITICAL !!! For API Error {"code":-2015,"msg":"Invalid API-key, IP, or permissions for action"}:
# 1. VERIFY API KEY & SECRET: Ensure they are copied correctly from Binance.
# 2. API PERMISSIONS:
#    - MUST have "Enable Reading".
#    - MUST have "Enable Futures".
#    - For actual trading, "Enable Spot & Margin Trading" might be needed if leveraged tokens or other instruments are involved,
#      but for pure futures, "Enable Futures" + general trading permissions are key.
#    - NEVER enable "Enable Withdrawals" for a bot API key.
# 3. IP ACCESS RESTRICTIONS:
#    - If you have IP whitelisting enabled on Binance for this API key,
#      the IP address of the server/machine RUNNING THIS BOT MUST be added to the whitelist.
#    - If your bot's IP is dynamic, consider using a static IP or disabling IP restrictions (less secure).
# 4. TESTNET vs. MAINNET:
#    - Ensure you are using Testnet API keys if CONFIG["use_testnet"] = True.
#    - Ensure you are using Mainnet API keys if CONFIG["use_testnet"] = False.
#    - They are different sets of keys.
BINANCE_API_KEY = "And1Vi17pnDNSrNrEXi8MIAW384JV66CIYq3mW46SFkpaTDi1iDiO67UTfSVEZP1"  # Your Binance API key
BINANCE_API_SECRET = "PDTavTkCR4KR3Lm7PTPj5einLHvUXCV9k7pBdTyPc2Uxinr5TTyYUclpS7860pip" 
BINANCE_API_URL = "https://fapi.binance.com"  # Futures API URL


# Trading modes
TRADING_MODES = {
    "safe": {
        "leverage": 5,
        "take_profit": 0.6,  # 0.6% take profit
        "stop_loss": 0.95,    # 0.95% stop loss - User had 0.95, assuming this might be a typo for 0.3 or 0.45 for safety. Keeping 0.95 as per original.
        "position_size_percent": 10,  # 10% of available balance
        "max_daily_trades": 10,
        "description": "Safe mode with lower risk and conservative profit targets"
    },
    "standard": {
        "leverage": 10,
        "take_profit": 1.0,  # 1.0% take profit
        "stop_loss": 0.5,    # 0.5% stop loss
        "position_size_percent": 15,  # 15% of available balance
        "max_daily_trades": 15,
        "description": "Standard mode with balanced risk and profit targets"
    },
    "aggressive": {
        "leverage": 20,
        "take_profit": 1.5,  # 1.5% take profit
        "stop_loss": 0.7,    # 0.7% stop loss
        "position_size_percent": 20,  # 20% of available balance
        "max_daily_trades": 20,
        "description": "Aggressive mode with higher risk and profit targets"
    }
}

# Technical indicator settings
INDICATOR_SETTINGS = {
    # Parameter RSI
    "rsi_period": 14,
    "rsi_oversold": 35,
    "rsi_overbought": 65,

    # Parameter EMA
    "ema_short_period": 12,
    "ema_long_period": 26,

    # Parameter Bollinger Bands
    "bb_period": 20,
    "bb_std": 2.0,

    # Pengaturan Sinyal & Timeframe
    "candle_timeframe": "5m",
    "signal_strength_threshold": 25,
    "klines_limit_for_indicator_calc": 150
}

# --- Konfigurasi Utama Bot (`CONFIG`) ---
CONFIG = {
    "api_key": BINANCE_API_KEY,
    "api_secret": BINANCE_API_SECRET,
    "trading_enabled_on_start": False,
    "trading_mode": "standard",
    # "use_testnet": True,  # <For now Testnet is not running 
    "use_real_trading": True, # <<< CHANGE TO TRUE TO EXECUTE REAL ORDERS

    "static_trading_pairs": ["BTCUSDT", "ETHUSDT"],
    "dynamic_pair_selection": True,
    "dynamic_watchlist_symbols": [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", 
        "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT", "TRXUSDT", "LTCUSDT", "UNIUSDT",
        "ATOMUSDT", "ETCUSDT", "BCHUSDT", "XLMUSDT", "NEARUSDT", "ALGOUSDT", "VETUSDT",
        "FTMUSDT", "MANAUSDT", "SANDUSDT", "APEUSDT", "AXSUSDT", "FILUSDT", "ICPUSDT",
        "AAVEUSDT", "MKRUSDT", "COMPUSDT", "GRTUSDT", "RUNEUSDT", "THETAUSDT", "EGLDUSDT",
    ],
    "max_active_dynamic_pairs": 3,
    "min_24h_volume_usdt_for_scan": 10000000,
    "dynamic_scan_interval_seconds": 300,
    "api_call_delay_seconds_in_scan": 0.3, # Corrected key name usage later

    "leverage": 10,
    "take_profit": 1.0,
    "stop_loss": 0.5,
    "position_size_percentage": 10.0, # Will be overridden by trading_mode
    "max_daily_trades": 15, # Will be overridden by trading_mode

    "use_percentage_for_pos_size": True,
    # "position_size_percentage": 10.0, # Already defined above, covered by trading_mode
    "fixed_position_size_usdt": 100,

    "daily_profit_target_percentage": 5.0,
    "daily_loss_limit_percentage": 3.0,
    
    "signal_check_interval_seconds": 30,
    "post_trade_entry_delay_seconds": 5,
    
    "hedge_mode_enabled": True, # If True, bot will try to set Hedge Mode on Binance

    # --- Conceptual AI Integration (Gemini) ---
    # "GEMINI_API_KEY": "", # Add your Gemini API key here if you implement this
    # "use_ai_strategy": False, # Enable this to use the AI strategy component
    # "ai_signal_strength_boost": 25, # How much strength AI can add
    # "ai_override_threshold": 50, # If AI signal strength is above this, it might override TA
}

# --- Variabel Global untuk State Bot ---
# Ideally, these would be instance variables of TradingBot for better encapsulation.
ACTIVE_TRADES = []
COMPLETED_TRADES = []
DAILY_STATS = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "total_trades": 0,
    "winning_trades": 0,
    "losing_trades": 0,
    "total_profit_percentage_leveraged": 0.0,
    "total_profit_usdt": 0.0,
    "starting_balance_usdt": 0.0,
    "current_balance_usdt": 0.0,
    "roi_percentage": 0.0
}

# Cache for symbol information from exchangeInfo
SYMBOL_INFO = {} # FIXED: Renamed from SYMBOL_INFO_CACHE to SYMBOL_INFO

class BinanceFuturesAPI:
    def __init__(self, config):
        self.config = config
        self.api_key = config["api_key"]
        self.api_secret = config["api_secret"]
        self.base_url = BINANCE_API_URL

    def _generate_signature(self, data):
        query_string = urllib.parse.urlencode(data)
        return hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    def _get_headers(self):
        return {'X-MBX-APIKEY': self.api_key}

    def get_exchange_info(self):
        try:
            url = f"{self.base_url}/fapi/v1/exchangeInfo"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting exchange info: {e}")
            return None

    def get_account_info(self):
        try:
            url = f"{self.base_url}/fapi/v2/account"
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            params['signature'] = self._generate_signature(params)
            headers = self._get_headers()
            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API error response for get_account_info: {response.status_code} - {response.text}")
                if response.status_code == 401: # Unauthorized
                    logger.error("Authentication failed (401): Invalid API key or secret, or general auth issue. Check Binance key permissions and IP whitelist.")
                elif response.status_code == 403: # Forbidden
                    logger.error("Forbidden (403): API key may lack necessary permissions (e.g., for Futures). Check Binance key permissions.")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"RequestException getting account info: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting account info: {e}")
            return None


    def get_ticker_price(self, symbol):
        try:
            url = f"{self.base_url}/fapi/v1/ticker/price"
            params = {'symbol': symbol}
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            return float(response.json()['price'])
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get ticker price for {symbol}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing ticker price for {symbol}: {e}")
            return None

    def get_klines(self, symbol, interval, limit=100):
        try:
            url = f"{self.base_url}/fapi/v1/klines"
            params = {'symbol': symbol, 'interval': interval, 'limit': limit}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                            'close_time', 'quote_asset_volume', 'number_of_trades', 
                                            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True) # Drop rows with NaN in essential columns
            return df
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get klines for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing klines for {symbol}: {e}")
            return None

    # MOVED get_ticker_24hr HERE
    def get_ticker_24hr(self, symbol: str = None) -> list | dict | None:
        """
        Get 24hr ticker price change statistics.
        """
        try:
            url = f"{self.base_url}/fapi/v1/ticker/24hr" # Uses self.base_url from BinanceFuturesAPI
            params = {}
            if symbol:
                params['symbol'] = symbol.upper()
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error fetching 24hr ticker: {http_err} - {response.text}")
            return None
        except requests.exceptions.RequestException as req_err:
            logger.error(f"RequestException fetching 24hr ticker: {req_err}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching 24hr ticker: {e}", exc_info=True)
            return None

    def change_leverage(self, symbol, leverage):
        try:
            url = f"{self.base_url}/fapi/v1/leverage"
            timestamp = int(time.time() * 1000)
            params = {'symbol': symbol, 'leverage': leverage, 'timestamp': timestamp}
            params['signature'] = self._generate_signature(params)
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Changed leverage for {symbol} to {leverage}x")
                return response.json()
            else:
                logger.error(f"Failed to change leverage for {symbol} to {leverage}x: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error changing leverage for {symbol}: {e}")
            return None

    def change_margin_type(self, symbol, margin_type):
        """Change margin type for a symbol (ISOLATED or CROSSED)"""
        try:
            url = f"{self.base_url}/fapi/v1/marginType"
            timestamp = int(time.time() * 1000)
            params = {
                'symbol': symbol,
                'marginType': margin_type.upper(),
                'timestamp': timestamp
            }
            params['signature'] = self._generate_signature(params)
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Changed margin type for {symbol} to {margin_type}")
                return response.json()
            # Code 4046 means "No need to change margin type"
            elif response.status_code == 400 and response.json().get("code") == -4046:
                 logger.info(f"Margin type for {symbol} is already {margin_type}.")
                 return response.json() # Or a custom success dict
            else:
                logger.error(f"Failed to change margin type for {symbol} to {margin_type}: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error changing margin type for {symbol}: {e}")
            return None


    def get_position_mode(self):
        try:
            url = f"{self.base_url}/fapi/v1/positionSide/dual"
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            params['signature'] = self._generate_signature(params)
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting position mode: {e}")
            return None

    def change_position_mode(self, dual_side_position: bool):
        try:
            url = f"{self.base_url}/fapi/v1/positionSide/dual"
            timestamp = int(time.time() * 1000)
            params = {
                'dualSidePosition': 'true' if dual_side_position else 'false',
                'timestamp': timestamp
            }
            params['signature'] = self._generate_signature(params)
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=10)
            
            if response.status_code == 200:
                mode = "Hedge Mode" if dual_side_position else "One-way Mode"
                logger.info(f"Successfully set position mode to {mode}. Response: {response.json().get('msg', 'OK')}")
                return response.json()
            # Binance returns 400 with code -4059 if already in the desired mode
            elif response.status_code == 400 and response.json().get("code") == -4059:
                mode = "Hedge Mode" if dual_side_position else "One-way Mode"
                logger.info(f"Position mode is already set to {mode}.")
                return {"code": 200, "msg": f"No need to change position side."} # Simulate success
            else:
                logger.error(f"Failed to change position mode: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error changing position mode: {e}")
            return None

    def create_order(self, symbol, side, order_type, quantity=None, price=None, 
                    stop_price=None, position_side=None, reduce_only=False, 
                    time_in_force="GTC", close_position=False):
        try:
            url = f"{self.base_url}/fapi/v1/order"
            timestamp = int(time.time() * 1000)
            params = {
                'symbol': symbol,
                'side': side.upper(),
                'type': order_type.upper(),
                'timestamp': timestamp
            }
            if order_type.upper() not in ['MARKET', 'STOP_MARKET', 'TAKE_PROFIT_MARKET']:
                params['timeInForce'] = time_in_force
            if quantity: params['quantity'] = quantity
            if price and order_type.upper() not in ['MARKET', 'STOP_MARKET', 'TAKE_PROFIT_MARKET']: params['price'] = price
            if stop_price and order_type.upper() in ['STOP', 'STOP_MARKET', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET']: params['stopPrice'] = stop_price
            if position_side: params['positionSide'] = position_side.upper()
            if reduce_only: params['reduceOnly'] = 'true'
            if close_position: params['closePosition'] = 'true' # This is for One-way mode to close position
            
            params['signature'] = self._generate_signature(params)
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Created order for {symbol}: {side} {order_type} Qty: {quantity} PosSide: {position_side}. Response: {response.json()['orderId']}")
                return response.json()
            else:
                logger.error(f"Failed to create order for {symbol} ({side} {order_type} Qty: {quantity}): {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating order for {symbol}: {e}")
            return None

    def get_open_positions(self):
        try:
            account_info = self.get_account_info()
            if account_info and 'positions' in account_info:
                open_positions = [p for p in account_info['positions'] if float(p.get('positionAmt', 0)) != 0]
                return open_positions
            elif account_info is None:
                 logger.warning("Could not get account info to fetch open positions (API call failed or auth error).")
            return []
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []

    def get_open_orders(self, symbol=None):
        try:
            url = f"{self.base_url}/fapi/v1/openOrders"
            timestamp = int(time.time() * 1000)
            params = {'timestamp': timestamp}
            if symbol: params['symbol'] = symbol
            params['signature'] = self._generate_signature(params)
            response = requests.get(url, params=params, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get open orders for {symbol if symbol else 'all'}: {e}")
            return None

    def cancel_order(self, symbol, order_id=None, orig_client_order_id=None):
        try:
            url = f"{self.base_url}/fapi/v1/order"
            timestamp = int(time.time() * 1000)
            params = {'symbol': symbol, 'timestamp': timestamp}
            if order_id: params['orderId'] = order_id
            elif orig_client_order_id: params['origClientOrderId'] = orig_client_order_id
            else:
                logger.error("cancel_order: Either orderId or origClientOrderId must be provided.")
                return None
            params['signature'] = self._generate_signature(params)
            response = requests.delete(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Canceled order {order_id or orig_client_order_id} for {symbol}.")
                return response.json()
            else:
                # Error code -2011 means "Unknown order sent." - could be already filled/canceled.
                if response.json().get("code") == -2011:
                    logger.warning(f"Order {order_id or orig_client_order_id} for {symbol} not found or already processed (cancel attempt).")
                    return response.json() # Still return response
                logger.error(f"Failed to cancel order {order_id or orig_client_order_id} for {symbol}: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error canceling order {order_id or orig_client_order_id} for {symbol}: {e}")
            return None

    def cancel_all_orders(self, symbol):
        try:
            url = f"{self.base_url}/fapi/v1/allOpenOrders"
            timestamp = int(time.time() * 1000)
            params = {'symbol': symbol, 'timestamp': timestamp}
            params['signature'] = self._generate_signature(params)
            response = requests.delete(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Canceled all open orders for {symbol}.")
                return response.json()
            else:
                logger.error(f"Failed to cancel all orders for {symbol}: {response.status_code} - {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error canceling all orders for {symbol}: {e}")
            return None
            
    def get_symbol_info(self, symbol):
        global SYMBOL_INFO # FIXED: uses the renamed global variable
        if symbol in SYMBOL_INFO:
            return SYMBOL_INFO[symbol]
        try:
            exchange_info = self.get_exchange_info()
            if not exchange_info: return None
            for sym_data in exchange_info.get('symbols', []):
                if sym_data['symbol'] == symbol:
                    s_info = {
                        'pricePrecision': sym_data['pricePrecision'],
                        'quantityPrecision': sym_data['quantityPrecision'],
                        'minQty': next((f['minQty'] for f in sym_data['filters'] if f['filterType'] == 'LOT_SIZE'), '0.001'),
                        'tickSize': next((f['tickSize'] for f in sym_data['filters'] if f['filterType'] == 'PRICE_FILTER'), '0.01'),
                        'minNotional': next((f['notional'] for f in sym_data['filters'] if f['filterType'] == 'MIN_NOTIONAL'), '5.0') # Min notional is usually > $1 for futures
                    }
                    SYMBOL_INFO[symbol] = s_info
                    return s_info
            logger.error(f"Symbol {symbol} not found in exchange info.")
            return None
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None

    def get_decimal_places(self, value_str: str) -> int:
        if '.' in value_str:
            return len(value_str.split('.')[1].rstrip('0')) #rstrip('0') to handle things like "0.0100" -> precision 2
        return 0
        
    def round_price(self, symbol: str, price: float) -> float:
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info or 'tickSize' not in symbol_info:
            return round(price, 2) # Fallback
        
        tick_size_str = symbol_info['tickSize']
        precision = self.get_decimal_places(tick_size_str)
        
        # Round to the nearest tick_size
        tick_size = float(tick_size_str)
        return round(round(price / tick_size) * tick_size, precision)

    def round_quantity(self, symbol: str, quantity: float) -> float:
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info or 'minQty' not in symbol_info: # minQty often dictates stepSize for quantity
            return round(quantity, 3) # Fallback
        
        # The quantityPrecision from API is number of decimal places.
        # Step size for LOT_SIZE filter usually dictates rounding.
        step_size_str = symbol_info.get('minQty') # Assuming minQty is the step_size for simplicity
        
        precision = self.get_decimal_places(step_size_str)

        # Round down to the nearest step_size
        step_size = float(step_size_str)
        if step_size == 0: return round(quantity, precision) # Avoid division by zero
        
        return round(np.floor(quantity / step_size) * step_size, precision)

    def get_balance(self):
        try:
            account_info = self.get_account_info()
            if account_info and 'assets' in account_info:
                for asset in account_info['assets']:
                    if asset['asset'] == 'USDT': # Or BUSD, depending on what is used
                        return {
                            'total': float(asset.get('walletBalance', 0)),
                            'available': float(asset.get('availableBalance', 0)), # crossWalletBalance / availableBalance
                            'unrealized_pnl': float(asset.get('unrealizedProfit', 0))
                        }
            elif account_info is None:
                logger.warning("Could not get account info for balance (API call failed or auth error).")
            return None
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None

# --- Conceptual AI Strategy Integration ---
# class AIStrategy:
#     def __init__(self, config):
#         self.gemini_api_key = config.get("GEMINI_API_KEY")
#         self.enabled = config.get("use_ai_strategy", False)
#         # Initialize Gemini client here if using a library (e.g., google.generativeai)
#         # import google.generativeai as genai
#         # if self.enabled and self.gemini_api_key:
#         #     genai.configure(api_key=self.gemini_api_key)
#         #     self.model = genai.GenerativeModel('gemini-pro') # Or your preferred model
#         # else:
#         #     self.model = None
#         logger.info(f"AI Strategy component initialized. Enabled: {self.enabled}, Key Set: {bool(self.gemini_api_key)}")


#     def get_ai_recommendation(self, symbol: str, timeframe: str, latest_indicators: pd.Series, klines_df_tail: pd.DataFrame = None):
#         if not self.enabled or not self.gemini_api_key: # or not self.model:
#             # logger.debug(f"[{symbol}] AI recommendation skipped (disabled or no API key/model).")
#             return None

#         try:
#             # Construct a detailed prompt for Gemini
#             prompt_parts = [
#                 f"Futures trading analysis for {symbol} on {timeframe} timeframe.",
#                 "Current market conditions based on technical indicators:",
#                 f"- Price: {latest_indicators['close']:.4f}",
#                 f"- RSI ({INDICATOR_SETTINGS['rsi_period']}): {latest_indicators['rsi']:.2f}",
#                 f"- EMA Short ({INDICATOR_SETTINGS['ema_short_period']}): {latest_indicators['ema_short']:.4f}",
#                 f"- EMA Long ({INDICATOR_SETTINGS['ema_long_period']}): {latest_indicators['ema_long']:.4f}",
#                 f"- Bollinger Lower: {latest_indicators['bb_lower']:.4f}, Middle: {latest_indicators['bb_middle']:.4f}, Upper: {latest_indicators['bb_upper']:.4f}",
#                 f"- Last Candle: {latest_indicators['candle_color']}"
#             ]
#             if klines_df_tail is not None and not klines_df_tail.empty:
#                 prompt_parts.append("\nRecent candlestick data (last 5 candles, OHLCV):")
#                 # Select relevant columns and format nicely
#                 klines_str = klines_df_tail[['open', 'high', 'low', 'close', 'volume']].tail(5).to_string(index=False)
#                 prompt_parts.append(klines_str)

#             prompt_parts.extend([
#                 "\nBased on this data and general crypto market sentiment, what is your trading recommendation?",
#                 "Provide your signal as one of: LONG, SHORT, or WAIT.",
#                 "Also, provide a very brief (1-2 sentences) reasoning for your signal.",
#                 "Format your response as JSON: {\"action\": \"<SIGNAL>\", \"reasoning\": \"<REASONING>\"}"
#             ])
#             prompt = "\n".join(prompt_parts)
            
#             logger.info(f"[{symbol}] Querying Gemini AI for trading recommendation...")
#             # --- THIS IS WHERE THE ACTUAL GEMINI API CALL WOULD GO ---
#             # response = self.model.generate_content(prompt)
#             # ai_response_text = response.text
#             # --- END OF ACTUAL GEMINI API CALL ---

#             # Mock response for conceptual demonstration (REMOVE FOR REAL IMPLEMENTATION)
#             time.sleep(0.1) # Simulate API call latency
#             # mock_actions = ["LONG", "SHORT", "WAIT"]
#             # mock_action = random.choice(mock_actions)
#             # ai_response_text = json.dumps({"action": mock_action, "reasoning": f"Mock AI reasoning for {mock_action}."})
#             # logger.warning(f"[{symbol}] USING MOCK AI RESPONSE: {ai_response_text}")
#             # --- END OF MOCK RESPONSE ---
            
#             logger.warning(f"[{symbol}] Gemini AI integration is conceptual. No actual API call made. Returning WAIT.")
#             return {"action": "WAIT", "reasoning": "AI analysis placeholder."}


#             # # Parse the response (assuming it's JSON as requested in prompt)
#             # try:
#             #     parsed_response = json.loads(ai_response_text)
#             #     action = parsed_response.get("action", "WAIT").upper()
#             #     reasoning = parsed_response.get("reasoning", "AI provided no reasoning.")
#             #     if action not in ["LONG", "SHORT", "WAIT"]: action = "WAIT" # Validate
#             #     logger.info(f"[{symbol}] AI Recommendation: {action}. Reason: {reasoning}")
#             #     return {"action": action, "reasoning": reasoning}
#             # except json.JSONDecodeError:
#             #     logger.error(f"[{symbol}] Failed to parse AI JSON response: {ai_response_text}")
#             #     return None

#         except Exception as e:
#             logger.error(f"[{symbol}] Error during AI recommendation: {e}", exc_info=True)
#             return None
# --- End of Conceptual AI ---


class TechnicalAnalysis:
    def __init__(self, binance_api):
        self.binance_api = binance_api
        self.settings = INDICATOR_SETTINGS
        # Conceptual: Initialize AI strategy component if enabled
        # self.ai_strategy = AIStrategy(CONFIG) if CONFIG.get("use_ai_strategy") else None
        self.ai_strategy = None # For now, keep it simple

    def calculate_indicators(self, symbol: str, timeframe: str = None) -> dict | None:
        if timeframe is None:
            timeframe = self.settings.get('candle_timeframe', '5m')

        ema_long_period = self.settings.get('ema_long_period', 26) # Corrected key
        bb_period = self.settings.get('bb_period', 20)
        rsi_period = self.settings.get('rsi_period', 14)
        
        required_initial_candles = max(ema_long_period, bb_period, rsi_period)
        buffer_candles = 30 
        limit_request = self.settings.get('klines_limit_for_indicator_calc', required_initial_candles + buffer_candles)
        
        logger.debug(f"[{symbol}@{timeframe}] Requesting klines from API, limit: {limit_request}")
        
        df: pd.DataFrame | None = self.binance_api.get_klines(symbol, timeframe, limit=limit_request)

        if df is None or df.empty:
            logger.error(f"[{symbol}@{timeframe}] get_klines returned None or empty DataFrame. Cannot calculate indicators.")
            return None
        
        if len(df) < required_initial_candles:
            logger.warning(
                f"[{symbol}@{timeframe}] Insufficient data returned ({len(df)} rows) "
                f"for full indicator calculation (needed at least {required_initial_candles}). "
                f"Results might have NaNs."
            )
            # Proceeding, but be aware some indicators might be NaN initially

        try:
            ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in ohlcv_cols:
                if col not in df.columns:
                    logger.error(f"[{symbol}@{timeframe}] DataFrame missing required column: '{col}'.")
                    return None
                if not pd.api.types.is_numeric_dtype(df[col]):
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                if df[col].isnull().any() and col in ['close', 'open']: # Critical columns
                    logger.error(f"[{symbol}@{timeframe}] Column '{col}' contains NaN values after numeric conversion. Dropping affected rows.")
                    df.dropna(subset=[col], inplace=True) # Drop rows where this critical col is NaN

            if df.empty or len(df) < 10: # Need some minimal data after potential drops
                logger.error(f"[{symbol}@{timeframe}] DataFrame became empty or too small after NaN handling. Cannot calculate indicators.")
                return None


            rsi_len = self.settings.get('rsi_period', 14)
            df['rsi'] = ta.rsi(close=df['close'], length=rsi_len)
            
            ema_s_len = self.settings.get('ema_short_period', 12) # Corrected key
            ema_l_len = self.settings.get('ema_long_period', 26)  # Corrected key
            df['ema_short'] = ta.ema(close=df['close'], length=ema_s_len)
            df['ema_long'] = ta.ema(close=df['close'], length=ema_l_len)
            
            bb_len = self.settings.get('bb_period', 20)
            bb_std = self.settings.get('bb_std', 2.0)
            bbands_df = ta.bbands(close=df['close'], length=bb_len, std=bb_std)
            
            if bbands_df is not None and not bbands_df.empty:
                bb_std_str = f"{bb_std}" 
                bb_l_col = f'BBL_{bb_len}_{bb_std_str}'
                bb_m_col = f'BBM_{bb_len}_{bb_std_str}'
                bb_u_col = f'BBU_{bb_len}_{bb_std_str}'

                # pandas-ta might use float like "2.0" or int like "2" in column names
                if bb_l_col not in bbands_df.columns and bb_std == float(int(bb_std)): # e.g. 2.0 == 2
                    bb_std_str_alt = str(int(bb_std))
                    bb_l_col_alt = f'BBL_{bb_len}_{bb_std_str_alt}'
                    if bb_l_col_alt in bbands_df.columns:
                        bb_l_col, bb_m_col, bb_u_col = bb_l_col_alt, f'BBM_{bb_len}_{bb_std_str_alt}', f'BBU_{bb_len}_{bb_std_str_alt}'
                
                if bb_l_col in bbands_df.columns:
                    df['bb_lower'] = bbands_df[bb_l_col]
                    df['bb_middle'] = bbands_df[bb_m_col]
                    df['bb_upper'] = bbands_df[bb_u_col]
                else:
                    logger.warning(f"[{symbol}@{timeframe}] Could not find expected Bollinger Bands columns (e.g., {bb_l_col}). Columns available: {list(bbands_df.columns)}. Setting BBs to NaN.")
                    df['bb_lower'], df['bb_middle'], df['bb_upper'] = pd.NA, pd.NA, pd.NA
            else:
                logger.warning(f"[{symbol}@{timeframe}] pandas_ta.bbands returned None or empty. Setting BBs to NaN.")
                df['bb_lower'], df['bb_middle'], df['bb_upper'] = pd.NA, pd.NA, pd.NA
            
            df['candle_color'] = np.where(df['close'] >= df['open'], 'green', 'red')
            df['candle_size_pct'] = ((df['close'] - df['open']).abs() / df['open'].replace(0, np.nan) * 100).fillna(0.0)
            
            if df.empty:
                logger.error(f"[{symbol}@{timeframe}] DataFrame is empty before selecting the latest row.")
                return None
                
            latest_indicators_row = df.iloc[-1].copy()
            previous_indicators_row = df.iloc[-2].copy() if len(df) > 1 else None

            critical_ta_cols_for_signal = ['rsi', 'ema_short', 'ema_long', 'bb_middle'] # bb_lower, bb_upper also important
            nan_in_critical = latest_indicators_row[critical_ta_cols_for_signal].isnull().any()

            if nan_in_critical:
                nan_details = latest_indicators_row[critical_ta_cols_for_signal].isnull()
                logger.warning(
                    f"[{symbol}@{timeframe}] Latest indicator row contains NaN in critical TA values: "
                    f"{nan_details[nan_details].index.tolist()}. Cannot generate reliable signal."
                )
                return None

        except KeyError as e_key:
            logger.error(f"[{symbol}@{timeframe}] KeyError during indicator calculation for '{e_key}'. DataFrame columns: {list(df.columns)}", exc_info=True)
            return None
        except Exception as e_calc:
            logger.error(f"[{symbol}@{timeframe}] Unexpected error during indicator calculation: {e_calc}", exc_info=True)
            return None
            
        return {
            'symbol': symbol,
            'timestamp': latest_indicators_row['timestamp'],
            'open': latest_indicators_row['open'], # Added for AI context
            'high': latest_indicators_row['high'], # Added for AI context
            'low': latest_indicators_row['low'],   # Added for AI context
            'close': latest_indicators_row['close'],
            'volume': latest_indicators_row['volume'], # Added for AI context
            'rsi': latest_indicators_row['rsi'],
            'ema_short': latest_indicators_row['ema_short'],
            'ema_long': latest_indicators_row['ema_long'],
            'bb_upper': latest_indicators_row['bb_upper'],
            'bb_middle': latest_indicators_row['bb_middle'],
            'bb_lower': latest_indicators_row['bb_lower'],
            'candle_color': latest_indicators_row['candle_color'],
            'candle_size_pct': latest_indicators_row['candle_size_pct'],
            'previous': previous_indicators_row,
            'klines_df_tail': df[['open', 'high', 'low', 'close', 'volume', 'timestamp']].tail(10) # For AI context
        }
        
    def get_signal(self, symbol, timeframe=None):
        if not timeframe:
            timeframe = self.settings['candle_timeframe']
        
        indicators_data = self.calculate_indicators(symbol, timeframe) # Renamed for clarity
        if not indicators_data:
            return None # calculate_indicators already logged
            
        # Use the values directly from the returned dict
        indicators = indicators_data # Alias for convenience if preferred, or use indicators_data directly

        signal = {
            'symbol': symbol,
            'timestamp': indicators['timestamp'],
            'price': indicators['close'],
            'action': 'WAIT',
            'strength': 0,
            'reasons': []
        }
        
        # Check for NaN values (should be caught by calculate_indicators, but double-check)
        required_fields = ['rsi', 'ema_short', 'ema_long', 'bb_upper', 'bb_lower', 'bb_middle', 'close', 'open']
        for field in required_fields:
            if pd.isna(indicators.get(field)):
                logger.warning(f"[{symbol}@{timeframe}] Critical indicator '{field}' is NaN. Skipping signal generation.")
                signal['reasons'].append(f"Indicator '{field}' is NaN")
                return signal # Return WAIT signal

        rsi_is_oversold = indicators['rsi'] < self.settings['rsi_oversold']
        rsi_is_overbought = indicators['rsi'] > self.settings['rsi_overbought']
        candle_is_green = indicators['candle_color'] == 'green'
        candle_is_red = indicators['candle_color'] == 'red'

        if rsi_is_oversold and candle_is_green:
            signal['action'] = 'LONG'
            signal['strength'] += 30
            signal['reasons'].append(f"RSI oversold ({indicators['rsi']:.2f}) & green candle")
        elif rsi_is_overbought and candle_is_red:
            signal['action'] = 'SHORT'
            signal['strength'] += 30
            signal['reasons'].append(f"RSI overbought ({indicators['rsi']:.2f}) & red candle")

        ema_s_valid = not pd.isna(indicators['ema_short'])
        ema_l_valid = not pd.isna(indicators['ema_long'])
        ema_is_bullish = False
        ema_is_bearish = False
        if ema_s_valid and ema_l_valid:
            ema_is_bullish = indicators['close'] > indicators['ema_short'] and indicators['ema_short'] > indicators['ema_long']
            ema_is_bearish = indicators['close'] < indicators['ema_short'] and indicators['ema_short'] < indicators['ema_long']
        
        if ema_is_bullish:
            if signal['action'] == 'LONG': signal['strength'] += 20; signal['reasons'].append("EMA bullish confirmation")
            elif signal['action'] == 'WAIT': signal['action'] = 'LONG'; signal['strength'] += 20; signal['reasons'].append("EMA bullish crossover")
        elif ema_is_bearish:
            if signal['action'] == 'SHORT': signal['strength'] += 20; signal['reasons'].append("EMA bearish confirmation")
            elif signal['action'] == 'WAIT': signal['action'] = 'SHORT'; signal['strength'] += 20; signal['reasons'].append("EMA bearish crossover")

        bb_u_valid = not pd.isna(indicators['bb_upper'])
        bb_l_valid = not pd.isna(indicators['bb_lower'])
        price_above_bb_upper = bb_u_valid and indicators['close'] > indicators['bb_upper']
        price_below_bb_lower = bb_l_valid and indicators['close'] < indicators['bb_lower']

        if price_above_bb_upper:
            if signal['action'] == 'SHORT': signal['strength'] += 20; signal['reasons'].append("BB price above upper (confirms SHORT)")
            elif signal['action'] == 'WAIT': signal['action'] = 'SHORT'; signal['strength'] += 15; signal['reasons'].append("BB price above upper (potential SHORT reversal)")
        elif price_below_bb_lower:
            if signal['action'] == 'LONG': signal['strength'] += 20; signal['reasons'].append("BB price below lower (confirms LONG)")
            elif signal['action'] == 'WAIT': signal['action'] = 'LONG'; signal['strength'] += 15; signal['reasons'].append("BB price below lower (potential LONG reversal)")

        # --- Conceptual AI Signal Integration ---
        # if self.ai_strategy:
        #     ai_reco = self.ai_strategy.get_ai_recommendation(
        #         symbol, 
        #         timeframe, 
        #         latest_indicators=pd.Series(indicators), # Pass the dict as a Series
        #         klines_df_tail=indicators_data.get('klines_df_tail')
        #     )
        #     if ai_reco and ai_reco['action'] != 'WAIT':
        #         logger.info(f"[{symbol}@{timeframe}] AI Recommendation: {ai_reco['action']} ({ai_reco['reasoning']})")
        #         # Example: AI confirms or provides primary signal
        #         if signal['action'] == 'WAIT' or signal['action'] == ai_reco['action']:
        #             if signal['action'] == 'WAIT': # AI is primary
        #                 signal['action'] = ai_reco['action']
        #                 signal['strength'] += CONFIG.get("ai_signal_strength_boost", 20) # Base strength for AI
        #             else: # AI confirms TA
        #                 signal['strength'] += CONFIG.get("ai_signal_strength_boost", 20) // 2 # Smaller boost for confirmation
        #             signal['reasons'].append(f"AI: {ai_reco['action']} ({ai_reco['reasoning']})")
        #         # Example: AI conflicts, TA might prevail or be weakened
        #         elif signal['action'] != ai_reco['action']:
        #             signal['reasons'].append(f"AI conflict: AI suggests {ai_reco['action']}, TA suggests {signal['action']}.")
                    # Could reduce strength or revert to WAIT if AI conflict is strong
                    # signal['strength'] = max(0, signal['strength'] - 10) 
        # --- End Conceptual AI ---


        signal_threshold = self.settings.get('signal_strength_threshold', 30)
        if signal['action'] != 'WAIT' and signal['strength'] < signal_threshold:
            original_action = signal['action']
            signal['action'] = 'WAIT'
            signal['reasons'] = [f"Final strength {signal['strength']}/{signal_threshold} insufficient for {original_action}"]
            signal['strength'] = 0
        elif signal['action'] == 'WAIT' and not signal['reasons']:
             signal['reasons'].append(f"No strong TA signal found (strength {signal['strength']}/{signal_threshold})")

        log_level = logging.WARNING if signal['action'] != 'WAIT' else logging.INFO
        logger.log(log_level,
            f"[{symbol}@{timeframe}] Final Signal: {signal['action']}, Strength: {signal['strength']}/{signal_threshold}, "
            f"Price: {signal['price']:.4f}, Reasons: {'; '.join(signal['reasons'])}"
        )
            
        return signal

class TradingBot:
    def __init__(self, config, telegram_bot=None):
        self.config = config # This is a mutable dict, changes here affect behavior
        self.telegram_bot = telegram_bot
        self.running = False
        self.trading_thread = None # Not used directly, signal_check_thread is the main one
        self.signal_check_thread = None
        self.notification_queue = queue.Queue()
        self.notification_thread = None
        
        if config.get("api_key") and config.get("api_secret"):
            self.binance_api = BinanceFuturesAPI(config)
            self.technical_analysis = TechnicalAnalysis(self.binance_api)
        else:
            self.binance_api = None
            self.technical_analysis = None
            logger.warning("Binance API key/secret not configured. Bot will run in limited mode.")

        self.dynamic_pair_scanner_thread = None
        self.currently_scanned_pairs = []
        self.active_trading_pairs_lock = threading.Lock()
        
        self.reset_daily_stats()

    def reset_daily_stats(self):
        DAILY_STATS["date"] = datetime.now().strftime("%Y-%m-%d")
        DAILY_STATS["total_trades"] = 0
        DAILY_STATS["winning_trades"] = 0
        DAILY_STATS["losing_trades"] = 0
        DAILY_STATS["total_profit_percentage_leveraged"] = 0.0 # Corrected key
        DAILY_STATS["total_profit_usdt"] = 0.0
        
        if self.binance_api and self.config.get("use_real_trading"): # Use get for safety
            try:
                balance_info = self.binance_api.get_balance() # Renamed variable
                if balance_info:
                    DAILY_STATS["starting_balance_usdt"] = balance_info['total'] # Corrected key
                    DAILY_STATS["current_balance_usdt"] = balance_info['total']  # Corrected key
                    DAILY_STATS["roi_percentage"] = 0.0 # Corrected key
                else: # Balance fetch failed
                    DAILY_STATS["starting_balance_usdt"] = 0.0
                    DAILY_STATS["current_balance_usdt"] = 0.0
            except Exception as e:
                logger.error(f"Error getting balance for daily stats: {e}")
                DAILY_STATS["starting_balance_usdt"] = 0.0
                DAILY_STATS["current_balance_usdt"] = 0.0
        else:
            DAILY_STATS["starting_balance_usdt"] = 0.0
            DAILY_STATS["current_balance_usdt"] = 0.0
            DAILY_STATS["roi_percentage"] = 0.0


    def send_notification(self, message, keyboard=None):
        if not self.telegram_bot:
            logger.warning("Cannot send notification: Telegram bot not initialized")
            return
        if not hasattr(self.telegram_bot, 'admin_chat_ids') or not self.telegram_bot.admin_chat_ids:
            logger.warning("Cannot send notification: No admin chat IDs available")
            return
        try:
            self.notification_queue.put((message, keyboard))
        except Exception as e:
            logger.error(f"Error queueing notification: {e}")

    def process_notification_queue(self):
        logger.info("Starting notification queue processor thread")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while self.running or not self.notification_queue.empty(): # Process remaining queue even if stopping
            try:
                message, keyboard = self.notification_queue.get(block=True, timeout=1.0)
                if message is None and keyboard is None: # Sentinel
                    logger.info("Notification processor received stop signal.")
                    break

                if not self.telegram_bot or not hasattr(self.telegram_bot, 'admin_chat_ids') or not self.telegram_bot.admin_chat_ids:
                    logger.error("Cannot send notification: Telegram bot not initialized or no admin chat IDs during processing.")
                    self.notification_queue.task_done()
                    continue

                for chat_id in self.telegram_bot.admin_chat_ids:
                    try:
                        coro_payload = {'chat_id': chat_id, 'text': message, 'parse_mode': constants.ParseMode.HTML}
                        if keyboard: coro_payload['reply_markup'] = InlineKeyboardMarkup(keyboard)
                        
                        future = asyncio.run_coroutine_threadsafe(
                            self.telegram_bot.application.bot.send_message(**coro_payload), loop
                        )
                        future.result(timeout=10)
                    
                    except Exception as e1:
                        logger.error(f"Failed to send notification using asyncio to {chat_id}: {e1}. Trying fallback.")
                        try:
                            token = getattr(self.telegram_bot, 'token', None) or \
                                    getattr(getattr(getattr(self.telegram_bot, 'application', {}), 'bot', {}), '_token', None) or \
                                    getattr(getattr(self.telegram_bot, 'application', {}), 'token', None)

                            if not token: raise Exception("Telegram token not found for fallback.")
                            url = f"https://api.telegram.org/bot{token}/sendMessage"
                            payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
                            if keyboard:
                                payload['reply_markup'] = json.dumps({'inline_keyboard': [[{'text': b.text, 'callback_data': b.callback_data} for b in r] for r in keyboard]})
                            response = requests.post(url, json=payload, timeout=10)
                            if response.status_code != 200:
                                logger.error(f"Fallback requests failed for {chat_id} with status {response.status_code}: {response.text}")
                        except Exception as e2:
                            logger.error(f"Fallback requests method also failed for {chat_id}: {e2}")
                
                self.notification_queue.task_done()
            except queue.Empty:
                if not self.running and self.notification_queue.empty(): break
                continue
            except Exception as e:
                logger.error(f"Error processing notification queue: {e}", exc_info=True)
                if not self.running: break
                time.sleep(1) # Shorter sleep on general error within loop
        
        loop.close()
        logger.info("Notification queue processor thread stopped.")
            
    def get_liquid_pairs_from_watchlist(self):
        if not self.binance_api:
            logger.warning("Binance API not available for liquidity check. Returning full watchlist.")
            return self.config.get("dynamic_watchlist_symbols", [])

        watchlist = self.config.get("dynamic_watchlist_symbols", [])
        min_volume_usdt = self.config.get("min_24h_volume_usdt_for_scan", 0)
        liquid_pairs = []

        if not watchlist:
            logger.info("Dynamic watchlist is empty.")
            return []

        try:
            # FIXED: Call get_ticker_24hr on self.binance_api
            all_tickers_data = self.binance_api.get_ticker_24hr() 
            if not all_tickers_data or not isinstance(all_tickers_data, list): # API returns a list for all symbols
                logger.error(f"Failed to fetch 24h ticker data or data is not a list for liquidity check. Received: {type(all_tickers_data)}")
                return watchlist 

            tickers_map = {item['symbol']: item for item in all_tickers_data if isinstance(item, dict) and 'symbol' in item}

            for symbol in watchlist:
                ticker_info = tickers_map.get(symbol)
                if ticker_info:
                    volume_24h_usdt = float(ticker_info.get('quoteVolume', 0))
                    if volume_24h_usdt >= min_volume_usdt:
                        liquid_pairs.append(symbol)
                    # else: # Too verbose for INFO, consider DEBUG
                        # logger.debug(f"DynamicScan: {symbol} skipped, volume {volume_24h_usdt:.2f} USDT < {min_volume_usdt:.2f} USDT")
                # else: # Too verbose for INFO
                    # logger.debug(f"DynamicScan: No 24h ticker data found for {symbol} in watchlist.")
            
            logger.info(f"DynamicScan: Found {len(liquid_pairs)} liquid pairs for scanning from {len(watchlist)}: {liquid_pairs if liquid_pairs else 'None'}")
            return liquid_pairs
            
        except Exception as e:
            logger.error(f"DynamicScan: Error during liquidity check: {e}", exc_info=True)
            return watchlist

    def dynamic_pair_scan_loop(self):
        logger.info("Dynamic Pair Scanner loop initiated.")
        while self.running:
            scan_successful = False
            try:
                if not self.config.get("dynamic_pair_selection", False):
                    time.sleep(self.config.get("dynamic_scan_interval_seconds", 300) / 10) 
                    continue

                logger.info("DynamicScan: Starting new scan cycle...")
                
                potential_pairs = self.get_liquid_pairs_from_watchlist()
                if not potential_pairs:
                    logger.info("DynamicScan: No liquid pairs from watchlist to scan this cycle.")
                    scan_successful = True 
                    # Full sleep interval if no pairs
                    sleep_interval = self.config.get("dynamic_scan_interval_seconds", 300)
                    for _ in range(sleep_interval):
                        if not self.running: break
                        time.sleep(1)
                    continue

                candidate_signals = []
                for symbol_to_scan in potential_pairs:
                    if not self.running: 
                        logger.info("DynamicScan: Bot stopping, aborting current scan.")
                        return 
                    
                    # logger.debug(f"DynamicScan: Evaluating signal for candidate: {symbol_to_scan}")
                    signal_data = self.technical_analysis.get_signal(symbol_to_scan) 
                    
                    if signal_data and signal_data['action'] != 'WAIT' and \
                       signal_data['strength'] >= self.config.get("signal_strength_threshold", INDICATOR_SETTINGS.get("signal_strength_threshold")): # Fallback to INDICATOR_SETTINGS
                        candidate_signals.append(signal_data)
                        # logger.info(f"DynamicScan: Strong signal for {symbol_to_scan} - Action: {signal_data['action']}, Strength: {signal_data['strength']}")
                    
                    # FIXED: Use correct config key for delay
                    time.sleep(self.config.get("api_call_delay_seconds_in_scan", 0.3)) 

                candidate_signals.sort(key=lambda x: x['strength'], reverse=True)
                self.currently_scanned_pairs = candidate_signals 

                max_active = self.config.get("max_active_dynamic_pairs", 1)
                new_dynamic_active_pairs = [s['symbol'] for s in candidate_signals[:max_active]]

                with self.active_trading_pairs_lock:
                    current_trading_pairs = list(self.config.get("trading_pairs", []))
                    if set(new_dynamic_active_pairs) != set(current_trading_pairs):
                        self.config["trading_pairs"] = new_dynamic_active_pairs 
                        logger.warning(
                            f"DynamicScan: Active trading pairs UPDATED. "
                            f"Old: {current_trading_pairs}, New: {self.config['trading_pairs']}"
                        )
                        self.send_notification(
                            f"🔄 <b>Dynamic Trading Pairs Updated</b> 🔄\n\n"
                            f"Now actively monitoring: {', '.join(self.config['trading_pairs']) if self.config['trading_pairs'] else 'None'}\n"
                            f"(Scan found {len(candidate_signals)} candidates from {len(potential_pairs)} liquid pairs)"
                        )
                    else:
                        logger.info(f"DynamicScan: No change to active trading pairs: {self.config['trading_pairs']}")
                scan_successful = True
            except Exception as e:
                logger.error(f"DynamicScan: Error in dynamic_pair_scan_loop: {e}", exc_info=True)
                time.sleep(60) 
            
            finally:
                if scan_successful:
                    interval = self.config.get("dynamic_scan_interval_seconds", 300)
                    # logger.debug(f"DynamicScan: Cycle complete. Sleeping for {interval} seconds.")
                    for _ in range(interval):
                        if not self.running: break
                        time.sleep(1)
        logger.info("Dynamic Pair Scanner loop has stopped.")
        
    def start_trading(self):
        if self.running:
            logger.info("Trading bot is already running.")
            return False
            
        self.running = True
        logger.info("Attempting to start trading bot...")
        
        self.apply_trading_mode_settings()

        # Check API connection before proceeding if real trading or hedge mode setup is involved
        if self.binance_api and (self.config.get("hedge_mode_enabled") or self.config.get("use_real_trading")):
            logger.info("Checking Binance API connection before full start...")
            account_info = self.binance_api.get_account_info()
            if not account_info:
                error_msg = "CRITICAL: Binance API connection failed (get_account_info). Cannot start trading. Check API keys, permissions, and IP whitelist."
                logger.error(error_msg)
                self.send_notification(f"❌ <b>Bot Start Failed</b> ❌\n\n{error_msg}")
                self.running = False # Abort start
                return False
            logger.info("Binance API connection successful.")


        # FIXED: Use correct config key "hedge_mode_enabled"
        if self.config.get("hedge_mode_enabled", False) and self.binance_api:
            try:
                logger.info("Attempting to set position mode to Hedge Mode.")
                # Ensure margin type is ISOLATED for all watchlist pairs if hedge mode is on
                # This is a common requirement or good practice with hedge mode.
                # You might want to do this for self.config['trading_pairs'] instead or also.
                # for symbol in self.config.get("dynamic_watchlist_symbols", []):
                #     if not self.running: break
                #     self.binance_api.change_margin_type(symbol, "ISOLATED") # Best effort
                #     time.sleep(0.1)


                result = self.binance_api.change_position_mode(dual_side_position=True)
                if result and result.get('code') == 200 : # 200 is for success or "no change needed"
                    logger.info(f"Position mode confirmed/set to Hedge Mode. Response: {result.get('msg', 'OK')}")
                # elif result and result.get('code') == -4059 : # Already in that mode
                #     logger.info(f"Position mode already set as Hedge Mode (Code -4059).")
                else: # Could be None or other error
                    logger.warning(f"Failed to set/confirm Hedge Mode or unexpected response: {result}. Bot will continue, but check Binance settings.")
            except Exception as e:
                logger.error(f"Error setting hedge mode: {e}", exc_info=True)
        
        self.signal_check_thread = threading.Thread(target=self.signal_check_loop)
        self.signal_check_thread.daemon = True
        self.signal_check_thread.start()
        
        if self.config.get("dynamic_pair_selection", False):
            self.dynamic_pair_scanner_thread = threading.Thread(target=self.dynamic_pair_scan_loop)
            self.dynamic_pair_scanner_thread.daemon = True
            self.dynamic_pair_scanner_thread.start()

        self.notification_thread = threading.Thread(target=self.process_notification_queue)
        self.notification_thread.daemon = True
        self.notification_thread.start()

        self.reset_daily_stats() # Reset stats after API check and potential balance update
        
        start_notification_message = (
            f"🚀 <b>Trading Bot Started</b> 🚀\n\n"
            f"<b>Mode:</b> {self.config.get('trading_mode', 'N/A').capitalize()}\n"
            f"<b>Leverage:</b> {self.config.get('leverage', 0)}x\n"
            f"<b>Take Profit:</b> {self.config.get('take_profit', 0.0)}%\n"
            f"<b>Stop Loss:</b> {self.config.get('stop_loss', 0.0)}%\n"
            f"<b>Position Size:</b> {self.config.get('position_size_percentage', 0.0)}% of balance\n"
            f"<b>Daily Profit Target:</b> {self.config.get('daily_profit_target_percentage', 0.0)}%\n" # Corrected key
            f"<b>Daily Loss Limit:</b> {self.config.get('daily_loss_limit_percentage', 0.0)}%\n"   # Corrected key
            f"<b>Trading Pairs:</b> {', '.join(self.config.get('trading_pairs', [])) if not self.config.get('dynamic_pair_selection', False) and self.config.get('trading_pairs', []) else ('Dynamic Selection Active' if self.config.get('dynamic_pair_selection', False) else 'None Configured')}\n"
            f"<b>Dynamic Pair Selection:</b> {'✅ Enabled' if self.config.get('dynamic_pair_selection', False) else '❌ Disabled'}\n"
            f"<b>Hedge Mode Attempted:</b> {'✅ Yes' if self.config.get('hedge_mode_enabled', False) else '❌ No'}\n"
            f"<b>Real Trading:</b> {'✅ Enabled' if self.config.get('use_real_trading', False) else '❌ Disabled (Simulation)'}\n"
            #f"<b>Using Testnet:</b> {'✅ Yes' if self.config.get('use_testnet', False) else '❌ No (Production Account)'}"
        )
        self.send_notification(start_notification_message)        
        
        logger.info("Trading bot successfully started and all associated threads are running.")
        return True

    def stop_trading(self):
        if not self.running:
            logger.info("Trading bot is not running or already in the process of stopping.")
            return False

        logger.warning("Initiating trading bot stop sequence...")
        self.running = False

        if self.dynamic_pair_scanner_thread and self.dynamic_pair_scanner_thread.is_alive():
            logger.info("Waiting for Dynamic Pair Scanner thread to join...")
            self.dynamic_pair_scanner_thread.join(timeout=10.0)
            if self.dynamic_pair_scanner_thread.is_alive(): logger.warning("Dynamic Pair Scanner thread did not join in time.")
            else: logger.info("Dynamic Pair Scanner thread joined.")

        if self.signal_check_thread and self.signal_check_thread.is_alive():
            logger.info("Waiting for Signal Check thread to join...")
            # Timeout slightly more than its work interval + a bit
            timeout_signal_check = self.config.get("signal_check_interval_seconds", 30) + 10.0
            self.signal_check_thread.join(timeout=timeout_signal_check)
            if self.signal_check_thread.is_alive(): logger.warning("Signal Check thread did not join in time.")
            else: logger.info("Signal Check thread joined.")
        
        self.send_notification("⏹️ <b>Trading Bot Stopped</b> ⏹️") 
        time.sleep(0.5) 

        if self.notification_thread and self.notification_thread.is_alive():
            logger.info("Signalling Notification Processor thread to stop and waiting for it to join...")
            try:
                self.notification_queue.put((None, None), block=False) 
            except queue.Full:
                logger.warning("Notification queue was full when trying to put stop sentinel.")
            
            self.notification_thread.join(timeout=15.0)
            if self.notification_thread.is_alive(): logger.warning("Notification Processor thread did not join in time.")
            else: logger.info("Notification Processor thread joined.")
        
        logger.debug("Clearing any remaining items in the notification queue post-join...")
        while not self.notification_queue.empty():
            try: self.notification_queue.get_nowait(); self.notification_queue.task_done()
            except queue.Empty: break
        
        logger.warning("Trading bot stop sequence complete. Bot is now stopped.")
        return True
        
    def apply_trading_mode_settings(self):
        mode = self.config.get("trading_mode", "standard") # Use .get for safety
        if mode in TRADING_MODES:
            mode_settings = TRADING_MODES[mode]
            self.config["leverage"] = mode_settings["leverage"]
            self.config["take_profit"] = mode_settings["take_profit"]
            self.config["stop_loss"] = mode_settings["stop_loss"]
            self.config["position_size_percentage"] = mode_settings["position_size_percent"]
            self.config["max_daily_trades"] = mode_settings["max_daily_trades"]
            logger.info(f"Applied '{mode}' trading mode settings.")
        else:
            logger.warning(f"Trading mode '{mode}' not found in TRADING_MODES. Using current/default config values.")


    def check_daily_limits(self) -> bool: # Return True to continue, False to stop
        # Check daily trades limit first
        max_trades = self.config.get("max_daily_trades", 15)
        if DAILY_STATS["total_trades"] >= max_trades:
            logger.info(f"Max daily trades ({DAILY_STATS['total_trades']}/{max_trades}) reached. Stopping trading.")
            self.send_notification(
                f"📊 MAX DAILY TRADES REACHED ({max_trades})\n"
                f"Trading paused for today. Use /starttrade to resume tomorrow or after reset."
            )
            return False # Stop trading

        # Check profit/loss limits if real trading and balance tracking is meaningful
        if self.config.get("use_real_trading") and DAILY_STATS["starting_balance_usdt"] > 0:
            profit_target_pct = self.config.get("daily_profit_target_percentage", 5.0)
            loss_limit_pct = self.config.get("daily_loss_limit_percentage", 3.0)
            
            # Calculate current profit percentage based on tracked USDT balance
            current_profit_usdt = DAILY_STATS["current_balance_usdt"] - DAILY_STATS["starting_balance_usdt"]
            current_profit_percentage_on_balance = (current_profit_usdt / DAILY_STATS["starting_balance_usdt"]) * 100

            if current_profit_percentage_on_balance >= profit_target_pct:
                logger.info(f"Daily profit target reached: {current_profit_percentage_on_balance:.2f}% >= {profit_target_pct}%. Stopping trading.")
                self.send_notification(
                    f"🎯 DAILY PROFIT TARGET REACHED!\n"
                    f"Profit: {current_profit_percentage_on_balance:.2f}% of starting balance.\n"
                    f"Trading paused for today."
                )
                return False # Stop trading
            
            if current_profit_percentage_on_balance <= -loss_limit_pct: # Loss limit is positive, so compare to negative
                logger.info(f"Daily loss limit reached: {current_profit_percentage_on_balance:.2f}% <= -{loss_limit_pct}%. Stopping trading.")
                self.send_notification(
                    f"⚠️ DAILY LOSS LIMIT REACHED!\n"
                    f"Loss: {current_profit_percentage_on_balance:.2f}% of starting balance.\n"
                    f"Trading paused for today."
                )
                return False # Stop trading
        
        return True # Continue trading

    # REMOVED the first, simpler signal_check_loop. This is the retained, more complete one.
    def signal_check_loop(self):
        logger.info("Signal check loop (for active trading pairs) initiated.")
        
        # Initial sleep to allow dynamic scanner to potentially populate pairs
        if self.config.get("dynamic_pair_selection"):
            logger.info("SignalCheck: Initial short sleep for dynamic scanner.")
            time.sleep(5) 

        while self.running:
            try:
                if not self.check_daily_limits(): # This checks trades, P/L limits
                    logger.info("Daily limits reached or max trades. Stopping trading from signal_check_loop.")
                    self.stop_trading() 
                    break 
                
                active_pairs_this_iteration = []
                with self.active_trading_pairs_lock:
                    active_pairs_this_iteration = list(self.config.get("trading_pairs", []))

                if not active_pairs_this_iteration:
                    log_msg = "SignalCheck: No trading pairs configured."
                    if self.config.get("dynamic_pair_selection", False):
                        log_msg = "SignalCheck: No active dynamic trading pairs currently (waiting for scanner or no strong signals found). Idling."
                    # else: # Static pairs, but none are set
                        # log_msg = "SignalCheck: No static trading pairs configured. Idling."
                    # logger.debug(log_msg) # Can be noisy
                    time.sleep(self.config.get("signal_check_interval_seconds", 30) / 2) # Shorter sleep if no pairs
                    continue

                # logger.debug(f"SignalCheck: Checking signals for active pairs: {active_pairs_this_iteration}")
                for symbol_to_trade in active_pairs_this_iteration:
                    if not self.running: 
                        logger.info("SignalCheck: Bot stopping, aborting current pair checks.")
                        break 

                    has_active_trade_for_symbol = any(
                        t['symbol'] == symbol_to_trade and not t.get('completed', False) for t in ACTIVE_TRADES
                    )
                    if has_active_trade_for_symbol:
                        # logger.debug(f"SignalCheck: Skipping {symbol_to_trade}, active trade exists.")
                        continue
                        
                    # logger.debug(f"SignalCheck: Evaluating signal for active pair: {symbol_to_trade}")
                    signal = self.technical_analysis.get_signal(symbol_to_trade)
                    
                    if signal and signal['action'] != 'WAIT':
                        logger.info(f"SignalCheck: Processing signal for {symbol_to_trade}: {signal['action']} (Strength: {signal['strength']})")
                        self.process_signal(signal) 
                        time.sleep(self.config.get("post_trade_entry_delay_seconds", 2)) 
                    # Optional: Small delay between checking different symbols to avoid hitting API rate limits on klines if many pairs
                    # time.sleep(0.1) 

                if not self.running: break 

                # logger.debug(f"SignalCheck: Cycle complete. Sleeping for {self.config.get('signal_check_interval_seconds', 30)}s.")
                interval = self.config.get("signal_check_interval_seconds", 30)
                for _ in range(interval):
                    if not self.running: break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"SignalCheck: Error in signal_check_loop: {e}", exc_info=True)
                for _ in range(min(60, self.config.get("signal_check_interval_seconds", 30))): # Sleep on error, but not too long
                    if not self.running: break
                    time.sleep(1)
                    
        logger.info("Signal check loop has stopped.")

    def process_signal(self, signal):
        symbol = signal['symbol']
        action = signal['action'] # LONG or SHORT
        price = signal['price']   # Entry price from signal (current close)
        
        logger.info(f"Processing signal: {symbol} {action} at {price:.4f}, Strength: {signal['strength']}")
        
        if not self.config.get("use_real_trading"):
            logger.info(f"[SIMULATION] Would open {action} for {symbol} at {price:.4f}")
            # Create a simulated trade for tracking if desired, even in simulation mode
            # This part is up to how you want to handle simulation.
            # For now, we'll proceed as if creating a real trade but rely on `create_trade`'s internal check.
        
        position_side = "LONG" if action == "LONG" else "SHORT"
        order_side = "BUY" if action == "LONG" else "SELL"
        
        # Critical: Ensure API is available if real trading is on
        if self.config.get("use_real_trading") and not self.binance_api:
            logger.error(f"[{symbol}] Attempting real trade but Binance API is not initialized. Aborting.")
            self.send_notification(f"⚠️ Real trade for {symbol} aborted: API not initialized.")
            return

        # Calculate position size
        # This needs current price, which we have from signal['price']
        quantity = self.calculate_position_size(symbol, price) 
        if not quantity or quantity <= 0:
            logger.error(f"[{symbol}] Failed to calculate valid position size ({quantity}). Aborting trade.")
            self.send_notification(f"⚠️ Trade for {symbol} aborted: Invalid position size.")
            return
            
        # Set leverage for the symbol (only if real trading and API available)
        if self.binance_api and self.config.get("use_real_trading"):
            leverage_set_success = self.binance_api.change_leverage(symbol, self.config["leverage"])
            if not leverage_set_success:
                logger.warning(f"[{symbol}] Failed to set leverage to {self.config['leverage']}x. Order will use current leverage. Check API permissions for leverage.")
                # Decide if you want to abort or continue if leverage can't be set. For now, continue.
        
        # Create the trade (this will handle real vs. simulation internally)
        trade_details = self.create_trade(symbol, action, position_side, order_side, price, quantity)
        if not trade_details:
            logger.error(f"[{symbol}] Failed to create trade object/orders.")
            # Notification might be redundant if create_trade already sent one
            return
            
        self.send_trade_notification(trade_details, signal.get('reasons', []))


    def calculate_position_size(self, symbol: str, current_price: float) -> float | None:
        try:
            if current_price <= 0:
                logger.error(f"[{symbol}] Invalid current_price ({current_price}) for position size calculation.")
                return None

            # Handle simulation mode or if API is not available for balance check
            if not self.config.get("use_real_trading") or not self.binance_api:
                logger.info(f"[{symbol}] In simulation or API unavailable. Using fixed USDT amount for position size: {self.config.get('fixed_position_size_usdt', 10)} USDT.")
                fixed_usdt_for_sim = self.config.get("fixed_position_size_usdt", 10) # Default to small amount for sim
                # For simulation, if position_size_percentage is used, it needs a simulated balance.
                # For simplicity, simulation uses fixed_position_size_usdt to calculate quantity.
                sim_quantity = fixed_usdt_for_sim / current_price # This is notional based
                # If fixed_usdt_for_sim is margin, then: (fixed_usdt_for_sim * leverage) / current_price
                # Let's assume fixed_position_size_usdt is MARGIN for simulation consistency.
                sim_quantity_leveraged = (fixed_usdt_for_sim * self.config.get("leverage", 1)) / current_price
                
                # Round simulated quantity (important even for simulation if you log it like a real trade)
                if self.binance_api: # Try to get rounding info if API exists, even for sim
                     rounded_sim_quantity = self.binance_api.round_quantity(symbol, sim_quantity_leveraged)
                     # MinQty/MinNotional check for simulation (optional but good for realism)
                     # For now, just return the rounded quantity.
                     return rounded_sim_quantity if rounded_sim_quantity > 0 else None
                else: # No API for rounding info
                    return round(sim_quantity_leveraged, 8) if sim_quantity_leveraged > 0 else None # Generic rounding

            # Real trading: Get balance
            balance_data = self.binance_api.get_balance()
            if not balance_data or 'available' not in balance_data:
                logger.error(f"[{symbol}] Failed to get valid balance for position size calculation.")
                return None
            
            available_balance_usdt = float(balance_data['available'])
            if available_balance_usdt <= self.config.get("min_notional", 5.0): # Don't trade with dust
                logger.warning(f"[{symbol}] Available balance ({available_balance_usdt:.2f} USDT) is too low. Min needed approx {self.config.get('min_notional', 5.0)} USDT. Skipping trade.")
                return None

            margin_to_use_usdt = 0.0
            if self.config.get("use_percentage_for_pos_size", True):
                percentage = self.config.get("position_size_percentage", 1.0) # Default to 1% if not set
                margin_to_use_usdt = available_balance_usdt * (percentage / 100.0)
                logger.info(f"[{symbol}] Using {percentage}% of available balance ({available_balance_usdt:.2f} USDT) for margin = {margin_to_use_usdt:.2f} USDT.")
            else:
                margin_to_use_usdt = self.config.get("fixed_position_size_usdt", 10.0) # Default to 10 USDT fixed
                logger.info(f"[{symbol}] Using fixed margin amount = {margin_to_use_usdt:.2f} USDT.")

            # Ensure margin is not more than available balance
            if margin_to_use_usdt > available_balance_usdt * 0.98 : # Use 98% to leave some buffer
                margin_to_use_usdt = available_balance_usdt * 0.98
                logger.warning(f"[{symbol}] Calculated margin exceeds available balance. Adjusted to {margin_to_use_usdt:.2f} USDT.")

            if margin_to_use_usdt <= 0:
                logger.error(f"[{symbol}] Margin to use ({margin_to_use_usdt:.2f} USDT) is not positive. Cannot open position.")
                return None

            current_leverage = self.config.get("leverage", 1) # Default to 1x if not set
            
            # Quantity = (Margin * Leverage) / Price
            quantity_calculated = (margin_to_use_usdt * current_leverage) / current_price
            
            if quantity_calculated <= 0:
                logger.error(f"[{symbol}] Calculated quantity ({quantity_calculated}) is not positive. Cannot proceed.")
                return None

            rounded_quantity = self.binance_api.round_quantity(symbol, quantity_calculated)
            if rounded_quantity <= 0:
                logger.error(f"[{symbol}] Rounded quantity ({rounded_quantity}) is not positive. Original: {quantity_calculated}. Cannot proceed.")
                return None

            # MinQty and MinNotional Checks
            symbol_info = self.binance_api.get_symbol_info(symbol)
            if symbol_info:
                min_qty_str = symbol_info.get('minQty', '0.00000001')
                min_notional_str = symbol_info.get('minNotional', '5.0') # Futures min notional is often around 5 USDT
                
                try:
                    min_qty = float(min_qty_str)
                    min_notional_val = float(min_notional_str)
                except ValueError:
                    logger.error(f"[{symbol}] Could not parse minQty/minNotional from symbol_info: {min_qty_str}, {min_notional_str}")
                    return None # Fail safe

                if rounded_quantity < min_qty:
                    logger.error(f"[{symbol}] Calculated quantity {rounded_quantity} is less than minQty {min_qty}. Adjusting or skipping.")
                    # Option: try to adjust to min_qty if notional allows, or just skip
                    # For now, skip if strictly less.
                    return None 
                
                notional_value_of_trade = rounded_quantity * current_price # This is the value of the position
                if notional_value_of_trade < min_notional_val:
                    logger.error(f"[{symbol}] Notional value {notional_value_of_trade:.2f} USDT is less than minNotional {min_notional_val:.2f} USDT. Cannot create order.")
                    # Option: try to increase quantity to meet minNotional, if balance/risk allows
                    return None
            else:
                logger.warning(f"[{symbol}] Could not get symbol_info to verify minQty/minNotional. Proceeding with caution with quantity: {rounded_quantity}")

            logger.info(f"[{symbol}] Position Size: Margin {margin_to_use_usdt:.2f} USDT, Leverage {current_leverage}x, Price {current_price:.4f} -> Quantity {quantity_calculated:.8f} -> Rounded Qty {rounded_quantity:.8f}")
            return rounded_quantity
            
        except KeyError as e:
            logger.error(f"Error calculating position size: Missing key {e} in config or balance data.", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error calculating position size for {symbol}: {e}", exc_info=True)
            return None

    def create_trade(self, symbol, action, position_side, order_side, entry_price, quantity):
        try:
            tp_percentage = self.config.get("take_profit", 1.0)
            sl_percentage = self.config.get("stop_loss", 0.5)
            
            if action == "LONG":
                tp_price_calc = entry_price * (1 + tp_percentage / 100)
                sl_price_calc = entry_price * (1 - sl_percentage / 100)
            else:  # SHORT
                tp_price_calc = entry_price * (1 - tp_percentage / 100)
                sl_price_calc = entry_price * (1 + sl_percentage / 100)
            
            # Round prices (needs binance_api, handle if not available for sim)
            if self.binance_api:
                take_profit_price = self.binance_api.round_price(symbol, tp_price_calc)
                stop_loss_price = self.binance_api.round_price(symbol, sl_price_calc)
            else: # Basic rounding for simulation if API not present
                take_profit_price = round(tp_price_calc, 8) 
                stop_loss_price = round(sl_price_calc, 8)
            
            # Ensure TP/SL prices are valid (e.g., SL not triggering immediately)
            if action == "LONG":
                if stop_loss_price >= entry_price: 
                    logger.warning(f"[{symbol}] Calculated SL price {stop_loss_price} for LONG is >= entry {entry_price}. Adjusting SL lower or check config.")
                    # Potentially adjust SL or make it wider, or require wider SL in config. For now, log and proceed.
                if take_profit_price <= entry_price:
                     logger.warning(f"[{symbol}] Calculated TP price {take_profit_price} for LONG is <= entry {entry_price}. Check config.")
            else: # SHORT
                if stop_loss_price <= entry_price:
                    logger.warning(f"[{symbol}] Calculated SL price {stop_loss_price} for SHORT is <= entry {entry_price}. Adjusting SL higher or check config.")
                if take_profit_price >= entry_price:
                    logger.warning(f"[{symbol}] Calculated TP price {take_profit_price} for SHORT is >= entry {entry_price}. Check config.")


            trade_obj = { # Renamed to avoid conflict with trade variable name later
                'id': f"{symbol}-{int(time.time())}-{random.randint(100,999)}", # More unique ID
                'timestamp': time.time(),
                'symbol': symbol,
                'action': action, # LONG/SHORT (strategy intent)
                'position_side': position_side, # LONG/SHORT (for hedge mode)
                'order_side': order_side, # BUY/SELL (for market entry order)
                'entry_price': entry_price, # Actual or intended entry price
                'quantity': quantity,
                'take_profit_price': take_profit_price, # Renamed for clarity
                'stop_loss_price': stop_loss_price,   # Renamed for clarity
                'leverage': self.config.get("leverage", 1),
                'entry_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'completed': False,
                'status': 'PENDING_ENTRY', # PENDING_ENTRY, ACTIVE, PENDING_CLOSE
                'mode': self.config.get('trading_mode', 'N/A'),
                'entry_order_id': None, 'entry_order_status': None, 'avg_fill_price': None,
                'tp_order_id': None, 'sl_order_id': None,
                'real_trade': self.config.get("use_real_trading", False) and bool(self.binance_api) # Must have API for real trade
            }
            
            if trade_obj['real_trade']:
                logger.info(f"[{symbol}] Attempting to place REAL orders.")
                # Ensure hedge mode consistency: positionSide is LONG or SHORT
                entry_order_params = {
                    'symbol': symbol, 'side': order_side, 'order_type': "MARKET",
                    'quantity': quantity
                }
                if self.config.get("hedge_mode_enabled"):
                    entry_order_params['positionSide'] = position_side
                
                entry_order_response = self.binance_api.create_order(**entry_order_params)
                
                if not entry_order_response or 'orderId' not in entry_order_response:
                    logger.error(f"[{symbol}] Failed to create REAL entry order. Response: {entry_order_response}")
                    self.send_notification(f"❌ Failed to open REAL {action} for {symbol}.")
                    return None # Critical failure for real trade
                
                trade_obj['entry_order_id'] = entry_order_response['orderId']
                trade_obj['status'] = 'ENTRY_ORDER_PLACED' 
                logger.info(f"[{symbol}] REAL Entry Market Order placed: ID {trade_obj['entry_order_id']}.")

                # For MARKET orders, Binance fills them quickly. We might need to query order status to get avgFilledPrice.
                # For simplicity here, we'll assume entry_price is close enough for TP/SL calculation for now.
                # A robust system would query the fill price after a short delay.
                # trade_obj['avg_fill_price'] = float(entry_order_response.get('avgPrice', entry_price)) # If market order gives avgPrice
                # if trade_obj['avg_fill_price'] and trade_obj['avg_fill_price'] > 0:
                #    # Recalculate TP/SL based on actual fill price if significantly different
                #    pass


                # Wait a moment for the entry order to likely fill before placing TP/SL
                time.sleep(self.config.get("post_trade_entry_delay_seconds", 3)) 

                # Place TP and SL orders (OCO is not directly supported for futures like spot, use separate TP_MARKET/STOP_MARKET)
                # These orders are reduceOnly and opposite side of the position.
                tp_sl_side = "SELL" if action == "LONG" else "BUY"

                # Take Profit Order
                tp_params = {
                    'symbol': symbol, 'side': tp_sl_side, 'order_type': "TAKE_PROFIT_MARKET",
                    'quantity': quantity, 'stopPrice': take_profit_price, 'reduceOnly': True
                }
                if self.config.get("hedge_mode_enabled"): tp_params['positionSide'] = position_side
                
                tp_order_response = self.binance_api.create_order(**tp_params)
                if tp_order_response and 'orderId' in tp_order_response:
                    trade_obj['tp_order_id'] = tp_order_response['orderId']
                    logger.info(f"[{symbol}] REAL TP Order placed: ID {trade_obj['tp_order_id']} at {take_profit_price:.4f}")
                else:
                    logger.warning(f"[{symbol}] Failed to place REAL TP order. Response: {tp_order_response}")
                    # This is not ideal, position is open without TP. Manual intervention might be needed.
                    self.send_notification(f"⚠️ Failed to place TP for {symbol} {action}. Position is open.")

                # Stop Loss Order
                sl_params = {
                    'symbol': symbol, 'side': tp_sl_side, 'order_type': "STOP_MARKET",
                    'quantity': quantity, 'stopPrice': stop_loss_price, 'reduceOnly': True
                }
                if self.config.get("hedge_mode_enabled"): sl_params['positionSide'] = position_side

                sl_order_response = self.binance_api.create_order(**sl_params)
                if sl_order_response and 'orderId' in sl_order_response:
                    trade_obj['sl_order_id'] = sl_order_response['orderId']
                    logger.info(f"[{symbol}] REAL SL Order placed: ID {trade_obj['sl_order_id']} at {stop_loss_price:.4f}")
                else:
                    logger.warning(f"[{symbol}] Failed to place REAL SL order. Response: {sl_order_response}")
                    self.send_notification(f"⚠️ Failed to place SL for {symbol} {action}. Position is open without SL protection.")
                
                trade_obj['status'] = 'ACTIVE' # If entry order is assumed filled and TP/SL placed

            else: # Simulation
                logger.info(f"[{symbol}] Recording SIMULATED {action} trade at {entry_price:.4f}, Qty: {quantity}.")
                trade_obj['status'] = 'ACTIVE' # Simulated trades are active immediately

            ACTIVE_TRADES.append(trade_obj)
            DAILY_STATS["total_trades"] += 1 # Count both real and simulated for this stat
            
            return trade_obj
            
        except Exception as e:
            logger.error(f"[{symbol}] Error in create_trade: {e}", exc_info=True)
            self.send_notification(f"❌ Error creating trade for {symbol}: {e}")
            return None

    def send_trade_notification(self, trade, reasons):
        action_emoji = "🟢" if trade['action'] == "LONG" else "🔴"
        trade_type = "REAL" if trade['real_trade'] else "SIMULATED"
        
        message = (
            f"{action_emoji} NEW {trade_type} {trade['action']} POSITION\n\n"
            f"Symbol: <b>{trade['symbol']}</b>\n"
            f"Mode: {trade.get('mode', 'N/A').capitalize()}\n"
            f"Entry Price: ${trade['entry_price']:.4f}\n"
            f"Quantity: {trade['quantity']}\n"
            f"Leverage: {trade['leverage']}x\n"
            f"Take Profit: ${trade['take_profit_price']:.4f} (+{self.config.get('take_profit',0)}%)\n" # Use configured TP %
            f"Stop Loss: ${trade['stop_loss_price']:.4f} (-{self.config.get('stop_loss',0)}%)\n"     # Use configured SL %
            f"Time: {trade['entry_time']}\n"
        )
        if reasons:
            message += f"\nSignal Reasons:\n"
            for reason_idx, reason in enumerate(reasons):
                if reason_idx < 5: # Limit number of reasons displayed
                     message += f"• {reason}\n"
                elif reason_idx == 5:
                    message += f"• ... and more.\n"


        if trade['real_trade']:
            message += f"\nEntry Order ID: {trade.get('entry_order_id', 'N/A')}\n"
            message += f"TP Order ID: {trade.get('tp_order_id', 'N/A')}\n"
            message += f"SL Order ID: {trade.get('sl_order_id', 'N/A')}\n"
        
        message += f"\nStatus: {trade.get('status', 'UNKNOWN')}"
        
        self.send_notification(message)

    # This method is for manual or external completion signals.
    # Automatic completion via TP/SL hits would need a separate monitoring loop for open orders/positions.
    def complete_trade(self, trade_id, exit_price, exit_reason="manual_close"):
        trade_to_complete = next((t for t in ACTIVE_TRADES if t['id'] == trade_id and not t.get('completed')), None)
        if not trade_to_complete:
            logger.warning(f"Attempted to complete non-existent or already completed trade ID: {trade_id}")
            return False

        try:
            entry_price = trade_to_complete['entry_price']
            quantity = trade_to_complete['quantity']
            leverage = trade_to_complete['leverage']
            action = trade_to_complete['action']

            if action == "LONG":
                raw_profit_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price != 0 else 0
            else:  # SHORT
                raw_profit_pct = ((entry_price - exit_price) / entry_price) * 100 if entry_price != 0 else 0
                
            leveraged_profit_pct = raw_profit_pct * leverage
            
            # Profit in USDT (Notional Value * Raw Profit Percentage)
            # Notional value at entry = entry_price * quantity
            # This is the PnL on the position size, not on the margin used.
            profit_usdt = (entry_price * quantity) * (raw_profit_pct / 100.0)
            
            trade_to_complete.update({
                'completed': True,
                'status': 'COMPLETED',
                'exit_price': exit_price,
                'exit_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'profit_pct_raw': raw_profit_pct, # Pct change of price
                'leveraged_profit_pct': leveraged_profit_pct, # Pct change on margin (approx)
                'profit_usdt': profit_usdt, # Actual USDT PnL
                'exit_reason': exit_reason
            })
            
            # Update daily stats (only if it was a real trade for financial stats)
            if trade_to_complete.get('real_trade', False):
                DAILY_STATS["total_profit_percentage_leveraged"] += leveraged_profit_pct # This is an aggregation of percentages, might not be ideal.
                DAILY_STATS["total_profit_usdt"] += profit_usdt
                
                if profit_usdt > 0: DAILY_STATS["winning_trades"] += 1
                elif profit_usdt < 0: DAILY_STATS["losing_trades"] += 1 # Only count if actual loss
                
                # Update current balance (important for daily P/L limits)
                if DAILY_STATS["starting_balance_usdt"] > 0: # Ensure we have a starting point
                    DAILY_STATS["current_balance_usdt"] += profit_usdt
                    DAILY_STATS["roi_percentage"] = ((DAILY_STATS["current_balance_usdt"] - DAILY_STATS["starting_balance_usdt"]) / DAILY_STATS["starting_balance_usdt"]) * 100
            
            # If this was a real trade, attempt to cancel any remaining TP/SL orders
            if trade_to_complete.get('real_trade', False) and self.binance_api:
                symbol = trade_to_complete['symbol']
                if trade_to_complete.get('tp_order_id'):
                    logger.info(f"Attempting to cancel TP order {trade_to_complete['tp_order_id']} for closed trade {trade_id}")
                    self.binance_api.cancel_order(symbol, order_id=trade_to_complete['tp_order_id'])
                if trade_to_complete.get('sl_order_id'):
                    logger.info(f"Attempting to cancel SL order {trade_to_complete['sl_order_id']} for closed trade {trade_id}")
                    self.binance_api.cancel_order(symbol, order_id=trade_to_complete['sl_order_id'])
            
            is_win = profit_usdt > 0
            result_text = "WIN" if is_win else ("LOSS" if profit_usdt < 0 else "BREAKEVEN")
            emoji = "✅" if is_win else ("❌" if profit_usdt < 0 else "➖")
            
            exit_reason_map = {
                "take_profit": "Take Profit Hit", "stop_loss": "Stop Loss Hit",
                "manual_close": "Manual Close", "signal_reversed": "Signal Reversed",
                "daily_limit": "Daily Limit Hit"
            }
            reason_display = exit_reason_map.get(exit_reason, exit_reason.replace("_", " ").capitalize())
                
            duration_seconds = int(time.time() - trade_to_complete['timestamp'])
            
            complete_message = (
                f"{emoji} TRADE {result_text} ({'REAL' if trade_to_complete['real_trade'] else 'SIM'}) {emoji}\n\n"
                f"Symbol: <b>{trade_to_complete['symbol']}</b> ({trade_to_complete['action']})\n"
                f"Entry: ${entry_price:.4f}, Exit: ${exit_price:.4f}\n"
                f"Qty: {quantity}, Lev: {leverage}x\n"
                f"PnL USDT: <b>${profit_usdt:.2f}</b>\n"
                f"PnL Raw: {raw_profit_pct:.2f}%, Leveraged: {leveraged_profit_pct:.2f}%\n"
                f"Reason: {reason_display}\n"
                f"Duration: {timedelta(seconds=duration_seconds)}\n"
                f"Mode: {trade_to_complete.get('mode', 'N/A').capitalize()}"
            )
            self.send_notification(complete_message)
            
            ACTIVE_TRADES.remove(trade_to_complete)
            COMPLETED_TRADES.append(trade_to_complete)
            logger.info(f"Trade {trade_id} completed. Result: {result_text}, PnL: ${profit_usdt:.2f} USDT.")
            return True
            
        except Exception as e:
            logger.error(f"Error completing trade {trade_id}: {e}", exc_info=True)
            return False

    def get_daily_stats_message(self):
        # Recalculate win_rate based on current DAILY_STATS
        # total_recorded_trades = DAILY_STATS["winning_trades"] + DAILY_STATS["losing_trades"] # Trades with P/L
        total_recorded_trades = DAILY_STATS["total_trades"] # All attempts
        win_rate = 0
        if total_recorded_trades > 0: # Use total_trades for win rate if it includes all opened positions
            win_rate = (DAILY_STATS["winning_trades"] / total_recorded_trades) * 100 if total_recorded_trades > 0 else 0

        # ROI based on starting and current USDT balance for the day
        # roi_pct = DAILY_STATS.get("roi_percentage", 0.0) # This is already calculated in complete_trade

        stats_message = (
            f"📊 <b>DAILY TRADING STATS - {DAILY_STATS.get('date', 'N/A')}</b> 📊\n\n"
            f"Attempted Trades: {DAILY_STATS['total_trades']}\n"
            f"Winning Trades: {DAILY_STATS['winning_trades']}\n"
            f"Losing Trades: {DAILY_STATS['losing_trades']}\n"
            f"Win Rate (on attempts): {win_rate:.1f}%\n\n"
            # f"Total Profit/Loss (Leveraged % Sum): {DAILY_STATS['total_profit_percentage_leveraged']:.2f}% (Note: Sum of percentages)\n" # This can be misleading
            f"Total Profit/Loss (USDT): <b>${DAILY_STATS['total_profit_usdt']:.2f}</b>\n\n"
            f"<u>Balance Tracking (Real Trades):</u>\n"
            f"Starting Balance: ${DAILY_STATS['starting_balance_usdt']:.2f} USDT\n"
            f"Current Balance: ${DAILY_STATS['current_balance_usdt']:.2f} USDT\n"
            f"Daily ROI: {DAILY_STATS.get('roi_percentage',0.0):.2f}%\n\n"
            f"<u>Current Bot Settings:</u>\n"
            f"Trading Mode: {self.config.get('trading_mode', 'N/A').capitalize()}\n"
            f"Real Trading: {'✅ Enabled' if self.config.get('use_real_trading') else '❌ Disabled'}\n"
            #f"Testnet: {'✅ Yes' if self.config.get('use_testnet') else '❌ No (Production)'}"
        )
        return stats_message

class TelegramBotHandler:
    def __init__(self, token, admin_ids):
        self.token = token
        self.admin_user_ids = admin_ids # These are user IDs
        self.admin_chat_ids = [] # These will be populated on /start from authorized users
        self.trading_bot: TradingBot = None # Type hint
        self.bot = None
        self.application = Application.builder().token(token).build()
        self.register_handlers()
        logger.info(f"TelegramBotHandler initialized. Authorized User IDs: {self.admin_user_ids}")

    def register_handlers(self):
        # (Handlers remain largely the same, ensure they use `await self.is_authorized(update)`)
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("config", self.config_command))
        self.application.add_handler(CommandHandler("set", self.set_config_command))
        self.application.add_handler(CommandHandler("trades", self.trades_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("positions", self.positions_command))
        self.application.add_handler(CommandHandler("indicators", self.indicators_command))
        self.application.add_handler(CommandHandler("scannedpairs", self.scanned_pairs_command))
        
        self.application.add_handler(CommandHandler("starttrade", self.start_trading_command))
        self.application.add_handler(CommandHandler("stoptrade", self.stop_trading_command))
        self.application.add_handler(CommandHandler("closeall", self.close_all_positions_command)) # Ensure this is safe

        self.application.add_handler(CommandHandler("setleverage", self.set_leverage_command))
        self.application.add_handler(CommandHandler("setmode", self.set_mode_command))
        self.application.add_handler(CommandHandler("addpair", self.add_pair_command)) # For static pairs if dynamic is off
        self.application.add_handler(CommandHandler("removepair", self.remove_pair_command)) # For static pairs
        self.application.add_handler(CommandHandler("setprofit", self.set_profit_command)) # Sets daily P/L limits

        self.application.add_handler(CommandHandler("enablereal", self.enable_real_trading_command))
        self.application.add_handler(CommandHandler("disablereal", self.disable_real_trading_command))
        
        self.application.add_handler(CommandHandler("testapi", self.test_api_command))
        
        # Dynamic pair management commands (conceptual, can be expanded)
        self.application.add_handler(CommandHandler("toggledynamic", self.toggle_dynamic_selection_command))
        self.application.add_handler(CommandHandler("watchlist", self.manage_watchlist_command))


        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_error_handler(self.error_handler)

    def set_trading_bot(self, trading_bot):
        self.trading_bot = trading_bot
        self.bot = self.application.bot # Store bot instance for convenience

    async def is_authorized(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if user_id not in self.admin_user_ids:
            if update.effective_chat: # Check if chat is available
                await update.effective_chat.send_message("⛔ You are not authorized to use this bot.")
            logger.warning(f"Unauthorized access attempt by user {user_id} in chat {update.effective_chat.id if update.effective_chat else 'N/A'}")
            return False
        
        # Add user's current chat_id to admin_chat_ids if they are an admin and it's not already there
        # This allows bot to send notifications to the chat where admin last interacted.
        if update.effective_chat and update.effective_chat.id not in self.admin_chat_ids:
            self.admin_chat_ids.append(update.effective_chat.id)
            logger.info(f"Admin user {user_id} interacted. Added/confirmed chat_id {update.effective_chat.id} for notifications. Current admin_chat_ids: {self.admin_chat_ids}")
        return True

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return

        # Authorization check already adds chat_id if user is admin
        # chat_id = update.effective_chat.id
        # if chat_id not in self.admin_chat_ids: # Should be redundant due to is_authorized
        #     self.admin_chat_ids.append(chat_id)
        #     logger.info(f"Added chat ID {chat_id} to admin chats. Current admin chats: {self.admin_chat_ids}")

        keyboard = [
            [InlineKeyboardButton("🚀 Start Trading", callback_data="select_trading_mode")],
            [InlineKeyboardButton("📊 Statistics", callback_data="stats"),
             InlineKeyboardButton("📈 Positions", callback_data="positions")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="config"),
             InlineKeyboardButton("📋 Status", callback_data="status")]
        ]
        await update.message.reply_text(
            "👋 Welcome to your Binance Futures Bot!\n"
            "Use the menu or /help for commands.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        # Help text can be expanded, keeping it concise for now
        help_text = (
            "<b>Core Commands:</b>\n"
            "/start - Main menu\n"
            "/help - This message\n"
            "/status - Bot status\n"
            "/config - View current bot configuration\n"
            "/set <code>[param] [value]</code> - Change a specific configuration parameter (e.g., /set leverage 10)\n"
            "/stats - View daily profit/loss statistics\n"
            "/balance - Check your account balance\n"
            "/positions - View all open trading positions\n"
            "/indicators <code>SYMBOL</code> - Get technical indicators for a specific trading pair (e.g., /indicators BTCUSDT)\n"
            "/scannedpairs - See dynamically scanned trading candidates\n\n"
            "<b>Trading Control:</b>\n"
            "/starttrade - Start the trading bot (you'll be prompted to select a trading mode)\n"
            "/stoptrade - Stop all active trading processes\n"
            "/closeall - Close all currently open trading positions (<b>REAL MODE ONLY</b>)\n\n"
            "<b>Settings:</b>\n"
            "/setmode <code>mode</code> - Set the trading mode (options: <code>safe</code>, <code>standard</code>, <code>aggressive</code>)\n"
            "/setleverage <code>X</code> - Set the desired leverage for your trades (e.g., /setleverage 20)\n"
            "/setprofit <code>target%</code> <code>limit%</code> - Define your daily profit target and loss limit percentages (e.g., /setprofit 1 0.5)\n"
            "/addpair <code>SYMBOL</code> - Add a trading pair to your static watchlist (e.g., /addpair ETHUSDT)\n"
            "/removepair <code>SYMBOL</code> - Remove a trading pair from your static watchlist (e.g., /removepair ETHUSDT)\n\n"
            "<b>Dynamic Pairs:</b>\n"
            "/toggledynamic - Toggle dynamic pair scanning on or off\n"
            "/watchlist <code>add/remove/list</code> <code>[SYMBOL]</code> - Manage your dynamic watchlist (e.g., /watchlist add SOLUSDT, /watchlist list)\n\n"
            "<b>System:</b>\n"
            "/enablereal - Enable real trading mode\n"
            "/disablereal - Disable real trading mode (switches to test/paper trading)\n"
            # "/toggletestnet - Switch between Testnet and Production API (currently removed)\n"
            "/testapi - Test your API connection to the exchange"
        )        
        await update.message.reply_text(help_text, parse_mode=constants.ParseMode.HTML)    
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot:
            await msg_obj.reply_text("Trading bot not initialized.")
            return

        bot_cfg = self.trading_bot.config # shorthand
        dynamic_status = "✅ Enabled" if bot_cfg.get("dynamic_pair_selection") else "❌ Disabled"
        active_dynamic_pairs_text = ""
        if bot_cfg.get("dynamic_pair_selection"):
            with self.trading_bot.active_trading_pairs_lock:
                 current_dynamic_pairs = bot_cfg.get("trading_pairs", [])
            active_dynamic_pairs_text = f"\n  Active Dynamic Pairs: {', '.join(current_dynamic_pairs) if current_dynamic_pairs else 'None selected'}"

        active_trades_list = [t for t in ACTIVE_TRADES if not t.get('completed')] # Global var
        
        # Use DAILY_STATS for P/L summary for consistency
        total_pnl_usdt_today = DAILY_STATS.get('total_profit_usdt', 0.0)
        wins_today = DAILY_STATS.get('winning_trades', 0)
        losses_today = DAILY_STATS.get('losing_trades', 0)
        attempts_today = DAILY_STATS.get('total_trades',0)
        # total_completed_today = wins_today + losses_today
        # win_rate_today = (wins_today / total_completed_today * 100) if total_completed_today > 0 else 0.0
        win_rate_today_on_attempts = (wins_today / attempts_today * 100) if attempts_today > 0 else 0.0


        status_text = (
            f"📊 <b>BOT STATUS</b> ({'PRODUCTION'}) 📊\n\n"
            f"<b>Trading:</b> {'✅ Running' if self.trading_bot.running else '❌ Stopped'}\n"
            f"<b>Mode:</b> {bot_cfg.get('trading_mode', 'N/A').capitalize()}\n"
            f"<b>Leverage:</b> {bot_cfg.get('leverage', 0)}x\n"
            f"<b>Real Trading:</b> {'✅ Enabled' if bot_cfg.get('use_real_trading') else '❌ Disabled (Sim)'}\n\n"
            f"<b>Active Trades (Bot):</b> {len(active_trades_list)}\n"
            f"<b>Today's P/L (USDT):</b> ${total_pnl_usdt_today:.2f}\n"
            f"<b>Today's Trades (W/L/Total):</b> {wins_today}/{losses_today}/{attempts_today}\n"
            f"<b>Today's Win Rate (on attempts):</b> {win_rate_today_on_attempts:.1f}%\n\n"
            f"<u>Dynamic Pair Selection:</u> {dynamic_status}{active_dynamic_pairs_text}\n"
            f"  Watchlist Size: {len(bot_cfg.get('dynamic_watchlist_symbols',[]))}\n"
            f"  Max Active Dynamic: {bot_cfg.get('max_active_dynamic_pairs',0)}\n\n"
            f"<b>Monitored Pairs:</b> {', '.join(bot_cfg.get('trading_pairs', ['N/A']))}\n"
            f"<b>Daily Profit Target:</b> {bot_cfg.get('daily_profit_target_percentage', 0.0)}%\n"
            f"<b>Daily Loss Limit:</b> {bot_cfg.get('daily_loss_limit_percentage', 0.0)}%"
        )
        keyboard = [
            [InlineKeyboardButton("🚀 Start", callback_data="select_trading_mode"), InlineKeyboardButton("🛑 Stop", callback_data="stop_trading")],
            [InlineKeyboardButton("📊 Daily Stats", callback_data="stats"), InlineKeyboardButton("📈 Positions", callback_data="positions")],
            [InlineKeyboardButton("⚙️ Config", callback_data="config"), 
             InlineKeyboardButton(f"{'🔴 Disable' if bot_cfg.get('use_real_trading') else '🟢 Enable'} Real", callback_data="toggle_real_trading")]
        ]
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
            else:
                await msg_obj.reply_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
        except Exception as e: # Handle "message is not modified" error
            if "message is not modified" in str(e).lower():
                await update.callback_query.answer("Status is already up to date.")
            else:
                logger.error(f"status_command: Failed to send/edit: {e}", exc_info=True)
                # Fallback send new if edit fails for other reasons
                if update.callback_query : await msg_obj.chat.send_message(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)

    async def scanned_pairs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot:
            await update.message.reply_text("Bot not initialized.")
            return
        
        if not self.trading_bot.config.get("dynamic_pair_selection"):
            await update.message.reply_text("Dynamic pair selection is disabled. /toggledynamic to enable.")
            return

        scanned_info = "🔎 <b>Last Scanned Dynamic Candidates</b> 🔍\n"
        if not self.trading_bot.currently_scanned_pairs:
            scanned_info += "\nNo strong signals found in last scan, or scan not run yet."
        else:
            for i, sig_data in enumerate(self.trading_bot.currently_scanned_pairs[:10]): # Limit display
                scanned_info += (
                    f"\n<b>{i+1}. {sig_data['symbol']}</b>: {sig_data['action']} (Str: {sig_data['strength']})\n"
                    f"  Price: ${sig_data['price']:.4f}\n  Reasons: {'; '.join(sig_data.get('reasons',[]))[:100]}" # Truncate reasons
                )
            if len(self.trading_bot.currently_scanned_pairs) > 10:
                scanned_info += f"\n...and {len(self.trading_bot.currently_scanned_pairs)-10} more."
        
        with self.trading_bot.active_trading_pairs_lock:
            active_pairs = self.trading_bot.config.get('trading_pairs', [])
        scanned_info += f"\n\n<b>Currently Active:</b> {', '.join(active_pairs) if active_pairs else 'None'}"
            
        await update.message.reply_text(scanned_info, parse_mode=constants.ParseMode.HTML)

    async def config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot:
            await msg_obj.reply_text("Bot not initialized.")
            return

        cfg = self.trading_bot.config.copy()
        cfg['api_key'] = '****' if cfg.get('api_key') else 'Not Set'
        cfg['api_secret'] = '****' if cfg.get('api_secret') else 'Not Set'
        # GEMINI_API_KEY also if you add it

        # Create a more readable config display
        text = "⚙️ <b>BOT CONFIGURATION</b> ⚙️\n\n"
        text += f"<b>Mode:</b> {cfg['trading_mode'].capitalize()} (Lev: {cfg['leverage']}x, TP: {cfg['take_profit']}%, SL: {cfg['stop_loss']}%)\n"
        text += f"<b>Pos Size:</b> {cfg['position_size_percentage']}% of balance (Max Daily Trades: {cfg['max_daily_trades']})\n"
        text += f"<b>Daily P/L:</b> Target {cfg['daily_profit_target_percentage']}% / Limit -{cfg['daily_loss_limit_percentage']}%\n"
        text += f"<b>Real Trading:</b> {'✅ Yes' if cfg['use_real_trading'] else '❌ No (Sim)'}\n"
        # text += f"<b>Testnet:</b> {'✅ Yes' if cfg['use_testnet'] else '❌ No (Prod)'}\n"
        text += f"<b>Dynamic Pairs:</b> {'✅ Yes' if cfg['dynamic_pair_selection'] else '❌ No'}\n"
        if cfg['dynamic_pair_selection']:
            text += f"  Max Active: {cfg['max_active_dynamic_pairs']}, Scan Interval: {cfg['dynamic_scan_interval_seconds']}s\n"
            text += f"  Min Volume: {cfg['min_24h_volume_usdt_for_scan']/1_000_000:.1f}M USDT\n"
            text += f"  Watchlist: {len(cfg['dynamic_watchlist_symbols'])} symbols\n"
        else:
            text += f"<b>Static Pairs:</b> {', '.join(cfg['trading_pairs']) if cfg['trading_pairs'] else 'None'}\n"
        text += f"<b>Hedge Mode:</b> {'✅ Enabled' if cfg['hedge_mode_enabled'] else '❌ Disabled'}\n"
        # text += f"<b>AI Strategy:</b> {'✅ Enabled' if cfg.get('use_ai_strategy') else '❌ Disabled'}\n"


        keyboard = [
            [InlineKeyboardButton("Change Mode", callback_data="select_trading_mode")],
            # More buttons can be added for specific settings groups
            [InlineKeyboardButton("Back to Status", callback_data="status")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=constants.ParseMode.HTML)
            else:
                await msg_obj.reply_text(text, reply_markup=reply_markup, parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            if "message is not modified" not in str(e).lower(): logger.error(f"config_command error: {e}")


    async def set_config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot:
            await update.message.reply_text("Bot not initialized.")
            return

        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Usage: /set [param] [value]. Use /config to see current & /help for common params.")
            return

        param = args[0].lower()
        value_str = " ".join(args[1:]) # Allow spaces in value for strings

        # Sensitive keys that should not be settable this way or require confirmation
        sensitive_keys = ['api_key', 'api_secret'] # Add GEMINI_API_KEY if used
        if param in sensitive_keys:
            await update.message.reply_text(f"Parameter '{param}' is sensitive and should be set in the script's CONFIG dictionary directly for security.")
            return

        if param not in self.trading_bot.config:
            # Check if it's a sub-dict like INDICATOR_SETTINGS
            if param in INDICATOR_SETTINGS:
                 original_value_indic = INDICATOR_SETTINGS[param]
                 try:
                    if isinstance(original_value_indic, bool): new_value = value_str.lower() in ['true', '1', 'yes', 'on']
                    elif isinstance(original_value_indic, int): new_value = int(value_str)
                    elif isinstance(original_value_indic, float): new_value = float(value_str)
                    else: new_value = value_str # string
                    INDICATOR_SETTINGS[param] = new_value
                    # Re-initialize TA if settings change? Or TA reads dynamically? (Current TA reads dynamically)
                    await update.message.reply_text(f"Indicator setting updated: {param} = {new_value}")
                    return
                 except ValueError:
                    await update.message.reply_text(f"Invalid value for indicator param {param}. Expected type {type(original_value_indic).__name__}.")
                    return
            await update.message.reply_text(f"Unknown parameter: {param}. Check /config or INDICATOR_SETTINGS.")
            return

        original_value_main = self.trading_bot.config[param]
        new_value_main = None
        try:
            if isinstance(original_value_main, bool): new_value_main = value_str.lower() in ['true', '1', 'yes', 'on']
            elif isinstance(original_value_main, int): new_value_main = int(value_str)
            elif isinstance(original_value_main, float): new_value_main = float(value_str)
            elif isinstance(original_value_main, list): # For lists like trading_pairs, dynamic_watchlist_symbols
                new_value_main = [item.strip().upper() for item in value_str.split(',')] if value_str else []
            else: new_value_main = value_str # string

            self.trading_bot.config[param] = new_value_main
            msg = f"Config updated: {param} = {new_value_main}"

            if param == 'trading_mode':
                self.trading_bot.apply_trading_mode_settings() # This applies sub-settings
                msg += "\nTrading mode sub-settings (leverage, TP/SL, etc.) also applied."
            elif param == 'use_testnet':
                # Re-init API and TA
                self.trading_bot.binance_api = BinanceFuturesAPI(self.trading_bot.config)
                self.trading_bot.technical_analysis = TechnicalAnalysis(self.trading_bot.binance_api)
                msg += "\nAPI and TA modules re-initialized for new network."
            
            await update.message.reply_text(msg)
            logger.info(f"Config '{param}' changed from '{original_value_main}' to '{new_value_main}' by admin.")

        except ValueError:
            await update.message.reply_text(f"Invalid value format for {param}. Expected similar to: {type(original_value_main).__name__}.")
            return

    async def trades_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot:
            await update.message.reply_text("Bot not initialized.")
            return

        # Combine active and completed, sort by time, take recent
        # Be careful with global list modifications if other threads write to them without locks
        # For display, a copy is usually fine.
        with self.trading_bot.active_trading_pairs_lock: # Assuming this lock can cover global trade lists too, or add specific locks
            all_trades_display = ACTIVE_TRADES + COMPLETED_TRADES
        
        if not all_trades_display:
            await update.message.reply_text("No trades recorded yet.")
            return

        # Sort by 'timestamp' (unix epoch float)
        recent_trades_display = sorted(all_trades_display, key=lambda x: x.get('timestamp', 0), reverse=True)[:10]

        text = "📊 <b>RECENT TRADES</b> 📊\n"
        if not recent_trades_display: text += "\nNo trades found."
        
        for trade in recent_trades_display:
            status = trade.get('status', 'COMPLETED' if trade.get('completed') else 'ACTIVE')
            pnl_str = ""
            if trade.get('completed'):
                pnl_usdt = trade.get('profit_usdt', 0.0)
                pnl_color = "🟢" if pnl_usdt > 0 else ("🔴" if pnl_usdt < 0 else "⚪️")
                pnl_str = f"{pnl_color} PnL: ${pnl_usdt:.2f}"
            
            entry_dt = datetime.fromtimestamp(trade.get('timestamp',0)).strftime('%m-%d %H:%M')
            text += (
                f"\n<b>{trade['symbol']}</b> ({trade['action']}) {entry_dt}\n"
                f"  Status: {status}, Entry: ${trade['entry_price']:.4f} {pnl_str}\n"
                f"  Qty: {trade['quantity']}, Lev: {trade['leverage']}x, {'REAL' if trade['real_trade'] else 'SIM'}"
            )
        await update.message.reply_text(text, parse_mode=constants.ParseMode.HTML)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot:
            await msg_obj.reply_text("Bot not initialized.")
            return

        stats_text = self.trading_bot.get_daily_stats_message()
        keyboard = [[InlineKeyboardButton("🔙 Back to Status", callback_data="status")]]
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
            else:
                await msg_obj.reply_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            if "message is not modified" not in str(e).lower(): logger.error(f"stats_command error: {e}")


    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot or not self.trading_bot.binance_api:
            await update.message.reply_text("Bot or Binance API not initialized.")
            return

        status_msg = await update.message.reply_text("🔄 Fetching balance...")
        try:
            balance = self.trading_bot.binance_api.get_balance()
            if balance:
                text = (
                    f"💰 <b>ACCOUNT BALANCE</b> ({'Production'}) 💰\n\n"
                    f"Total: <b>${balance.get('total', 0):.2f}</b> USDT\n"
                    f"Available: ${balance.get('available', 0):.2f} USDT\n"
                    f"Unrealized PnL: ${balance.get('unrealized_pnl', 0):.2f} USDT"
                )
                await status_msg.edit_text(text, parse_mode=constants.ParseMode.HTML)
            else:
                await status_msg.edit_text("❌ Failed to get balance. Check API (permissions, network) or logs.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error getting balance: {str(e)}")


    async def positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot or not self.trading_bot.binance_api:
            await msg_obj.reply_text("Bot or Binance API not initialized.")
            return

        status_msg = await msg_obj.reply_text("🔄 Fetching open positions...")
        try:
            positions = self.trading_bot.binance_api.get_open_positions() # Fetches from Binance
            text = f"📈 <b>OPEN POSITIONS ON BINANCE</b> ({'Production'}) 📈\n"
            
            if not positions:
                text += "\nNo open positions found on Binance account."
            else:
                found_any = False
                for p in positions:
                    if float(p.get('positionAmt', 0)) != 0: # Only show actual open positions
                        found_any = True
                        side = "LONG" if float(p['positionAmt']) > 0 else "SHORT"
                        # API positionSide can be BOTH, LONG, SHORT in Hedge Mode
                        api_pos_side = p.get('positionSide', 'N/A') 
                        
                        initial_margin = float(p.get('initialMargin', 0))
                        unreal_pnl = float(p.get('unrealizedProfit', 0))
                        roi_pct = (unreal_pnl / initial_margin * 100) if initial_margin != 0 else 0

                        text += (
                            f"\n<b>{p['symbol']}</b> ({side}, API: {api_pos_side})\n"
                            f"  Size: {p['positionAmt']}, Entry: ${float(p['entryPrice']):.4f}\n"
                            f"  Mark: ${float(p['markPrice']):.4f}, Lev: {int(float(p['leverage']))}x\n"
                            f"  Unreal PnL: ${unreal_pnl:.2f} (ROI: {roi_pct:.2f}%)"
                        )
                if not found_any: text += "\nNo open positions with non-zero amount found."
            
            keyboard = [[InlineKeyboardButton("🔙 Back to Status", callback_data="status")]]
            await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            await status_msg.edit_text(f"❌ Error getting positions: {str(e)}")


    async def indicators_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot or not self.trading_bot.technical_analysis:
            await update.message.reply_text("Bot or TA module not initialized.")
            return

        args = context.args
        if not args:
            await update.message.reply_text("Usage: /indicators [SYMBOL]")
            return
        symbol = args[0].upper()
        status_msg = await update.message.reply_text(f"🔄 Calculating indicators for {symbol}...")

        try:
            # Use default timeframe from settings
            timeframe = self.trading_bot.technical_analysis.settings.get('candle_timeframe', '5m')
            indicators = self.trading_bot.technical_analysis.calculate_indicators(symbol, timeframe)
            
            if indicators:
                text = (
                    f"📊 <b>INDICATORS - {symbol} ({timeframe})</b> 📊\n\n"
                    f"Close Price: ${indicators['close']:.4f} (at {indicators['timestamp'].strftime('%H:%M:%S')})\n"
                    f"RSI ({self.trading_bot.technical_analysis.settings['rsi_period']}): {indicators['rsi']:.2f}\n"
                    f"EMA ({self.trading_bot.technical_analysis.settings['ema_short_period']}): {indicators['ema_short']:.4f}\n"
                    f"EMA ({self.trading_bot.technical_analysis.settings['ema_long_period']}): {indicators['ema_long']:.4f}\n"
                    f"BBands ({self.trading_bot.technical_analysis.settings['bb_period']},{self.trading_bot.technical_analysis.settings['bb_std']}):\n"
                    f"  L: ${indicators['bb_lower']:.4f}, M: ${indicators['bb_middle']:.4f}, U: ${indicators['bb_upper']:.4f}\n"
                    f"Candle: {indicators['candle_color'].capitalize()} ({indicators['candle_size_pct']:.2f}%)\n"
                )
                # Get signal based on these indicators
                signal_info = self.trading_bot.technical_analysis.get_signal(symbol, timeframe)
                if signal_info:
                    text += f"\n<b>Signal: {signal_info['action']} (Strength: {signal_info['strength']})</b>\n"
                    text += f"  Reasons: {'; '.join(signal_info.get('reasons',[]))}"

                await status_msg.edit_text(text, parse_mode=constants.ParseMode.HTML)
            else:
                await status_msg.edit_text(f"❌ Failed to calculate indicators for {symbol}. Check logs.")
        except Exception as e:
            await status_msg.edit_text(f"❌ Error calculating indicators for {symbol}: {str(e)}")


    async def start_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot:
            await update.message.reply_text("Bot not initialized.")
            return
        if self.trading_bot.running:
            await update.message.reply_text("Trading is already running. /stoptrade first if you want to change mode and restart.")
            return
        await self.show_trading_mode_selection(update, context) # Presents mode choices

    async def show_trading_mode_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # This is called by /starttrade or button callbacks to choose a mode
        text = "🔄 <b>SELECT TRADING MODE TO START</b> 🔄\n\n"
        keyboard = []
        for mode_name, settings in TRADING_MODES.items():
            text += f"<b>{mode_name.capitalize()}</b>: Lev {settings['leverage']}x, TP {settings['take_profit']}%, SL {settings['stop_loss']}%\n"
            text += f"  Desc: {settings['description']}\n\n"
            keyboard.append([InlineKeyboardButton(f"🚀 Start {mode_name.capitalize()}", callback_data=f"start_mode_{mode_name}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Cancel & View Status", callback_data="status")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=constants.ParseMode.HTML)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            if "message is not modified" not in str(e).lower(): logger.error(f"show_trading_mode_selection error: {e}")


    async def stop_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot:
            await update.message.reply_text("Bot not initialized.")
            return

        msg_obj = update.callback_query.message if update.callback_query else update.message
        if self.trading_bot.stop_trading():
            response_text = "Trading stop sequence initiated. Bot will stop opening new trades and shut down gracefully."
        else:
            response_text = "Trading is already stopped or was not running."
        
        if update.callback_query: await update.callback_query.edit_message_text(response_text)
        else: await msg_obj.reply_text(response_text)


    async def close_all_positions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot or not self.trading_bot.binance_api:
            await update.message.reply_text("Bot or API not initialized. Cannot close positions.")
            return
        if not self.trading_bot.config.get("use_real_trading"):
            await update.message.reply_text("Real trading is disabled. /closeall only works for real trades.")
            return

        status_msg = await update.message.reply_text("⚠️ Are you sure you want to MARKET CLOSE all open positions for all symbols on Binance? This is for REAL TRADES.",
                                                 reply_markup=InlineKeyboardMarkup([
                                                     [InlineKeyboardButton("✅ Yes, Close All REAL", callback_data="confirm_close_all_real")],
                                                     [InlineKeyboardButton("❌ No, Cancel", callback_data="status")]
                                                 ]))
    
    async def _confirm_close_all_positions_real(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Internal handler for the confirmation button
        if not await self.is_authorized(update): return # Redundant if button only shown to admins

        await update.callback_query.edit_message_text("🔄 Closing all REAL open positions on Binance... Please wait.")
        
        closed_count = 0
        error_count = 0
        try:
            # Fetch all symbols with open positions first.
            # This is safer than iterating through a fixed list like dynamic_watchlist_symbols
            open_positions_data = self.trading_bot.binance_api.get_open_positions()
            if not open_positions_data:
                await update.callback_query.edit_message_text("No open positions found on Binance to close.")
                return

            symbols_with_positions = list(set(pos['symbol'] for pos in open_positions_data if float(pos.get('positionAmt',0)) != 0))
            if not symbols_with_positions:
                await update.callback_query.edit_message_text("No non-zero amount open positions found on Binance.")
                return

            logger.warning(f"Admin initiated CLOSE ALL REAL POSITIONS for symbols: {symbols_with_positions}")

            for symbol in symbols_with_positions:
                # For each symbol, determine if LONG or SHORT based on current positionAmt
                # This requires fetching position details again or using the already fetched ones carefully.
                current_pos_for_symbol = next((p for p in open_positions_data if p['symbol'] == symbol and float(p.get('positionAmt',0)) != 0), None)
                if not current_pos_for_symbol: continue

                amount = float(current_pos_for_symbol['positionAmt'])
                order_side = "SELL" if amount > 0 else "BUY" # Opposite to close
                pos_side_for_order = "LONG" if amount > 0 else "SHORT" # Match the side being closed

                close_params = {
                    'symbol': symbol, 'side': order_side, 'order_type': "MARKET",
                    'quantity': abs(amount), 'reduceOnly': True
                }
                if self.trading_bot.config.get("hedge_mode_enabled"):
                    close_params['positionSide'] = pos_side_for_order
                
                logger.info(f"Attempting to close position for {symbol} by placing {order_side} MARKET order, Qty: {abs(amount)}, PosSide: {pos_side_for_order if self.trading_bot.config.get('hedge_mode_enabled') else 'N/A'}")
                
                close_order = self.trading_bot.binance_api.create_order(**close_params)
                
                if close_order and close_order.get('orderId'):
                    closed_count += 1
                    logger.info(f"Market close order for {symbol} placed. OrderID: {close_order['orderId']}")
                    # Also, try to complete the trade in the bot's internal tracking
                    active_bot_trade = next((t for t in ACTIVE_TRADES if t['symbol'] == symbol and not t.get('completed') and t.get('real_trade')), None)
                    if active_bot_trade:
                        # Need an exit price; for market close, query fill or use mark price approx
                        # This is simplified; a robust system would query actual fill.
                        approx_exit_price = self.trading_bot.binance_api.get_ticker_price(symbol) or float(current_pos_for_symbol.get('markPrice',0))
                        self.trading_bot.complete_trade(active_bot_trade['id'], approx_exit_price, "manual_admin_close_all")
                else:
                    error_count +=1
                    logger.error(f"Failed to place market close order for {symbol}. Response: {close_order}")
                time.sleep(0.2) # Small delay

            result_text = f"✅ Successfully sent close orders for {closed_count} positions."
            if error_count > 0: result_text += f"\n⚠️ Failed to close {error_count} positions. Check logs."
            await update.callback_query.edit_message_text(result_text)

        except Exception as e:
            logger.error(f"Error during /closeall execution: {e}", exc_info=True)
            await update.callback_query.edit_message_text(f"❌ Error during close all: {str(e)}")


    async def set_leverage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return
        args = context.args
        if not args:
            await update.message.reply_text(f"Current leverage: {self.trading_bot.config['leverage']}x. Usage: /setleverage [value]")
            return
        try:
            lev = int(args[0])
            if not 1 <= lev <= 125: await update.message.reply_text("Leverage must be 1-125."); return
            self.trading_bot.config['leverage'] = lev
            # Note: Leverage is typically set per symbol on Binance. Changing this config
            # means new trades will attempt to use this. Existing positions retain their leverage.
            # To change leverage for all active pairs, an additional loop would be needed.
            # For now, this only changes the config for future trades.
            self.trading_bot.apply_trading_mode_settings() # Re-apply to ensure mode settings are consistent or overridden by this
            await update.message.reply_text(f"Bot default leverage set to {lev}x for NEW trades. This may be overridden by trading mode selection unless mode is also updated.")
        except ValueError: await update.message.reply_text("Invalid number.")


    async def set_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return
        args = context.args
        if not args:
            await update.message.reply_text(
                f"Current mode: {self.trading_bot.config['trading_mode']}. "
                f"Usage: /setmode [safe|standard|aggressive]")
            return
        mode = args[0].lower()
        if mode not in TRADING_MODES:
            await update.message.reply_text(f"Invalid mode. Options: {', '.join(TRADING_MODES.keys())}")
            return
        self.trading_bot.config['trading_mode'] = mode
        self.trading_bot.apply_trading_mode_settings() # This applies leverage, TP/SL etc. from mode
        await update.message.reply_text(
            f"Trading mode set to <b>{mode}</b>. Associated settings (leverage, TP/SL, etc.) have been applied:\n"
            f" Leverage: {self.trading_bot.config['leverage']}x, TP: {self.trading_bot.config['take_profit']}%, SL: {self.trading_bot.config['stop_loss']}%",
            parse_mode=constants.ParseMode.HTML
        )


    async def add_pair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # This command is for the STATIC list of pairs if dynamic selection is OFF.
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return
        
        args = context.args
        if not args:
            await update.message.reply_text(f"Static pairs: {', '.join(self.trading_bot.config.get('static_trading_pairs',[]))}. Usage: /addpair SYMBOL")
            return
        symbol = args[0].upper()

        if self.trading_bot.config.get("dynamic_pair_selection"):
            await update.message.reply_text("Dynamic pair selection is ON. Manage pairs via /watchlist command.")
            return

        # For static list
        static_pairs = self.trading_bot.config.get("static_trading_pairs", [])
        if symbol in static_pairs:
            await update.message.reply_text(f"{symbol} already in static list.")
            return
        
        # Simple validation: check if symbol exists via price check
        if self.trading_bot.binance_api and not self.trading_bot.binance_api.get_ticker_price(symbol):
            await update.message.reply_text(f"Symbol {symbol} not found or invalid on Binance.")
            return

        static_pairs.append(symbol)
        self.trading_bot.config["static_trading_pairs"] = static_pairs
        # If not dynamic, trading_pairs should be static_trading_pairs
        if not self.trading_bot.config.get("dynamic_pair_selection"):
            with self.trading_bot.active_trading_pairs_lock:
                self.trading_bot.config["trading_pairs"] = list(static_pairs)

        await update.message.reply_text(f"{symbol} added to static list. Current: {', '.join(static_pairs)}")


    async def remove_pair_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return
        args = context.args
        if not args:
            await update.message.reply_text(f"Static pairs: {', '.join(self.trading_bot.config.get('static_trading_pairs',[]))}. Usage: /removepair SYMBOL")
            return
        symbol = args[0].upper()

        if self.trading_bot.config.get("dynamic_pair_selection"):
            await update.message.reply_text("Dynamic pair selection is ON. Manage pairs via /watchlist command.")
            return

        static_pairs = self.trading_bot.config.get("static_trading_pairs", [])
        if symbol not in static_pairs:
            await update.message.reply_text(f"{symbol} not in static list.")
            return
        
        static_pairs.remove(symbol)
        self.trading_bot.config["static_trading_pairs"] = static_pairs
        if not self.trading_bot.config.get("dynamic_pair_selection"):
            with self.trading_bot.active_trading_pairs_lock:
                self.trading_bot.config["trading_pairs"] = list(static_pairs)
        await update.message.reply_text(f"{symbol} removed. Static list: {', '.join(static_pairs)}")


    async def set_profit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE): # Daily P/L limits
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return
        args = context.args
        if len(args) < 2:
            await update.message.reply_text(
                f"Current Daily Profit Target: {self.trading_bot.config['daily_profit_target_percentage']}% "
                f"Limit: {self.trading_bot.config['daily_loss_limit_percentage']}%.\n"
                "Usage: /setprofit [target_perc] [loss_limit_perc] (e.g. /setprofit 5 3)")
            return
        try:
            target = float(args[0])
            limit = float(args[1])
            if not (0 < target <= 100 and 0 < limit <= 100):
                await update.message.reply_text("Percentages must be between 0 and 100 (exclusive of 0 for target/limit).")
                return
            self.trading_bot.config['daily_profit_target_percentage'] = target
            self.trading_bot.config['daily_loss_limit_percentage'] = limit
            await update.message.reply_text(f"Daily P/L limits set: Target {target}%, Loss Limit -{limit}%")
        except ValueError: await update.message.reply_text("Invalid numbers.")


    async def enable_real_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot: await msg_obj.reply_text("Bot not initialized."); return

        if not self.trading_bot.config["api_key"] or not self.trading_bot.config["api_secret"]:
            await msg_obj.reply_text("⚠️ API credentials not set in CONFIG. Cannot enable real trading.")
            return

        if self.trading_bot.config["use_real_trading"]:
             await msg_obj.reply_text("Real trading is already enabled.")
             return

        # Test connection first
        status_msg = await msg_obj.reply_text("🔄 Testing API for REAL trading...")
        if self.trading_bot.binance_api:
            account_info = self.trading_bot.binance_api.get_account_info()
            if account_info:
                self.trading_bot.config["use_real_trading"] = True
                network = "Production"
                await status_msg.edit_text(
                    f"✅ Real trading ENABLED on {network}!\n"
                    f"⚠️ Trades will now use REAL funds. Monitor carefully!"
                )
                logger.warning(f"REAL TRADING ENABLED by admin on {network}.")
            else:
                await status_msg.edit_text("❌ API connection failed. Real trading NOT enabled. Check keys/permissions/IP.")
        else: # Should not happen if keys are set
             await status_msg.edit_text("❌ Binance API module not available. Real trading NOT enabled.")


    async def disable_real_trading_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot: await msg_obj.reply_text("Bot not initialized."); return
        
        if not self.trading_bot.config["use_real_trading"]:
             await msg_obj.reply_text("Real trading is already disabled (Simulation mode).")
             return

        self.trading_bot.config["use_real_trading"] = False
        await msg_obj.reply_text("✅ Real trading DISABLED. Bot is now in Simulation mode.")
        logger.info("Real trading disabled by admin.")


    async def toggle_testnet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return

        if self.trading_bot.running:
            await update.message.reply_text("Cannot toggle Testnet/Production while bot is running. /stoptrade first.")
            return

        current_testnet_status = self.trading_bot.config["use_testnet"]
        self.trading_bot.config["use_testnet"] = not current_testnet_status
        new_network = "Testnet" if self.trading_bot.config["use_testnet"] else "Production"
        
        # Re-initialize API and TA with new network setting
        if self.trading_bot.config.get("api_key") and self.trading_bot.config.get("api_secret"):
            self.trading_bot.binance_api = BinanceFuturesAPI(self.trading_bot.config)
            self.trading_bot.technical_analysis = TechnicalAnalysis(self.trading_bot.binance_api)
            await update.message.reply_text(
                f"✅ Switched to <b>{new_network}</b> mode.\n"
                f"API and TA modules re-initialized. Ensure correct API keys are set for {new_network}.",
                parse_mode=constants.ParseMode.HTML
            )
            logger.info(f"Switched to {new_network} mode by admin. API re-initialized.")
        else:
            # If keys aren't set, still toggle, but warn
            self.trading_bot.binance_api = None
            self.trading_bot.technical_analysis = None
            await update.message.reply_text(
                f"✅ Switched to <b>{new_network}</b> mode conceptually.\n"
                f"⚠️ API keys not set. API/TA modules are disabled. Set keys for {new_network} to use API.",
                parse_mode=constants.ParseMode.HTML
            )
            logger.warning(f"Switched to {new_network} mode by admin, but API keys not set. API disabled.")


    async def test_api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return

        if not self.trading_bot.config.get("api_key") or not self.trading_bot.config.get("api_secret"):
            await update.message.reply_text("⚠️ API credentials not set in CONFIG. Cannot test.")
            return
        if not self.trading_bot.binance_api: # Should be init if keys are there
            await update.message.reply_text("⚠️ Binance API module not initialized despite keys. Check logs.")
            return

        status_msg = await update.message.reply_text("🔄 Testing Binance API connection...")
        try:
            account_info = self.trading_bot.binance_api.get_account_info()
            network = "Testnet" if self.trading_bot.config['use_testnet'] else "Production"
            if account_info:
                balance = self.trading_bot.binance_api.get_balance()
                text = (
                    f"✅ API Test Successful ({network})!\n\n"
                    # f"Can Trade: {account_info.get('canTrade')}\n" # Example field
                    f"Assets found: {len(account_info.get('assets',[]))}, Positions: {len(account_info.get('positions',[]))}\n"
                    f"USDT Balance: ${balance.get('total', 0):.2f} (Available: ${balance.get('available',0):.2f})" if balance else "USDT Balance: N/A"
                )
                await status_msg.edit_text(text)
            else: # get_account_info returned None
                await status_msg.edit_text(
                    f"❌ API Test Failed ({network}).\n"
                    f"get_account_info returned None. Check API Key, Secret, Permissions (Futures enabled?), and IP Whitelist on Binance."
                )
        except Exception as e: # Should be caught by get_account_info, but as fallback
            await status_msg.edit_text(f"❌ API Test Exception ({network}): {str(e)}")

    async def toggle_dynamic_selection_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return

        current_status = self.trading_bot.config.get("dynamic_pair_selection", False)
        new_status = not current_status
        self.trading_bot.config["dynamic_pair_selection"] = new_status
        
        # If turning ON, and scanner thread isn't running (e.g. bot was started with it OFF)
        if new_status and (not self.trading_bot.dynamic_pair_scanner_thread or not self.trading_bot.dynamic_pair_scanner_thread.is_alive()):
            if self.trading_bot.running: # Only start scanner if bot itself is running
                logger.info("Dynamic pair selection enabled. Starting scanner thread.")
                self.trading_bot.dynamic_pair_scanner_thread = threading.Thread(target=self.trading_bot.dynamic_pair_scan_loop)
                self.trading_bot.dynamic_pair_scanner_thread.daemon = True
                self.trading_bot.dynamic_pair_scanner_thread.start()
            else:
                logger.info("Dynamic pair selection enabled, but bot is not running. Scanner will start with /starttrade.")
        # If turning OFF, the scanner loop will self-terminate in its next check of self.config
        # and will not update trading_pairs. Bot will then use static_trading_pairs if any.

        if not new_status: # If turning OFF dynamic selection
            with self.trading_bot.active_trading_pairs_lock:
                 # Fallback to static pairs if dynamic is turned off
                self.trading_bot.config["trading_pairs"] = list(self.trading_bot.config.get("static_trading_pairs",[]))
            msg_suffix = f"\nBot will now use static pairs: {self.trading_bot.config['trading_pairs']}"
        else:
            msg_suffix = "\nDynamic scanner will now manage active pairs."

        await update.message.reply_text(f"Dynamic Pair Selection: {'✅ ENABLED' if new_status else '❌ DISABLED'}.{msg_suffix}")
        logger.info(f"Dynamic pair selection toggled to {new_status} by admin.")

    async def manage_watchlist_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not initialized."); return
        
        args = context.args
        if not args or args[0].lower() not in ['add', 'remove', 'list', 'clear']:
            await update.message.reply_text("Usage: /watchlist [add|remove|list|clear] [SYMBOL_CSV_FOR_ADD_REMOVE]")
            return

        action = args[0].lower()
        current_watchlist = self.trading_bot.config.get("dynamic_watchlist_symbols", [])

        if action == 'list':
            await update.message.reply_text(f"Dynamic Watchlist ({len(current_watchlist)}):\n{', '.join(current_watchlist) if current_watchlist else 'Empty'}")
            return
        if action == 'clear':
            self.trading_bot.config["dynamic_watchlist_symbols"] = []
            await update.message.reply_text("Dynamic watchlist cleared.")
            logger.info("Dynamic watchlist cleared by admin.")
            return

        if len(args) < 2 and action in ['add', 'remove']:
            await update.message.reply_text(f"Usage: /watchlist {action} SYMBOL1,SYMBOL2,...")
            return
        
        symbols_to_process_str = args[1]
        symbols_to_process = [s.strip().upper() for s in symbols_to_process_str.split(',')]

        if action == 'add':
            added_count = 0
            valid_new_symbols = []
            # Simple validation: check if symbol exists via price check
            if self.trading_bot.binance_api:
                for sym in symbols_to_process:
                    if self.trading_bot.binance_api.get_ticker_price(sym): # Valid symbol
                         if sym not in current_watchlist:
                            current_watchlist.append(sym)
                            added_count += 1
                    else: logger.warning(f"Watchlist add: Invalid symbol {sym} skipped.")
            else: # No API, add blindly
                for sym in symbols_to_process:
                    if sym not in current_watchlist:
                        current_watchlist.append(sym)
                        added_count += 1
            self.trading_bot.config["dynamic_watchlist_symbols"] = current_watchlist
            await update.message.reply_text(f"Added {added_count} new symbol(s) to watchlist. Total: {len(current_watchlist)}")
            if added_count > 0: logger.info(f"Admin added to watchlist: {symbols_to_process_str}")

        elif action == 'remove':
            removed_count = 0
            for sym in symbols_to_process:
                if sym in current_watchlist:
                    current_watchlist.remove(sym)
                    removed_count += 1
            self.trading_bot.config["dynamic_watchlist_symbols"] = current_watchlist
            await update.message.reply_text(f"Removed {removed_count} symbol(s) from watchlist. Total: {len(current_watchlist)}")
            if removed_count > 0: logger.info(f"Admin removed from watchlist: {symbols_to_process_str}")


    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return # Auth check critical for callbacks

        query = update.callback_query
        await query.answer() # Acknowledge callback

        data = query.data

        if data.startswith("start_mode_"):
            if self.trading_bot.running:
                await query.edit_message_text("Trading is already running. /stoptrade first to change mode and restart.")
                return
            mode = data.replace("start_mode_", "")
            if mode in TRADING_MODES:
                self.trading_bot.config["trading_mode"] = mode
                # apply_trading_mode_settings is called within start_trading
                if self.trading_bot.start_trading(): # This now applies settings and starts threads
                    # start_trading sends its own notification. Edit message to confirm action.
                    await query.edit_message_text(
                        f"✅ Trading start sequence initiated with <b>{mode.capitalize()}</b> mode.\n"
                        f"Bot is starting up. Check /status shortly.",
                        parse_mode=constants.ParseMode.HTML
                    )
                else: # Start_trading failed (e.g. API connection issue)
                    await query.edit_message_text("⚠️ Trading failed to start. Check logs for errors (e.g. API connection).")
            else: await query.edit_message_text(f"Unknown mode: {mode}")
            return

        elif data == "select_trading_mode": await self.show_trading_mode_selection(update, context)
        elif data == "stop_trading": await self.stop_trading_command(update, context) # Reuse command logic
        elif data == "status": await self.status_command(update, context)
        elif data == "config": await self.config_command(update, context)
        elif data == "stats": await self.stats_command(update, context)
        elif data == "positions": await self.positions_command(update, context)
        elif data == "confirm_close_all_real": await self._confirm_close_all_positions_real(update, context)
        elif data == "toggle_real_trading":
            # This is a quick toggle, for more checks use /enablereal or /disablereal
            if not self.trading_bot: return
            current_real_state = self.trading_bot.config.get("use_real_trading", False)
            if not current_real_state: # Trying to enable
                if not self.trading_bot.config["api_key"] or not self.trading_bot.config["api_secret"]:
                    await query.edit_message_text("⚠️ API credentials not set. Cannot enable real trading via quick toggle. Use /set api_key ...")
                    return
                # Simple test
                if self.trading_bot.binance_api and self.trading_bot.binance_api.get_account_info():
                    self.trading_bot.config["use_real_trading"] = True
                    await query.edit_message_text("✅ Real trading ENABLED via toggle. Monitor carefully!", reply_markup=None) # Remove buttons after toggle
                    logger.warning("REAL TRADING ENABLED via quick toggle by admin.")

                else:
                    await query.edit_message_text("❌ API connection test failed. Real trading NOT enabled via toggle.", reply_markup=None)
            else: # Trying to disable
                self.trading_bot.config["use_real_trading"] = False
                await query.edit_message_text("✅ Real trading DISABLED via toggle. Bot in Simulation mode.", reply_markup=None)
                logger.info("Real trading disabled via quick toggle by admin.")
            # Optionally, call status_command again to refresh the view with new state
            await self.status_command(update, context)


        # Add more button handlers here if needed

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        await update.message.reply_text("Unknown command or message. Use /help for available commands.")

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)
        # Try to notify admin if possible
        if isinstance(update, Update) and update.effective_chat:
            try:
                await self.application.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ An internal error occurred. Developers have been notified via logs."
                )
            except Exception as e_send:
                logger.error(f"Failed to send error notification to user: {e_send}")
        # For more robust error reporting, consider integrating Sentry or similar.

    def run(self):
        logger.info("Telegram bot polling started.")
        self.application.run_polling()
        logger.info("Telegram bot polling stopped.") # Won't be reached if run_polling is blocking indefinitely unless stopped by signal


def main():
    logger.info("Bot starting up...")
    
    # Initialize Telegram bot handler first
    telegram_handler = TelegramBotHandler(TELEGRAM_BOT_TOKEN, ADMIN_USER_IDS)
    
    # Initialize TradingBot and pass the telegram_handler for notifications
    # CONFIG is global here, passed to TradingBot
    trading_bot_instance = TradingBot(CONFIG, telegram_handler) # Changed variable name
    
    # Give the telegram_handler a reference to the trading_bot for command processing
    telegram_handler.set_trading_bot(trading_bot_instance)

    logger.info(f"Admin User IDs: {ADMIN_USER_IDS}")
    logger.info(f"Initial Trading Mode: {CONFIG.get('trading_mode', 'N/A')}")
    logger.info(f"Initial Use Testnet: {CONFIG.get('use_testnet', 'N/A')}")
    logger.info("Press Ctrl+C to stop the bot.")

    try:
        telegram_handler.run() # This blocks until Ctrl+C or other stop signal
    except KeyboardInterrupt:
        logger.info("Ctrl+C received. Shutting down bot...")
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
    finally:
        logger.info("Main: Initiating graceful shutdown of trading bot...")
        if trading_bot_instance and trading_bot_instance.running:
            trading_bot_instance.stop_trading() # Ensure threads are stopped
        logger.info("Bot shutdown sequence complete.")


if __name__ == "__main__":
    main()
