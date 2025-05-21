
# Bagian atas file script Python Anda

# Import utama dari python-telegram-bot untuk fungsionalitas dasar
from telegram import (
    Update,                       # Objek yang mewakili update masuk (pesan, callback query, dll.)
    InlineKeyboardButton,         # Untuk membuat tombol inline di bawah pesan
    InlineKeyboardMarkup,         # Untuk membuat layout keyboard inline
    constants                     # Berisi konstanta berguna seperti ParseMode.HTML
)

# Import dari telegram.ext untuk membangun aplikasi bot dan menangani update
from telegram.ext import (
    Application,                  # Kelas utama untuk menjalankan bot
    CommandHandler,               # Handler untuk perintah (misal: /start, /help)
    CallbackQueryHandler,         # Handler untuk callback dari tombol inline
    ContextTypes,                 # Tipe untuk objek context yang diteruskan ke handler
    MessageHandler,               # Handler untuk pesan teks biasa (bukan perintah)
    filters                       # Untuk memfilter tipe update (misal: teks, perintah)
)

# Import spesifik untuk menangani error dari API Telegram
from telegram.error import (
    BadRequest,                   # Error jika request ke API Telegram salah format atau tidak valid
    TelegramError                 # Kelas dasar untuk semua error dari pustaka ini (bisa juga digunakan untuk error handler umum)
    # Anda bisa menambahkan error spesifik lainnya jika perlu, contoh:
    # TimedOut, NetworkError, Forbidden, Unauthorized, ChatMigrated, RetryAfter, etc.
)

# Import lain yang mungkin sudah Anda miliki (tidak terkait langsung dengan error saat ini, tapi penting untuk bot)
import asyncio      # Untuk operasi asinkron (digunakan secara internal oleh python-telegram-bot v20+)
import logging      # Untuk logging aktivitas dan error bot
import json         # Untuk parsing JSON (misalnya, dari Gemini atau konfigurasi)
import os           # Untuk interaksi dengan sistem operasi (misalnya, membaca environment variables)
from dotenv import load_dotenv # Untuk memuat environment variables dari file .env


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
import pandas_ta as ta
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram import (
    Update,                       # Objek yang mewakili update masuk (pesan, callback query, dll.)
    InlineKeyboardButton,         # Untuk membuat tombol inline di bawah pesan
    InlineKeyboardMarkup,         # Untuk membuat layout keyboard inline
    constants                     # Berisi konstanta berguna seperti ParseMode.HTML
)

# Import dari telegram.ext untuk membangun aplikasi bot dan menangani update
from telegram.ext import (
    Application,                  # Kelas utama untuk menjalankan bot
    CommandHandler,               # Handler untuk perintah (misal: /start, /help)
    CallbackQueryHandler,         # Handler untuk callback dari tombol inline
    ContextTypes,                 # Tipe untuk objek context yang diteruskan ke handler
    MessageHandler,               # Handler untuk pesan teks biasa (bukan perintah)
    filters                       # Untuk memfilter tipe update (misal: teks, perintah)
)

# Import spesifik untuk menangani error dari API Telegram
from telegram.error import (
    BadRequest,                   # Error jika request ke API Telegram salah format atau tidak valid
    TelegramError                 # Kelas dasar untuk semua error dari pustaka ini (bisa juga digunakan untuk error handler umum)
    # Anda bisa menambahkan error spesifik lainnya jika perlu, contoh:
    # TimedOut, NetworkError, Forbidden, Unauthorized, ChatMigrated, RetryAfter, etc.
)
# --- Integrasi Gemini AI ---
import os
from dotenv import load_dotenv
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None # Placeholder
# --- End Integrasi Gemini AI ---

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Load Environment Variables ---
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_ENV", "YOUR_FALLBACK_TELEGRAM_TOKEN")
ADMIN_USER_IDS_STR = os.getenv("ADMIN_USER_IDS_ENV", "")
try:
    ADMIN_USER_IDS = [int(admin_id.strip()) for admin_id in ADMIN_USER_IDS_STR.split(',') if admin_id.strip()]
except ValueError:
    logger.error("ADMIN_USER_IDS_ENV format error. Expected comma-separated integers.")
    ADMIN_USER_IDS = []

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY_ENV", "YOUR_FALLBACK_BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET_ENV", "YOUR_FALLBACK_BINANCE_API_SECRET")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY_ENV")
# --- End Load Environment Variables ---

BINANCE_API_URL = "https://fapi.binance.com"

# --- Gemini AI Model Configuration ---
gemini_model_instance = None
if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model_instance = genai.GenerativeModel('gemini-1.5-flash-latest')
        logger.info("Gemini AI Model configured successfully with 'gemini-1.5-flash-latest'.")
    except Exception as e:
        logger.error(f"Failed to configure Gemini AI: {e}")
        gemini_model_instance = None
elif not GEMINI_AVAILABLE:
    logger.warning("Google Generative AI library not installed. Gemini AI integration will be disabled.")
else:
    logger.warning("GEMINI_API_KEY_ENV not found in .env file. Gemini AI integration will be disabled.")
# --- End Gemini AI Model Configuration ---


TRADING_MODES = {
    "safe": {"leverage": 5, "take_profit": 0.5, "stop_loss": 0.3, "position_size_percent": 8, "max_daily_trades": 8, "description": "Safe: Lower risk"},
    "standard": {"leverage": 10, "take_profit": 0.8, "stop_loss": 0.4, "position_size_percent": 12, "max_daily_trades": 12, "description": "Standard: Balanced"},
    "aggressive": {"leverage": 15, "take_profit": 1.2, "stop_loss": 0.6, "position_size_percent": 18, "max_daily_trades": 18, "description": "Aggressive: Higher risk/reward"}
}

DEFAULT_INDICATOR_SETTINGS = {
    "rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 65,
    "ema_short_period": 12, "ema_long_period": 26,
    "bb_period": 20, "bb_std": 2.0,
    "candle_timeframe": "5m", "signal_strength_threshold": 25,
    "klines_limit_for_indicator_calc": 150,
    "description": "Default Balanced Profile"
}
INDICATOR_SETTINGS = DEFAULT_INDICATOR_SETTINGS.copy() # GLOBAL, MUTABLE DICTIONARY


AI_MODE_CONFIG = {
    "enabled_on_start": False,
    "use_gemini_for_analysis": True,
    "optimization_interval_seconds": 3600,
    "market_volatility_threshold_low": 1.5,
    "market_volatility_threshold_high": 4.0,
    "indicator_profiles": {
        "conservative": {"rsi_period": 18, "rsi_oversold": 30, "rsi_overbought": 70, "ema_short_period": 15, "ema_long_period": 30, "bb_period": 25, "bb_std": 2.2, "candle_timeframe": "5m", "signal_strength_threshold": 30, "klines_limit_for_indicator_calc": 150, "description": "Rule-Based Conservative"},
        "balanced": {"rsi_period": 14, "rsi_oversold": 35, "rsi_overbought": 65, "ema_short_period": 12, "ema_long_period": 26, "bb_period": 20, "bb_std": 2.0, "candle_timeframe": "5m", "signal_strength_threshold": 25, "klines_limit_for_indicator_calc": 150, "description": "Rule-Based Balanced"},
        "responsive": {"rsi_period": 10, "rsi_oversold": 40, "rsi_overbought": 60, "ema_short_period": 9, "ema_long_period": 21, "bb_period": 15, "bb_std": 1.8, "candle_timeframe": "5m", "signal_strength_threshold": 20, "klines_limit_for_indicator_calc": 150, "description": "Rule-Based Responsive"}
    }
}

CONFIG = {
    "api_key": BINANCE_API_KEY, "api_secret": BINANCE_API_SECRET,
    "trading_enabled_on_start": False,
    "trading_mode": "standard",
    "use_real_trading": False,
    "static_trading_pairs": ["BTCUSDT", "ETHUSDT"],
    "dynamic_pair_selection": True,
    "dynamic_watchlist_symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT", "LINKUSDT", "TRXUSDT", "LTCUSDT", "UNIUSDT", "ATOMUSDT", "ETCUSDT", "BCHUSDT", "XLMUSDT", "NEARUSDT", "ALGOUSDT", "VETUSDT", "FTMUSDT", "MANAUSDT", "SANDUSDT", "APEUSDT", "AXSUSDT", "FILUSDT", "ICPUSDT", "AAVEUSDT", "MKRUSDT", "COMPUSDT", "GRTUSDT", "RUNEUSDT", "THETAUSDT", "EGLDUSDT"],
    "max_active_dynamic_pairs": 3,
    "min_24h_volume_usdt_for_scan": 10000000,
    "dynamic_scan_interval_seconds": 300,
    "api_call_delay_seconds_in_scan": 0.3,
    "leverage": 10, "take_profit": 1.0, "stop_loss": 0.5,
    "position_size_percentage": 10.0, "max_daily_trades": 15,
    "use_percentage_for_pos_size": True, "fixed_position_size_usdt": 100,
    "daily_profit_target_percentage": 5.0, "daily_loss_limit_percentage": 3.0,
    "signal_check_interval_seconds": 30, "post_trade_entry_delay_seconds": 5,
    "hedge_mode_enabled": True,
    "ai_mode_active": AI_MODE_CONFIG["enabled_on_start"],
}

ACTIVE_TRADES = []
COMPLETED_TRADES = []
DAILY_STATS = {"date": datetime.now().strftime("%Y-%m-%d"), "total_trades": 0, "winning_trades": 0, "losing_trades": 0, "total_profit_percentage_leveraged": 0.0, "total_profit_usdt": 0.0, "starting_balance_usdt": 0.0, "current_balance_usdt": 0.0, "roi_percentage": 0.0}
SYMBOL_INFO = {}


class BinanceFuturesAPI:
    def __init__(self, config_dict):
        self.config_dict = config_dict
        self.api_key = config_dict["api_key"]
        self.api_secret = config_dict["api_secret"]
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
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"API error response for get_account_info: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 401:
                logger.error("Authentication failed (401): Invalid API key or secret, or general auth issue. Check Binance key permissions and IP whitelist.")
            elif e.response.status_code == 403:
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
            df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True)
            return df
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get klines for {symbol}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing klines for {symbol}: {e}")
            return None

    def get_ticker_24hr(self, symbol: str = None) -> list | dict | None:
        try:
            url = f"{self.base_url}/fapi/v1/ticker/24hr"
            params = {}
            if symbol:
                params['symbol'] = symbol.upper()
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error fetching 24hr ticker: {http_err} - {http_err.response.text if http_err.response else 'No response text'}")
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
        try:
            url = f"{self.base_url}/fapi/v1/marginType"
            timestamp = int(time.time() * 1000)
            params = {'symbol': symbol, 'marginType': margin_type.upper(), 'timestamp': timestamp}
            params['signature'] = self._generate_signature(params)
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Changed margin type for {symbol} to {margin_type}")
                return response.json()
            elif response.status_code == 400 and response.json().get("code") == -4046:
                 logger.info(f"Margin type for {symbol} is already {margin_type}.")
                 return response.json()
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
            params = {'dualSidePosition': 'true' if dual_side_position else 'false', 'timestamp': timestamp}
            params['signature'] = self._generate_signature(params)
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                mode_str = "Hedge Mode" if dual_side_position else "One-way Mode"
                logger.info(f"Successfully set position mode to {mode_str}. Response: {response.json().get('msg', 'OK')}")
                return response.json()
            elif response.status_code == 400 and response.json().get("code") == -4059:
                mode_str = "Hedge Mode" if dual_side_position else "One-way Mode"
                logger.info(f"Position mode is already set to {mode_str}.")
                return {"code": 200, "msg": "No need to change position side."}
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
            params = {'symbol': symbol, 'side': side.upper(), 'type': order_type.upper(), 'timestamp': timestamp}
            if order_type.upper() not in ['MARKET', 'STOP_MARKET', 'TAKE_PROFIT_MARKET']: params['timeInForce'] = time_in_force
            if quantity: params['quantity'] = quantity
            if price and order_type.upper() not in ['MARKET', 'STOP_MARKET', 'TAKE_PROFIT_MARKET']: params['price'] = price
            if stop_price and order_type.upper() in ['STOP', 'STOP_MARKET', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET']: params['stopPrice'] = stop_price
            if position_side: params['positionSide'] = position_side.upper()
            if reduce_only: params['reduceOnly'] = 'true'
            if close_position: params['closePosition'] = 'true'
            params['signature'] = self._generate_signature(params)
            response = requests.post(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Created order for {symbol}: {side} {order_type} Qty: {quantity} PosSide: {position_side}. ID: {response.json()['orderId']}")
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
                return [p for p in account_info['positions'] if float(p.get('positionAmt', 0)) != 0]
            elif account_info is None:
                 logger.warning("Could not get account info to fetch open positions.")
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
            else: logger.error("cancel_order: orderId or origClientOrderId must be provided."); return None
            params['signature'] = self._generate_signature(params)
            response = requests.delete(url, params=params, headers=self._get_headers(), timeout=10)
            if response.status_code == 200:
                logger.info(f"Canceled order {order_id or orig_client_order_id} for {symbol}.")
                return response.json()
            else:
                if response.json().get("code") == -2011: # "Unknown order sent."
                    logger.warning(f"Order {order_id or orig_client_order_id} for {symbol} not found or already processed (cancel attempt).")
                    return response.json()
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
        global SYMBOL_INFO
        if symbol in SYMBOL_INFO:
            return SYMBOL_INFO[symbol]
        try:
            exchange_info_data = self.get_exchange_info()
            if not exchange_info_data: return None
            for sym_data in exchange_info_data.get('symbols', []):
                if sym_data['symbol'] == symbol:
                    s_info = {
                        'pricePrecision': sym_data['pricePrecision'],
                        'quantityPrecision': sym_data['quantityPrecision'],
                        'minQty': next((f['minQty'] for f in sym_data['filters'] if f['filterType'] == 'LOT_SIZE'), '0.001'),
                        'tickSize': next((f['tickSize'] for f in sym_data['filters'] if f['filterType'] == 'PRICE_FILTER'), '0.01'),
                        'minNotional': next((f['notional'] for f in sym_data['filters'] if f['filterType'] == 'MIN_NOTIONAL'), '5.0'),
                        # Extract stepSize for quantity rounding
                        'stepSize': next((f['stepSize'] for f in sym_data['filters'] if f['filterType'] == 'LOT_SIZE'), '0.001')
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
            if 'e-' in value_str.lower():
                try:
                    return int(value_str.lower().split('e-')[-1])
                except ValueError:
                    pass
            return len(value_str.split('.')[1].rstrip('0'))
        return 0

    def round_price(self, symbol: str, price: float) -> float:
        symbol_info_data = self.get_symbol_info(symbol)
        if not symbol_info_data or 'tickSize' not in symbol_info_data: return round(price, 8)
        tick_size_str = symbol_info_data['tickSize']
        precision = self.get_decimal_places(tick_size_str)
        tick_size = float(tick_size_str)
        if tick_size == 0: return round(price, precision)
        return round(round(price / tick_size) * tick_size, precision)

    def round_quantity(self, symbol: str, quantity: float) -> float:
        symbol_info_data = self.get_symbol_info(symbol)
        # Prefer stepSize from symbol_info if available, otherwise use minQty as fallback for step_size_str
        step_size_str = symbol_info_data.get('stepSize', symbol_info_data.get('minQty')) if symbol_info_data else '0.001'
        if not step_size_str: # Ultimate fallback if somehow both are missing
             step_size_str = '0.001' # Default if minQty also not found (should not happen with proper get_symbol_info)
             logger.warning(f"[{symbol}] No stepSize or minQty in symbol_info, using default step for quantity rounding.")

        precision = self.get_decimal_places(step_size_str)
        step_size = float(step_size_str)
        if step_size == 0: return round(quantity, precision)
        return round(np.floor(quantity / step_size) * step_size, precision)

    def get_balance(self):
        try:
            account_info = self.get_account_info()
            if account_info and 'assets' in account_info:
                for asset in account_info['assets']:
                    if asset['asset'] == 'USDT':
                        return {'total': float(asset.get('walletBalance', 0)),
                                'available': float(asset.get('availableBalance', 0)),
                                'unrealized_pnl': float(asset.get('unrealizedProfit', 0))}
            elif account_info is None:
                logger.warning("Could not get account info for balance (API call failed or auth error).")
            return None
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None

    def get_atr(self, symbol: str, timeframe: str = '1h', period: int = 14, limit: int = 100) -> tuple[float | None, float | None]:
        df = self.get_klines(symbol, timeframe, limit=limit + period)
        if df is None or df.empty or len(df) < period:
            logger.warning(f"[{symbol}] Insufficient klines data for ATR (got {len(df) if df is not None else 0}, need >{period}).")
            return None, None
        try:
            current_price = df['close'].iloc[-1]
            atr_series = ta.atr(df['high'], df['low'], df['close'], length=period)
            if atr_series is None or atr_series.empty or atr_series.isnull().all():
                logger.warning(f"[{symbol}] ATR calculation returned None, empty, or all NaNs.")
                return None, current_price
            latest_atr = atr_series.iloc[-1]
            if pd.isna(latest_atr):
                 logger.warning(f"[{symbol}] Latest ATR value is NaN.")
                 return None, current_price
            return latest_atr, current_price
        except Exception as e:
            logger.error(f"[{symbol}] Error calculating ATR: {e}")
            return None, None


class TechnicalAnalysis:
    def __init__(self, binance_api_instance):
        self.binance_api = binance_api_instance

    def calculate_indicators(self, symbol: str, timeframe: str = None) -> dict | None:
        global INDICATOR_SETTINGS
        current_settings = INDICATOR_SETTINGS.copy()

        tf = timeframe if timeframe else current_settings.get('candle_timeframe', '5m')
        limit_req = current_settings.get('klines_limit_for_indicator_calc', 150)

        max_period = max(current_settings.get('rsi_period', 14),
                         current_settings.get('ema_long_period', 26),
                         current_settings.get('bb_period', 20))
        required_klines = max_period + 50
        if limit_req < required_klines: limit_req = required_klines

        df = self.binance_api.get_klines(symbol, tf, limit=limit_req)
        if df is None or df.empty or len(df) < max_period :
            logger.error(f"[{symbol}@{tf}] Insufficient klines ({len(df) if df is not None else 0}, need >{max_period}) for indicators.")
            return None

        try:
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col not in df.columns: logger.error(f"[{symbol}@{tf}] Missing column: '{col}'."); return None
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df.dropna(subset=['open', 'high', 'low', 'close', 'volume'], inplace=True)
            if len(df) < max_period: logger.error(f"[{symbol}@{tf}] Insufficient klines after NaN drop."); return None

            df['rsi'] = ta.rsi(close=df['close'], length=current_settings['rsi_period'])
            df['ema_short'] = ta.ema(close=df['close'], length=current_settings['ema_short_period'])
            df['ema_long'] = ta.ema(close=df['close'], length=current_settings['ema_long_period'])

            bb_df = ta.bbands(close=df['close'], length=current_settings['bb_period'], std=current_settings['bb_std'])
            if bb_df is not None and not bb_df.empty:
                std_str = f"{current_settings['bb_std']}"
                l_col, m_col, u_col = f'BBL_{current_settings["bb_period"]}_{std_str}', f'BBM_{current_settings["bb_period"]}_{std_str}', f'BBU_{current_settings["bb_period"]}_{std_str}'
                if l_col not in bb_df.columns and isinstance(current_settings['bb_std'], float) and current_settings['bb_std'] == int(current_settings['bb_std']):
                    std_alt = str(int(current_settings['bb_std']))
                    l_alt, m_alt, u_alt = f'BBL_{current_settings["bb_period"]}_{std_alt}', f'BBM_{current_settings["bb_period"]}_{std_alt}', f'BBU_{current_settings["bb_period"]}_{std_alt}'
                    if l_alt in bb_df.columns: l_col, m_col, u_col = l_alt, m_alt, u_alt

                if l_col in bb_df.columns: df['bb_lower'], df['bb_middle'], df['bb_upper'] = bb_df[l_col], bb_df[m_col], bb_df[u_col]
                else: df['bb_lower'], df['bb_middle'], df['bb_upper'] = pd.NA, pd.NA, pd.NA; logger.warning(f"[{symbol}@{tf}] BB cols not found ({l_col}).")
            else: df['bb_lower'], df['bb_middle'], df['bb_upper'] = pd.NA, pd.NA, pd.NA; logger.warning(f"[{symbol}@{tf}] ta.bbands failed.")

            df['candle_color'] = np.where(df['close'] >= df['open'], 'green', 'red')
            df['candle_size_pct'] = ((df['close'] - df['open']).abs() / df['open'].replace(0, np.nan) * 100).fillna(0.0)

            latest = df.iloc[-1].copy()
            prev = df.iloc[-2].copy() if len(df) > 1 else None

            crit_cols = ['rsi', 'ema_short', 'ema_long', 'bb_middle', 'bb_lower', 'bb_upper']
            if latest[crit_cols].isnull().any():
                logger.warning(f"[{symbol}@{tf}] NaN in critical TA: {latest[crit_cols].isnull()[latest[crit_cols].isnull()].index.tolist()}.")
                return None

            return {'symbol': symbol, 'timestamp': latest['timestamp'], 'open': latest['open'], 'high': latest['high'], 'low': latest['low'], 'close': latest['close'], 'volume': latest['volume'], 'rsi': latest['rsi'], 'ema_short': latest['ema_short'], 'ema_long': latest['ema_long'], 'bb_upper': latest['bb_upper'], 'bb_middle': latest['bb_middle'], 'bb_lower': latest['bb_lower'], 'candle_color': latest['candle_color'], 'candle_size_pct': latest['candle_size_pct'], 'previous': prev, 'klines_df_tail': df[['open', 'high', 'low', 'close', 'volume', 'timestamp']].tail(10)}
        except Exception as e:
            logger.error(f"[{symbol}@{tf}] Error in calc_indicators: {e}", exc_info=True)
            return None

    def get_signal(self, symbol, timeframe=None):
        global INDICATOR_SETTINGS
        current_settings = INDICATOR_SETTINGS

        tf = timeframe if timeframe else current_settings['candle_timeframe']
        indicators = self.calculate_indicators(symbol, tf)
        if not indicators: return None

        signal = {'symbol': symbol, 'timestamp': indicators['timestamp'], 'price': indicators['close'], 'action': 'WAIT', 'strength': 0, 'reasons': []}

        req_fields = ['rsi', 'ema_short', 'ema_long', 'bb_upper', 'bb_lower', 'bb_middle', 'close', 'open']
        if any(pd.isna(indicators.get(f)) for f in req_fields):
            logger.warning(f"[{symbol}@{tf}] NaN in critical indicators for signal. Skipping."); return signal

        rsi_os = indicators['rsi'] < current_settings['rsi_oversold']
        rsi_ob = indicators['rsi'] > current_settings['rsi_overbought']
        green = indicators['candle_color'] == 'green'
        red = indicators['candle_color'] == 'red'

        if rsi_os and green: signal['action'] = 'LONG'; signal['strength'] += 30; signal['reasons'].append(f"RSI OS ({indicators['rsi']:.1f}) G")
        elif rsi_ob and red: signal['action'] = 'SHORT'; signal['strength'] += 30; signal['reasons'].append(f"RSI OB ({indicators['rsi']:.1f}) R")

        ema_bull = indicators['close'] > indicators['ema_short'] > indicators['ema_long']
        ema_bear = indicators['close'] < indicators['ema_short'] < indicators['ema_long']

        if ema_bull:
            if signal['action'] == 'LONG': signal['strength'] += 20; signal['reasons'].append("EMA Bull Cnf")
            elif signal['action'] == 'WAIT': signal['action'] = 'LONG'; signal['strength'] += 20; signal['reasons'].append("EMA Bull X")
        elif ema_bear:
            if signal['action'] == 'SHORT': signal['strength'] += 20; signal['reasons'].append("EMA Bear Cnf")
            elif signal['action'] == 'WAIT': signal['action'] = 'SHORT'; signal['strength'] += 20; signal['reasons'].append("EMA Bear X")

        price_abv_bbu = indicators['close'] > indicators['bb_upper']
        price_blw_bbl = indicators['close'] < indicators['bb_lower']

        if price_abv_bbu:
            if signal['action'] == 'SHORT': signal['strength'] += 20; signal['reasons'].append("BB > Upper Cnf")
            elif signal['action'] == 'WAIT': signal['action'] = 'SHORT'; signal['strength'] += 15; signal['reasons'].append("BB > Upper Pot")
        elif price_blw_bbl:
            if signal['action'] == 'LONG': signal['strength'] += 20; signal['reasons'].append("BB < Lower Cnf")
            elif signal['action'] == 'WAIT': signal['action'] = 'LONG'; signal['strength'] += 15; signal['reasons'].append("BB < Lower Pot")

        sig_thresh = current_settings.get('signal_strength_threshold', 30)
        if signal['action'] != 'WAIT' and signal['strength'] < sig_thresh:
            orig_action = signal['action']
            signal['action'] = 'WAIT'; signal['reasons'] = [f"Str {signal['strength']}/{sig_thresh} low for {orig_action}"]; signal['strength'] = 0
        elif signal['action'] == 'WAIT' and not signal['reasons']: signal['reasons'].append(f"No TA signal (Str {signal['strength']}/{sig_thresh})")

        logger.log(logging.INFO if signal['action'] != 'WAIT' else logging.DEBUG, f"[{symbol}@{tf}] Signal: {signal['action']}, Str: {signal['strength']}, Px: {signal['price']:.4f}, R: {';'.join(signal['reasons'])}")
        return signal


class TradingBot:
    def __init__(self, config_obj, telegram_bot_instance=None):
        self.config = config_obj
        self.telegram_bot = telegram_bot_instance
        self.running = False
        self.signal_check_thread = None
        self.notification_queue = queue.Queue()
        self.notification_thread = None

        if config_obj.get("api_key") and config_obj.get("api_secret"):
            self.binance_api = BinanceFuturesAPI(config_obj)
            self.technical_analysis = TechnicalAnalysis(self.binance_api)
        else:
            self.binance_api = None; self.technical_analysis = None
            logger.warning("Binance API key/secret not configured. Limited mode.")

        self.dynamic_pair_scanner_thread = None
        self.currently_scanned_pairs = []
        self.active_trading_pairs_lock = threading.Lock()
        self.ai_optimizer_thread = None
        self.last_ai_optimization_time = 0
        self.reset_daily_stats()

    def reset_daily_stats(self):
        DAILY_STATS["date"] = datetime.now().strftime("%Y-%m-%d")
        DAILY_STATS["total_trades"] = 0; DAILY_STATS["winning_trades"] = 0; DAILY_STATS["losing_trades"] = 0
        DAILY_STATS["total_profit_percentage_leveraged"] = 0.0; DAILY_STATS["total_profit_usdt"] = 0.0
        if self.binance_api and self.config.get("use_real_trading"):
            try:
                bal = self.binance_api.get_balance()
                if bal: DAILY_STATS["starting_balance_usdt"] = bal['total']; DAILY_STATS["current_balance_usdt"] = bal['total']; DAILY_STATS["roi_percentage"] = 0.0
                else: DAILY_STATS["starting_balance_usdt"] = 0.0; DAILY_STATS["current_balance_usdt"] = 0.0
            except Exception as e: logger.error(f"Err daily stats balance: {e}"); DAILY_STATS["starting_balance_usdt"] = 0.0; DAILY_STATS["current_balance_usdt"] = 0.0
        else: DAILY_STATS["starting_balance_usdt"] = 0.0; DAILY_STATS["current_balance_usdt"] = 0.0; DAILY_STATS["roi_percentage"] = 0.0

    def send_notification(self, message, keyboard=None):
        if not self.telegram_bot or not hasattr(self.telegram_bot, 'admin_chat_ids') or not self.telegram_bot.admin_chat_ids:
            logger.warning("No Telegram bot/admin_chat_ids for notification.")
            return
        try: self.notification_queue.put((message, keyboard))
        except Exception as e: logger.error(f"Error queueing notification: {e}")

    def process_notification_queue(self):
        logger.info("Starting notification queue processor thread")
        loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        while self.running or not self.notification_queue.empty():
            try:
                message, keyboard = self.notification_queue.get(block=True, timeout=1.0)
                if message is None and keyboard is None: break
                if not self.telegram_bot or not self.telegram_bot.admin_chat_ids: continue

                for chat_id in self.telegram_bot.admin_chat_ids:
                    try:
                        payload = {'chat_id': chat_id, 'text': message, 'parse_mode': constants.ParseMode.HTML}
                        if keyboard: payload['reply_markup'] = InlineKeyboardMarkup(keyboard)
                        future = asyncio.run_coroutine_threadsafe(self.telegram_bot.application.bot.send_message(**payload), loop)
                        future.result(timeout=10)
                    except Exception as e1:
                        logger.error(f"Failed to send notification (asyncio) to {chat_id}: {e1}. Fallback.")
                        try:
                            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                            fb_payload = {'chat_id': chat_id, 'text': message, 'parse_mode': 'HTML'}
                            if keyboard:
                                fb_payload['reply_markup'] = json.dumps({'inline_keyboard': [[{'text':b.text, 'callback_data':b.callback_data} for b in r] for r in keyboard]})
                            requests.post(url, json=fb_payload, timeout=10).raise_for_status()
                        except Exception as e2: logger.error(f"Fallback also failed for {chat_id}: {e2}")
                self.notification_queue.task_done()
            except queue.Empty: continue
            except Exception as e: logger.error(f"Error processing notification queue: {e}", exc_info=True)
        loop.close(); logger.info("Notification queue processor thread stopped.")

    async def _call_gemini_api(self, prompt: str) -> str | None:
        if not gemini_model_instance:
            return None
        try:
            response = await asyncio.to_thread(gemini_model_instance.generate_content, prompt)
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"): cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"): cleaned_text = cleaned_text[:-3]
            return cleaned_text.strip()
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}", exc_info=True)
            if "API_KEY_INVALID" in str(e).upper() or "PERMISSION_DENIED" in str(e).upper():
                 logger.critical("GEMINI API KEY INVALID OR PERMISSION DENIED.")
            return None

    async def get_gemini_trading_mode(self, market_summary: str) -> str | None:
        prompt = f"""
As an expert crypto futures trading strategist, analyze the following market summary:
"{market_summary}"
Optimal trading mode? Choose ONE: "safe", "standard", "aggressive".
Response MUST be JSON: {{"trading_mode": "chosen_mode"}}
"""
        response_text = await self._call_gemini_api(prompt)
        if response_text:
            try:
                data = json.loads(response_text)
                mode = data.get("trading_mode")
                if mode in TRADING_MODES: logger.info(f"Gemini recommended trading mode: {mode}"); return mode
                logger.warning(f"Gemini invalid trading mode: {mode} from: {response_text}")
            except json.JSONDecodeError: logger.error(f"Failed to parse Gemini JSON for trading mode: {response_text}")
        return None

    async def get_gemini_indicator_settings(self, market_summary: str) -> dict | None:
        prompt = f"""
Expert crypto futures strategist (5-min TF). Analyze market:
"{market_summary}"
Recommend OPTIMAL JSON indicator settings:
- "rsi_period": int (7-25)
- "rsi_oversold": int (20-40)
- "rsi_overbought": int (60-80, > rsi_oversold)
- "ema_short_period": int (5-15)
- "ema_long_period": int (18-35, > ema_short_period + 4)
- "bb_period": int (10-30)
- "bb_std": float (1.5-2.5, one decimal)
- "signal_strength_threshold": int (15-35)
- "description": string (e.g., "Gemini Volatile Profile")
Example: {{"rsi_period":12, "rsi_oversold":30, ... , "description":"Gemini Profile"}}
"""
        response_text = await self._call_gemini_api(prompt)
        if response_text:
            try:
                settings = json.loads(response_text)
                req_keys = ["rsi_period", "rsi_oversold", "rsi_overbought", "ema_short_period", "ema_long_period", "bb_period", "bb_std", "signal_strength_threshold", "description"]
                if not all(key in settings for key in req_keys):
                    logger.warning(f"Gemini indicator settings missing keys: {response_text}"); return None
                if not (7<=settings["rsi_period"]<=25 and 20<=settings["rsi_oversold"]<=40 and 60<=settings["rsi_overbought"]<=80 and settings["rsi_overbought"]>settings["rsi_oversold"] and \
                        5<=settings["ema_short_period"]<=15 and 18<=settings["ema_long_period"]<=35 and settings["ema_long_period"]>(settings["ema_short_period"]+4) and \
                        10<=settings["bb_period"]<=30 and 1.5<=settings["bb_std"]<=2.5 and 15<=settings["signal_strength_threshold"]<=35):
                    logger.warning(f"Gemini indicator settings out of range: {settings}"); return None
                settings.setdefault("candle_timeframe", "5m")
                settings.setdefault("klines_limit_for_indicator_calc", 150)
                logger.info(f"Gemini recommended indicator settings: {settings.get('description')}")
                return settings
            except json.JSONDecodeError: logger.error(f"Failed to parse Gemini JSON for indicators: {response_text}")
            except (TypeError, KeyError) as e_val: logger.error(f"Validation error for Gemini settings: {e_val} in {response_text}")
        return None

    async def run_ai_optimizer_cycle(self):
        global INDICATOR_SETTINGS
        if not self.config.get("ai_mode_active", False): return

        logger.info("🤖 AI Optimizer: Starting settings cycle...")
        current_settings_summary_detailed = self.get_current_settings_summary_for_ai_notification() # Detail untuk notif
        changes_made = []
        volatility_percent, btc_price, market_trend = 0.0, None, "Undetermined" # Add trend later

        if self.binance_api:
            atr_val, btc_price_val = self.binance_api.get_atr("BTCUSDT", timeframe='1h', period=14, limit=50)
            btc_price = btc_price_val
            if atr_val and btc_price and btc_price > 0:
                volatility_percent = (atr_val / btc_price) * 100
                logger.info(f"🤖 AI: BTC 1h ATR Volatility: {volatility_percent:.2f}% (Price: ${btc_price:.2f})")
            else: logger.warning("🤖 AI: Could not determine BTC volatility accurately.")
            # TODO: Add simple trend detection

        market_summary = f"BTC Volatility (1h ATR): {volatility_percent:.2f}%. BTC Price: ${btc_price if btc_price else 'N/A'}. Trend: {market_trend}."

        chosen_trading_mode = self.config["trading_mode"]; source_tm = "Current"
        if AI_MODE_CONFIG.get("use_gemini_for_analysis") and gemini_model_instance:
            gemini_mode = await self.get_gemini_trading_mode(market_summary)
            if gemini_mode: chosen_trading_mode = gemini_mode; source_tm = "Gemini AI"
            else: logger.warning("🤖 AI: Gemini failed for trading mode, using rule-based fallback."); source_tm = "Rule-Based (Gemini fail)"
        if source_tm != "Gemini AI": # Rule-based or fallback
            if volatility_percent > AI_MODE_CONFIG["market_volatility_threshold_high"]: chosen_trading_mode = "safe"
            elif volatility_percent < AI_MODE_CONFIG["market_volatility_threshold_low"]: chosen_trading_mode = "aggressive"
            else: chosen_trading_mode = "standard"
            if source_tm == "Current": source_tm = "Rule-Based"

        if self.config["trading_mode"] != chosen_trading_mode:
            self.config["trading_mode"] = chosen_trading_mode
            self.apply_trading_mode_settings() # Ini akan update leverage, TP, SL di CONFIG
            changes_made.append(f"🎯 Trading Mode: <b>{chosen_trading_mode.capitalize()}</b> (by {source_tm})\n"
                                f"   - Leverage: {self.config['leverage']}x\n"
                                f"   - Take Profit: {self.config['take_profit']}%\n"
                                f"   - Stop Loss: {self.config['stop_loss']}%")

        new_indicator_settings = None; source_is = "Rule-Based"
        if AI_MODE_CONFIG.get("use_gemini_for_analysis") and gemini_model_instance:
            gemini_settings = await self.get_gemini_indicator_settings(market_summary)
            if gemini_settings: new_indicator_settings = gemini_settings; source_is = "Gemini AI"
            else: logger.warning("🤖 AI: Gemini failed for indicators, using rule-based fallback.")
        if not new_indicator_settings:
            profile_name = "balanced"
            if volatility_percent > AI_MODE_CONFIG["market_volatility_threshold_high"]: profile_name = "conservative"
            elif volatility_percent < AI_MODE_CONFIG["market_volatility_threshold_low"]: profile_name = "responsive"
            new_indicator_settings = AI_MODE_CONFIG["indicator_profiles"][profile_name].copy()

        if new_indicator_settings and INDICATOR_SETTINGS.get("description") != new_indicator_settings.get("description"):
            old_desc = INDICATOR_SETTINGS.get("description", "N/A")
            INDICATOR_SETTINGS = new_indicator_settings
            changes_made.append(f"📊 Indicator Profile: <b>{INDICATOR_SETTINGS.get('description')}</b> (by {source_is})\n"
                                f"   - RSI: {INDICATOR_SETTINGS['rsi_period']}({INDICATOR_SETTINGS['rsi_oversold']}/{INDICATOR_SETTINGS['rsi_overbought']}), EMA: {INDICATOR_SETTINGS['ema_short_period']}/{INDICATOR_SETTINGS['ema_long_period']}\n"
                                f"   - BB: {INDICATOR_SETTINGS['bb_period']}({INDICATOR_SETTINGS['bb_std']}), Signal Str: {INDICATOR_SETTINGS['signal_strength_threshold']}")


        if changes_made:
            notif = "✨ <b>AI Optimizer Update</b> ✨\n"
            notif += f"<i>Market State (BTC): Vol {volatility_percent:.2f}%, Trend {market_trend}</i>\n\n"
            notif += "<b><u>Perubahan Dilakukan:</u></b>\n"
            for change in changes_made:
                notif += f"{change}\n\n" # Tambah spasi antar grup perubahan
            notif += f"<b><u>Pengaturan Sebelumnya:</u></b>\n{current_settings_summary_detailed}"
            self.send_notification(notif)
        else: logger.info("🤖 AI Optimizer: No significant setting changes.")
        self.last_ai_optimization_time = time.time()
        
    def get_current_ai_settings_summary(self):
        return (f"  - Mode: {self.config['trading_mode'].capitalize()} (L:{self.config['leverage']}x)\n"
                f"  - Indicators: {INDICATOR_SETTINGS.get('description', 'N/A')}")
                
    def get_current_settings_summary_for_ai_notification(self):
        # Versi lebih detail untuk notifikasi AI
        summary = (
            f"  Mode: {self.config['trading_mode'].capitalize()} (L:{self.config['leverage']}x, TP:{self.config['take_profit']}%, SL:{self.config['stop_loss']}%)\n"
            f"  Indicators: {INDICATOR_SETTINGS.get('description', 'N/A')}\n"
            f"    (RSI: {INDICATOR_SETTINGS['rsi_period']}({INDICATOR_SETTINGS['rsi_oversold']}/{INDICATOR_SETTINGS['rsi_overbought']}), EMA: {INDICATOR_SETTINGS['ema_short_period']}/{INDICATOR_SETTINGS['ema_long_period']}, BB: {INDICATOR_SETTINGS['bb_period']}({INDICATOR_SETTINGS['bb_std']}))"
        )
        return summary

    async def ai_optimizer_loop_async(self):
        logger.info("AI Optimizer Loop (async) started.")
        if self.config.get("ai_mode_active"):
            try: await self.run_ai_optimizer_cycle()
            except Exception as e_ai_init: logger.error(f"Err initial AI cycle: {e_ai_init}", exc_info=True)
        while self.running:
            try:
                if self.config.get("ai_mode_active", False):
                    now = time.time(); interval = AI_MODE_CONFIG.get("optimization_interval_seconds", 3600)
                    if (now - self.last_ai_optimization_time) >= interval: await self.run_ai_optimizer_cycle()
                    else: await asyncio.sleep(min(60, interval - (now - self.last_ai_optimization_time)))
                else: await asyncio.sleep(60)
            except asyncio.CancelledError: logger.info("AI Optimizer loop cancelled."); break
            except Exception as e: logger.error(f"Error in AI Optimizer Loop: {e}", exc_info=True); await asyncio.sleep(300)
        logger.info("AI Optimizer Loop (async) stopped.")

    def _start_ai_optimizer_thread(self):
        if self.ai_optimizer_thread and self.ai_optimizer_thread.is_alive(): return
        def run_loop():
            loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
            try: loop.run_until_complete(self.ai_optimizer_loop_async())
            finally: loop.close()
        self.ai_optimizer_thread = threading.Thread(target=run_loop, daemon=True); self.ai_optimizer_thread.start()
        logger.info("AI Optimizer thread (for asyncio loop) started.")

    def get_liquid_pairs_from_watchlist(self):
        if not self.binance_api: return self.config.get("dynamic_watchlist_symbols", [])
        watchlist = self.config.get("dynamic_watchlist_symbols", []); min_vol = self.config.get("min_24h_volume_usdt_for_scan", 0)
        if not watchlist: return []
        all_tickers = self.binance_api.get_ticker_24hr()
        if not all_tickers or not isinstance(all_tickers, list): logger.error(f"Failed 24h ticker. Type: {type(all_tickers)}"); return watchlist
        tickers_map = {item['symbol']: item for item in all_tickers if isinstance(item, dict) and 'symbol' in item}
        return [s for s in watchlist if tickers_map.get(s) and float(tickers_map[s].get('quoteVolume', 0)) >= min_vol]

    def dynamic_pair_scan_loop(self):
        logger.info("Dynamic Pair Scanner loop initiated.")
        while self.running:
            try:
                if not self.config.get("dynamic_pair_selection", False): time.sleep(self.config.get("dynamic_scan_interval_seconds", 300) / 10); continue
                potential = self.get_liquid_pairs_from_watchlist()
                if not potential: time.sleep(self.config.get("dynamic_scan_interval_seconds", 300)); continue
                candidates = []
                for sym in potential:
                    if not self.running: break
                    signal = self.technical_analysis.get_signal(sym)
                    if signal and signal['action'] != 'WAIT' and signal['strength'] >= INDICATOR_SETTINGS.get("signal_strength_threshold"): candidates.append(signal)
                    time.sleep(self.config.get("api_call_delay_seconds_in_scan", 0.3))
                if not self.running: break
                candidates.sort(key=lambda x: x['strength'], reverse=True); self.currently_scanned_pairs = candidates
                max_act = self.config.get("max_active_dynamic_pairs", 1); new_active = [s['symbol'] for s in candidates[:max_act]]
                with self.active_trading_pairs_lock:
                    curr_active = list(self.config.get("trading_pairs", []))
                    if set(new_active) != set(curr_active):
                        self.config["trading_pairs"] = new_active
                        logger.warning(f"DynScan: Pairs UPDATED. Old:{curr_active}, New:{new_active}")
                        self.send_notification(f"🔄 <b>Dyn. Pairs Updated</b>: {', '.join(new_active) if new_active else 'None'}")
                interval = self.config.get("dynamic_scan_interval_seconds", 300)
                for _ in range(interval):
                    if not self.running: break; time.sleep(1)
            except Exception as e: logger.error(f"DynScan Error: {e}", exc_info=True); time.sleep(60)
        logger.info("Dynamic Pair Scanner loop stopped.")

    def start_trading(self):
        if self.running: logger.info("Bot already running."); return False
        self.running = True; logger.info("Attempting to start trading bot...")
        self._start_ai_optimizer_thread()
        if self.config.get("ai_mode_active"): logger.info("AI mode active. Allowing moment for initial AI opt..."); time.sleep(5) # Allow AI to run once
        if not self.config.get("ai_mode_active"): self.apply_trading_mode_settings()

        if self.binance_api and (self.config.get("hedge_mode_enabled") or self.config.get("use_real_trading")):
            acc_info = self.binance_api.get_account_info()
            if not acc_info: logger.error("CRITICAL: Binance API fail. Cannot start."); self.send_notification(f"❌ <b>Bot Start Fail</b>\nAPI conn failed."); self.running = False; return False
            logger.info("Binance API connection successful.")
        if self.config.get("hedge_mode_enabled", False) and self.binance_api:
            try:
                res = self.binance_api.change_position_mode(dual_side_position=True)
                if res and res.get('code') == 200: logger.info(f"Hedge Mode set/confirmed. Msg: {res.get('msg','OK')}")
                else: logger.warning(f"Failed Hedge Mode. Resp: {res}.")
            except Exception as e: logger.error(f"Err setting hedge: {e}", exc_info=True)

        self.signal_check_thread = threading.Thread(target=self.signal_check_loop, daemon=True); self.signal_check_thread.start()
        if self.config.get("dynamic_pair_selection", False):
            self.dynamic_pair_scanner_thread = threading.Thread(target=self.dynamic_pair_scan_loop, daemon=True); self.dynamic_pair_scanner_thread.start()
        self.notification_thread = threading.Thread(target=self.process_notification_queue, daemon=True); self.notification_thread.start()
        self.reset_daily_stats()

        # Notifikasi start_trading yang lebih detail
        start_msg = "🚀 <b>Trading Bot Dimulai</b> 🚀\n\n"
        start_msg += f"<b><u>Status AI:</u></b>\n"
        start_msg += f"  Mode AI: {'✅ AKTIF' if self.config.get('ai_mode_active') else '❌ NONAKTIF'}\n"
        start_msg += f"  Analisis Gemini: {'✅ DIGUNAKAN' if AI_MODE_CONFIG.get('use_gemini_for_analysis') and gemini_model_instance else '❌ RULE-BASED'}\n\n"
        start_msg += f"<b><u>Pengaturan Trading Saat Ini:</u></b>\n"
        start_msg += f"  Mode: {self.config.get('trading_mode','N/A').capitalize()}\n"
        start_msg += f"    Leverage: {self.config.get('leverage',0)}x\n"
        start_msg += f"    Take Profit: {self.config.get('take_profit',0.0)}%\n"
        start_msg += f"    Stop Loss: {self.config.get('stop_loss',0.0)}%\n"
        start_msg += f"    Ukuran Posisi: {self.config.get('position_size_percentage',0.0)}% / {self.config.get('fixed_position_size_usdt','N/A')} USDT\n"
        start_msg += f"    Maks Trade Harian: {self.config.get('max_daily_trades',0)}\n\n"
        start_msg += f"<b><u>Profil Indikator Saat Ini:</u></b>\n"
        start_msg += f"  Deskripsi: {INDICATOR_SETTINGS.get('description','N/A')}\n"
        start_msg += f"    RSI: P{INDICATOR_SETTINGS.get('rsi_period','N/A')} (OS:{INDICATOR_SETTINGS.get('rsi_oversold','N/A')}/OB:{INDICATOR_SETTINGS.get('rsi_overbought','N/A')})\n"
        start_msg += f"    EMA: S{INDICATOR_SETTINGS.get('ema_short_period','N/A')} / L{INDICATOR_SETTINGS.get('ema_long_period','N/A')}\n"
        start_msg += f"    BBands: P{INDICATOR_SETTINGS.get('bb_period','N/A')} (Std:{INDICATOR_SETTINGS.get('bb_std','N/A')})\n"
        start_msg += f"    Timeframe: {INDICATOR_SETTINGS.get('candle_timeframe','N/A')}\n"
        start_msg += f"    Kekuatan Sinyal Min: {INDICATOR_SETTINGS.get('signal_strength_threshold','N/A')}\n\n"
        start_msg += f"<b><u>Status Operasional:</u></b>\n"
        start_msg += f"  Trading Riil: {'✅ AKTIF' if self.config.get('use_real_trading') else '❌ SIMULASI'}\n"
        start_msg += f"  Seleksi Pair Dinamis: {'✅ AKTIF' if self.config.get('dynamic_pair_selection') else '❌ STATIS'}\n"
        active_pairs_list = self.config.get('trading_pairs', [])
        start_msg += f"  Pair Aktif: {', '.join(active_pairs_list) if active_pairs_list else ('Menunggu Pemindaian Dinamis' if self.config.get('dynamic_pair_selection') else 'Tidak Ada')}\n"
        start_msg += f"  Hedge Mode: {'✅ AKTIF' if self.config.get('hedge_mode_enabled') else '❌ NONAKTIF'}"

        self.send_notification(start_msg); logger.info("Trading bot started. Threads running.")
        return True
        

    def stop_trading(self):
        if not self.running: logger.info("Bot not running."); return False
        logger.warning("Initiating bot stop sequence..."); self.running = False
        if self.ai_optimizer_thread and self.ai_optimizer_thread.is_alive():
            logger.info("Waiting for AI Optimizer thread (max 10s)..."); self.ai_optimizer_thread.join(timeout=10)
            if self.ai_optimizer_thread.is_alive(): logger.warning("AI Optimizer thread did not join cleanly.")
        if self.dynamic_pair_scanner_thread and self.dynamic_pair_scanner_thread.is_alive(): self.dynamic_pair_scanner_thread.join(timeout=10)
        if self.signal_check_thread and self.signal_check_thread.is_alive(): self.signal_check_thread.join(timeout=self.config.get("signal_check_interval_seconds", 30) + 5)
        self.send_notification("⏹️ <b>Trading Bot Stopped</b> ⏹️"); time.sleep(0.5)
        if self.notification_thread and self.notification_thread.is_alive():
            try: self.notification_queue.put((None, None), block=False)
            except queue.Full: pass
            self.notification_thread.join(timeout=15)
        logger.warning("Bot stop sequence complete."); return True

    def apply_trading_mode_settings(self):
        mode = self.config.get("trading_mode", "standard")
        if mode in TRADING_MODES:
            s = TRADING_MODES[mode]
            self.config.update({"leverage":s["leverage"],"take_profit":s["take_profit"],"stop_loss":s["stop_loss"],"position_size_percentage":s["position_size_percent"],"max_daily_trades":s["max_daily_trades"]})
            logger.info(f"Applied '{mode}' mode settings from TRADING_MODES.")
        else: logger.warning(f"Mode '{mode}' not in TRADING_MODES.")

    def check_daily_limits(self) -> bool:
        max_t = self.config.get("max_daily_trades",15)
        if DAILY_STATS["total_trades"] >= max_t: logger.info(f"Max daily trades ({DAILY_STATS['total_trades']}/{max_t})."); self.send_notification(f"📊 MAX DAILY TRADES ({max_t}). Paused."); return False
        if self.config.get("use_real_trading") and DAILY_STATS["starting_balance_usdt"] > 0:
            profit_tgt, loss_lmt = self.config.get("daily_profit_target_percentage",5.0), self.config.get("daily_loss_limit_percentage",3.0)
            pnl_usdt = DAILY_STATS["current_balance_usdt"] - DAILY_STATS["starting_balance_usdt"]
            pnl_pct = (pnl_usdt / DAILY_STATS["starting_balance_usdt"]) * 100
            if pnl_pct >= profit_tgt: logger.info("Daily profit target."); self.send_notification("🎯 DAILY PROFIT TARGET! Paused."); return False
            if pnl_pct <= -loss_lmt: logger.info("Daily loss limit."); self.send_notification("⚠️ DAILY LOSS LIMIT! Paused."); return False
        return True

    def signal_check_loop(self):
        logger.info("Signal check loop initiated.")
        if self.config.get("dynamic_pair_selection"): time.sleep(5)
        while self.running:
            try:
                if not self.check_daily_limits():
                    if self.running: self.stop_trading(); break
                active_pairs = []
                with self.active_trading_pairs_lock:
                    if not self.config.get("dynamic_pair_selection"): active_pairs = list(self.config.get("static_trading_pairs",[]))
                    else: active_pairs = list(self.config.get("trading_pairs",[]))
                if not active_pairs: time.sleep(self.config.get("signal_check_interval_seconds",30)/2); continue
                for sym in active_pairs:
                    if not self.running: break
                    if any(t['symbol']==sym and not t.get('completed',False) for t in ACTIVE_TRADES): continue
                    signal = self.technical_analysis.get_signal(sym)
                    if signal and signal['action'] != 'WAIT':
                        logger.info(f"SignalCheck: {signal['action']} for {sym} (Str:{signal['strength']})")
                        self.process_signal(signal)
                        time.sleep(self.config.get("post_trade_entry_delay_seconds",2))
                if not self.running: break
                interval = self.config.get("signal_check_interval_seconds",30)
                for _ in range(interval):
                    if not self.running: break; time.sleep(1)
            except Exception as e: logger.error(f"SignalCheck Error: {e}", exc_info=True); time.sleep(60)
        logger.info("Signal check loop stopped.")

    def process_signal(self, signal):
        sym, act, px = signal['symbol'], signal['action'], signal['price']
        logger.info(f"Processing signal: {sym} {act} at {px:.4f}, Str:{signal['strength']}")
        if not self.config.get("use_real_trading") and not self.binance_api:
             logger.info(f"[SIM] Would open {act} for {sym} at {px:.4f}")
             trade_sim = self.create_trade(sym,act,"LONG" if act=="LONG" else "SHORT","BUY" if act=="LONG" else "SELL",px,0.001)
             if trade_sim: self.send_trade_notification(trade_sim,signal.get('reasons',[])); return
        pos_side, ord_side = ("LONG" if act=="LONG" else "SHORT"), ("BUY" if act=="LONG" else "SELL")
        if self.config.get("use_real_trading") and not self.binance_api: logger.error(f"[{sym}] Real trade but API N/A. Abort."); self.send_notification(f"⚠️ Real trade {sym} abort: API N/A."); return
        qty = self.calculate_position_size(sym,px)
        if not qty or qty<=0: logger.error(f"[{sym}] Invalid pos size ({qty}). Abort."); self.send_notification(f"⚠️ Trade {sym} abort: Invalid pos size."); return
        if self.binance_api and self.config.get("use_real_trading"):
            if not self.binance_api.change_leverage(sym,self.config["leverage"]): logger.warning(f"[{sym}] Failed leverage set.")
        trade_dets = self.create_trade(sym,act,pos_side,ord_side,px,qty)
        if trade_dets: self.send_trade_notification(trade_dets,signal.get('reasons',[]))
        else: logger.error(f"[{sym}] Failed to create trade object.")

    def calculate_position_size(self, symbol: str, current_price: float) -> float | None:
        try:
            if current_price <= 0: return None
            if not self.config.get("use_real_trading") or not self.binance_api:
                fixed_usdt = self.config.get("fixed_position_size_usdt",10); lev = self.config.get("leverage",1)
                sim_qty = (fixed_usdt * lev) / current_price if current_price > 0 else 0
                return self.binance_api.round_quantity(symbol,sim_qty) if self.binance_api and sim_qty>0 else (round(sim_qty,8) if sim_qty>0 else None)
            bal = self.binance_api.get_balance()
            if not bal or 'available' not in bal: return None
            avail_bal = float(bal['available'])
            margin_usdt = 0.0
            if self.config.get("use_percentage_for_pos_size",True): margin_usdt = avail_bal * (self.config.get("position_size_percentage",1.0)/100.0)
            else: margin_usdt = self.config.get("fixed_position_size_usdt",10.0)
            if margin_usdt > avail_bal*0.98: margin_usdt = avail_bal*0.98
            if margin_usdt <= 0: return None
            lev = self.config.get("leverage",1)
            qty_calc = (margin_usdt * lev) / current_price if current_price > 0 else 0
            if qty_calc <= 0: return None
            rnd_qty = self.binance_api.round_quantity(symbol,qty_calc)
            if rnd_qty <= 0: return None
            s_info = self.binance_api.get_symbol_info(symbol)
            if s_info:
                min_q = float(s_info.get('minQty','1e-8')); min_not = float(s_info.get('minNotional','1.0'))
                if rnd_qty < min_q: logger.error(f"[{symbol}] Qty {rnd_qty} < minQty {min_q}. Skip."); return None
                if (rnd_qty*current_price) < min_not: logger.error(f"[{symbol}] Notional {rnd_qty*current_price:.2f} < minNotional {min_not:.2f}. Skip."); return None
            else: logger.warning(f"[{symbol}] No symbol_info for minQty/Notional. Qty: {rnd_qty}")
            logger.info(f"[{symbol}] Pos Size: Margin ${margin_usdt:.2f}, Lev {lev}x, Px ${current_price:.4f} -> Qty {rnd_qty:.8f}")
            return rnd_qty
        except Exception as e: logger.error(f"Err calc pos size {symbol}: {e}", exc_info=True); return None

    def create_trade(self, symbol,action,position_side,order_side,entry_price,quantity):
        try:
            tp_pct,sl_pct = self.config.get("take_profit",1.0),self.config.get("stop_loss",0.5)
            tp_calc = entry_price*(1+tp_pct/100) if action=="LONG" else entry_price*(1-tp_pct/100)
            sl_calc = entry_price*(1-sl_pct/100) if action=="LONG" else entry_price*(1+sl_pct/100)
            tp_px,sl_px = entry_price,entry_price
            if self.binance_api: tp_px,sl_px = self.binance_api.round_price(symbol,tp_calc),self.binance_api.round_price(symbol,sl_calc)
            else: tp_px,sl_px = round(tp_calc,8),round(sl_calc,8)
            if (action=="LONG" and (sl_px>=entry_price or tp_px<=entry_price)) or \
               (action=="SHORT" and (sl_px<=entry_price or tp_px>=entry_price)):
                logger.warning(f"[{symbol}] Invalid TP/SL: E ${entry_price:.4f}, TP ${tp_px:.4f}, SL ${sl_px:.4f}.")

            trade_details = { # Renamed trade to trade_details
                'id':f"{symbol}-{int(time.time())}-{random.randint(100,999)}",
                'timestamp':time.time(), 'symbol':symbol, 'action':action,
                'position_side':position_side, 'order_side':order_side,
                'entry_price':entry_price, 'quantity':quantity,
                'take_profit_price':tp_px, 'stop_loss_price':sl_px,
                'leverage':self.config.get("leverage",1),
                'entry_time':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'completed':False, 'status':'PENDING_ENTRY',
                'mode':self.config.get('trading_mode','N/A'),
                'entry_order_id':None, 'avg_fill_price':None,
                'tp_order_id':None, 'sl_order_id':None,
                'real_trade':self.config.get("use_real_trading",False) and bool(self.binance_api)
            }
            if trade_details['real_trade']: # use trade_details consistently
                logger.info(f"[{symbol}] Attempting REAL orders...")
                entry_p={'symbol':symbol,'side':order_side,'order_type':"MARKET",'quantity':quantity}
                if self.config.get("hedge_mode_enabled"): entry_p['positionSide']=position_side
                entry_ord=self.binance_api.create_order(**entry_p)
                if not entry_ord or 'orderId' not in entry_ord:
                    logger.error(f"[{symbol}] Failed REAL entry. Resp:{entry_ord}")
                    self.send_notification(f"❌ Gagal buka posisi REAL {action} untuk {symbol}.")
                    return None
                trade_details['entry_order_id']=entry_ord['orderId']; trade_details['status']='ENTRY_ORDER_PLACED'
                logger.info(f"[{symbol}] REAL Entry Market ID {trade_details['entry_order_id']}.")
                time.sleep(self.config.get("post_trade_entry_delay_seconds",3)) # Sleep after entry order

                tp_sl_sd="SELL" if action=="LONG" else "BUY"
                tp_p={'symbol':symbol,'side':tp_sl_sd,'order_type':"TAKE_PROFIT_MARKET",'quantity':quantity,'stopPrice':tp_px,'reduceOnly':True}
                if self.config.get("hedge_mode_enabled"): tp_p['positionSide']=position_side
                tp_ord=self.binance_api.create_order(**tp_p)
                if tp_ord and 'orderId' in tp_ord:
                    trade_details['tp_order_id']=tp_ord['orderId']
                    logger.info(f"[{symbol}] REAL TP Order ID {trade_details['tp_order_id']} at {tp_px:.4f}")
                else:
                    logger.warning(f"[{symbol}] Failed REAL TP. Resp:{tp_ord}")
                    self.send_notification(f"⚠️ Gagal pasang TP untuk {symbol} {action}. Posisi terbuka tanpa TP.")

                sl_p={'symbol':symbol,'side':tp_sl_sd,'order_type':"STOP_MARKET",'quantity':quantity,'stopPrice':sl_px,'reduceOnly':True}
                if self.config.get("hedge_mode_enabled"): sl_p['positionSide']=position_side
                sl_ord=self.binance_api.create_order(**sl_p)
                if sl_ord and 'orderId' in sl_ord:
                    trade_details['sl_order_id']=sl_ord['orderId']
                    logger.info(f"[{symbol}] REAL SL Order ID {trade_details['sl_order_id']} at {sl_px:.4f}")
                else:
                    logger.warning(f"[{symbol}] Failed REAL SL. Resp:{sl_ord}")
                    self.send_notification(f"⚠️ Gagal pasang SL untuk {symbol} {action}. Posisi terbuka tanpa SL.")
                trade_details['status']='ACTIVE'
            else:
                logger.info(f"[{symbol}] SIMULATED {action} trade at {entry_price:.4f}, Qty:{quantity}.")
                trade_details['status']='ACTIVE'
            ACTIVE_TRADES.append(trade_details); DAILY_STATS["total_trades"]+=1
            return trade_details # return the modified dict
        except Exception as e:
            logger.error(f"[{symbol}] Err create_trade:{e}",exc_info=True)
            self.send_notification(f"❌ Error saat membuat trade untuk {symbol}:{e}")
            return None

    def send_trade_notification(self, trade_info, reasons): # Renamed param to trade_info
        action_emoji = "🟢" if trade_info['action'] == "LONG" else "🔴"
        trade_type_str = "REAL 🔥" if trade_info['real_trade'] else "SIMULASI 🧪"
        trade_mode_str = trade_info.get('mode', 'N/A').capitalize()

        msg = f"{action_emoji} <b>POSISI BARU {trade_type_str}</b> {action_emoji}\n\n"
        msg += f"📈 <b>Pair:</b> {trade_info['symbol']} ({trade_info['action']})\n"
        msg += f"🕹️ <b>Mode Bot:</b> {trade_mode_str}\n"
        msg += f"💲 <b>Harga Entry:</b> ${trade_info['entry_price']:.4f}\n"
        msg += f"📦 <b>Kuantitas:</b> {trade_info['quantity']}\n"
        msg += f" Leverage: {trade_info['leverage']}x\n\n"
        msg += f"🎯 <b>Take Profit:</b> ${trade_info['take_profit_price']:.4f} (+{self.config.get('take_profit',0):.2f}% dari entry)\n"
        msg += f"🛡️ <b>Stop Loss:</b> ${trade_info['stop_loss_price']:.4f} (-{self.config.get('stop_loss',0):.2f}% dari entry)\n\n"
        if reasons:
            msg += "<b><u>Alasan Sinyal:</u></b>\n"
            for i, reason in enumerate(reasons[:3]): # Tampilkan maks 3 alasan
                msg += f"  - {reason}\n"
            if len(reasons) > 3: msg += "  - ...dan lainnya.\n"
            msg += "\n"

        if trade_info['real_trade']:
            msg += "<b><u>Info Order (REAL):</u></b>\n"
            msg += f"  ID Order Entry: {trade_info.get('entry_order_id','N/A')}\n"
            msg += f"  ID Order TP: {trade_info.get('tp_order_id','N/A')}\n"
            msg += f"  ID Order SL: {trade_info.get('sl_order_id','N/A')}\n\n"

        msg += f"⏱️ <b>Waktu:</b> {trade_info['entry_time']}\n"
        msg += f"🚦 <b>Status Saat Ini:</b> {trade_info.get('status','TIDAK DIKETAHUI').replace('_',' ').capitalize()}"
        self.send_notification(msg)

    def complete_trade(self, trade_id, exit_price, exit_reason="manual_close"):
        trade_to_complete = next((t for t in ACTIVE_TRADES if t['id']==trade_id and not t.get('completed')),None) # Renamed trade to trade_to_complete
        if not trade_to_complete: return False
        try:
            e_px,qty,lev,act = trade_to_complete['entry_price'],trade_to_complete['quantity'],trade_to_complete['leverage'],trade_to_complete['action']
            raw_pnl_pct = ((exit_price-e_px)/e_px)*100 if act=="LONG" else ((e_px-exit_price)/e_px)*100
            if e_px == 0: raw_pnl_pct = 0 # Hindari division by zero
            lev_pnl_pct = raw_pnl_pct*lev
            pnl_usdt = (e_px*qty)*(raw_pnl_pct/100.0)
            trade_to_complete.update({'completed':True,'status':'COMPLETED','exit_price':exit_price,'exit_time':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),'profit_pct_raw':raw_pnl_pct,'leveraged_profit_pct':lev_pnl_pct,'profit_usdt':pnl_usdt,'exit_reason':exit_reason})

            if trade_to_complete.get('real_trade',False):
                DAILY_STATS["total_profit_usdt"]+=pnl_usdt
                if pnl_usdt>0: DAILY_STATS["winning_trades"]+=1
                elif pnl_usdt<0: DAILY_STATS["losing_trades"]+=1
                if DAILY_STATS["starting_balance_usdt"]>0:
                    DAILY_STATS["current_balance_usdt"]+=pnl_usdt
                    DAILY_STATS["roi_percentage"]=((DAILY_STATS["current_balance_usdt"]-DAILY_STATS["starting_balance_usdt"])/DAILY_STATS["starting_balance_usdt"])*100

            if trade_to_complete.get('real_trade',False) and self.binance_api:
                sym=trade_to_complete['symbol']
                if trade_to_complete.get('tp_order_id'): self.binance_api.cancel_order(sym,order_id=trade_to_complete.get('tp_order_id'))
                if trade_to_complete.get('sl_order_id'): self.binance_api.cancel_order(sym,order_id=trade_to_complete.get('sl_order_id'))

            result_text = "💰 PROFIT" if pnl_usdt>0 else ("💔 LOSS" if pnl_usdt<0 else "⚖️ BREAKEVEN")
            emoji = "✅" if pnl_usdt>0 else ("❌" if pnl_usdt<0 else "➖")
            reason_map={"take_profit":"🎯 Take Profit Tercapai","stop_loss":"🛡️ Stop Loss Tercapai","manual_close":"🛠️ Ditutup Manual Admin","manual_admin_close_all":"🚨 Ditutup Admin (Close All)"};
            reason_display=reason_map.get(exit_reason,exit_reason.replace("_"," ").capitalize())
            duration_seconds=int(time.time()-trade_to_complete['timestamp'])
            trade_type_str = "REAL 🔥" if trade_to_complete['real_trade'] else "SIMULASI 🧪"

            msg = f"{emoji} <b>TRADE SELESAI ({trade_type_str}) - {result_text}</b> {emoji}\n\n"
            msg += f"📈 <b>Pair:</b> {trade_to_complete['symbol']} ({trade_to_complete['action']})\n"
            msg += f"🕹️ <b>Mode Bot:</b> {trade_to_complete.get('mode','N/A').capitalize()}\n\n"
            msg += f"💲 <b>Harga Entry:</b> ${e_px:.4f}\n"
            msg += f"💲 <b>Harga Exit:</b> ${exit_price:.4f}\n"
            msg += f"📦 <b>Kuantitas:</b> {qty}\n"
            msg += f" Leverage: {lev}x\n\n"
            msg += f"💸 <b>Profit/Loss (USDT):</b> <b>${pnl_usdt:.2f}</b>\n"
            msg += f"  Profit/Loss (Raw %): {raw_pnl_pct:.2f}%\n"
            msg += f"  Profit/Loss (Leveraged %): {lev_pnl_pct:.2f}%\n\n"
            msg += f"🛑 <b>Alasan Exit:</b> {reason_display}\n"
            msg += f"⏱️ <b>Durasi Trade:</b> {str(timedelta(seconds=duration_seconds))}\n"
            msg += f"🕰️ <b>Waktu Selesai:</b> {trade_to_complete['exit_time']}"

            self.send_notification(msg)
            ACTIVE_TRADES.remove(trade_to_complete); COMPLETED_TRADES.append(trade_to_complete) # Use the correct variable name
            logger.info(f"Trade {trade_id} completed. Result:{result_text} PnL:${pnl_usdt:.2f} USDT.")
            return True
        except Exception as e: logger.error(f"Err completing trade {trade_id}:{e}",exc_info=True); return False

    def get_daily_stats_message(self):
        # Hitung win rate berdasarkan trade yang tercatat memiliki P/L (wins + losses)
        # total_trades_with_pl = DAILY_STATS["winning_trades"] + DAILY_STATS["losing_trades"]
        # win_rate_on_pl_trades = (DAILY_STATS["winning_trades"] / total_trades_with_pl * 100) if total_trades_with_pl > 0 else 0.0

        # Atau, hitung win rate berdasarkan semua trade yang diinisiasi (DAILY_STATS['total_trades'])
        # Ini mungkin lebih mencerminkan seberapa sering sinyal menghasilkan trade yang menang
        win_rate_on_attempts = (DAILY_STATS["winning_trades"] / DAILY_STATS["total_trades"] * 100) if DAILY_STATS["total_trades"] > 0 else 0.0


        msg = f"📊 <b>STATISTIK TRADING HARIAN - {DAILY_STATS.get('date','N/A')}</b> 📊\n\n"
        msg += f"<b><u>Ringkasan Performa:</u></b>\n"
        msg += f"  Total Trade Dicoba: {DAILY_STATS['total_trades']}\n"
        msg += f"  Trade Menang: {DAILY_STATS['winning_trades']} ✅\n"
        msg += f"  Trade Kalah: {DAILY_STATS['losing_trades']} ❌\n"
        # msg += f"  (Breakeven/Lainnya: {DAILY_STATS['total_trades'] - (DAILY_STATS['winning_trades'] + DAILY_STATS['losing_trades'])})\n"
        msg += f"  Win Rate (Menang/Total Dicoba): {win_rate_on_attempts:.1f}%\n\n"
        msg += f"💸 <b>Total Profit/Loss (USDT):</b> <b>${DAILY_STATS['total_profit_usdt']:.2f}</b>\n\n"

        msg += f"<b><u>Pelacakan Saldo (Untuk Trade Riil):</u></b>\n"
        msg += f"  Saldo Awal Hari Ini: ${DAILY_STATS['starting_balance_usdt']:.2f} USDT\n"
        msg += f"  Saldo Saat Ini: ${DAILY_STATS['current_balance_usdt']:.2f} USDT\n"
        msg += f"  ROI Harian: {DAILY_STATS.get('roi_percentage',0.0):.2f}%\n\n"

        msg += f"<b><u>Pengaturan Bot Saat Ini:</u></b>\n"
        msg += f"  Mode AI: {'✅ AKTIF' if self.config.get('ai_mode_active') else '❌ NONAKTIF'}\n"
        msg += f"    Analisis Gemini: {'✅ DIGUNAKAN' if AI_MODE_CONFIG.get('use_gemini_for_analysis') and gemini_model_instance else '❌ RULE-BASED'}\n"
        msg += f"  Mode Trading: {self.config.get('trading_mode','N/A').capitalize()} (L:{self.config.get('leverage',0)}x, TP:{self.config.get('take_profit',0)}%, SL:{self.config.get('stop_loss',0)}%)\n"
        msg += f"  Profil Indikator: {INDICATOR_SETTINGS.get('description','N/A')}\n"
        msg += f"  Trading Riil: {'✅ AKTIF' if self.config.get('use_real_trading') else '❌ SIMULASI'}"
        return msg


class TelegramBotHandler:
    def __init__(self, token_str, admin_ids_list):
        self.token = token_str
        self.admin_user_ids = admin_ids_list
        self.admin_chat_ids = []
        self.trading_bot: TradingBot = None
        self.application = Application.builder().token(self.token).build()
        self.register_handlers()
        logger.info(f"TelegramBotHandler initialized. Authorized User IDs: {self.admin_user_ids}")

    def register_handlers(self):
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
        self.application.add_handler(CommandHandler("closeall", self.close_all_positions_command))
        self.application.add_handler(CommandHandler("setleverage", self.set_leverage_command))
        self.application.add_handler(CommandHandler("setmode", self.set_mode_command))
        self.application.add_handler(CommandHandler("addpair", self.add_pair_command))
        self.application.add_handler(CommandHandler("removepair", self.remove_pair_command))
        self.application.add_handler(CommandHandler("setprofit", self.set_profit_command))
        self.application.add_handler(CommandHandler("enablereal", self.enable_real_trading_command))
        self.application.add_handler(CommandHandler("disablereal", self.disable_real_trading_command))
        self.application.add_handler(CommandHandler("testapi", self.test_api_command))
        self.application.add_handler(CommandHandler("toggledynamic", self.toggle_dynamic_selection_command))
        self.application.add_handler(CommandHandler("watchlist", self.manage_watchlist_command))
        self.application.add_handler(CommandHandler("toggleai", self.toggle_ai_mode_command))
        self.application.add_handler(CommandHandler("togglegemini", self.toggle_gemini_usage_command))
        self.application.add_handler(CommandHandler("runaiopt", self.run_ai_optimizer_now_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_error_handler(self.error_handler)

    def set_trading_bot(self, trading_bot_instance):
        self.trading_bot = trading_bot_instance

    async def is_authorized(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if user_id not in self.admin_user_ids:
            if update.effective_chat: await update.effective_chat.send_message("⛔ You are not authorized.")
            logger.warning(f"Unauthorized access by user {user_id}")
            return False
        if update.effective_chat and update.effective_chat.id not in self.admin_chat_ids:
            self.admin_chat_ids.append(update.effective_chat.id)
            logger.info(f"Admin user {user_id} chat_id {update.effective_chat.id} added for notifications.")
        return True

    async def toggle_ai_mode_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        current_status = self.trading_bot.config.get("ai_mode_active", False)
        new_status = not current_status
        self.trading_bot.config["ai_mode_active"] = new_status
        status_str = "✅ ACTIVE" if new_status else "❌ INACTIVE"
        msg = f"🤖 AI Mode set to: <b>{status_str}</b>.\n"
        if new_status:
            msg += "AI Optimizer will manage settings. Forcing an optimization cycle now..."
            asyncio.create_task(self.trading_bot.run_ai_optimizer_cycle())
        else: msg += "Bot uses manually configured settings."
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.HTML)

    async def toggle_gemini_usage_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        if not gemini_model_instance: await update.message.reply_text("⚠️ Gemini AI model N/A."); return
        current_gemini = AI_MODE_CONFIG.get("use_gemini_for_analysis", False)
        new_gemini = not current_gemini
        AI_MODE_CONFIG["use_gemini_for_analysis"] = new_gemini
        status_str = "✅ ENABLED" if new_gemini else "❌ DISABLED"
        msg = f"🤖 Gemini AI for analysis set to: <b>{status_str}</b>.\n"
        if new_gemini: msg += "AI Opt will use Gemini, with rule-based fallback."
        else: msg += "AI Opt uses rule-based logic only."
        await update.message.reply_text(msg, parse_mode=constants.ParseMode.HTML)

    async def run_ai_optimizer_now_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        if not self.trading_bot.config.get("ai_mode_active"): await update.message.reply_text("🤖 AI Mode INACTIVE. /toggleai first."); return
        await update.message.reply_text("🤖 Forcing AI Optimizer cycle... Check logs/notifications.")
        asyncio.create_task(self.trading_bot.run_ai_optimizer_cycle())

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        kbd = [[InlineKeyboardButton("🚀 Start Trading", callback_data="select_trading_mode")],
               [InlineKeyboardButton("📊 Stats", callback_data="stats"), InlineKeyboardButton("📈 Positions", callback_data="positions")],
               [InlineKeyboardButton("⚙️ Settings", callback_data="config"), InlineKeyboardButton("📋 Status", callback_data="status")]]
        await update.message.reply_text("👋 Welcome to Binance Futures Bot!\nUse menu or /help\n Author @JoestarMojo", reply_markup=InlineKeyboardMarkup(kbd))

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return

        help_text = "🆘 <b>PANDUAN LENGKAP BOT TRADING FUTURES</b> 🆘\n\n"
        help_text += "Selamat datang! Berikut adalah daftar perintah yang dapat Anda gunakan untuk mengelola bot ini:\n\n"

        help_text += "📖 <b><u>INFORMASI & STATUS BOT</u></b> 📖\n"
        help_text += "  <code>/start</code> - 🏁 Memulai interaksi & menampilkan menu utama.\n"
        help_text += "  <code>/help</code> - ❓ Menampilkan panduan lengkap ini.\n"
        help_text += "  <code>/status</code> - 📊 Melihat status operasional bot secara detail.\n"
        help_text += "  <code>/config</code> - ⚙️ Menampilkan konfigurasi bot saat ini.\n"
        help_text += "  <code>/trades</code> - 📋 Melihat riwayat 10 trade terakhir.\n"
        help_text += "  <code>/stats</code> - 📈 Menampilkan statistik performa trading harian.\n"
        help_text += "  <code>/balance</code> - 💰 Memeriksa saldo akun Binance Futures Anda.\n"
        help_text += "  <code>/positions</code> - 📂 Melihat posisi trading yang sedang terbuka di Binance.\n"
        help_text += "  <code>/indicators SIMBOL</code> - 🔬 Info indikator & sinyal untuk <code>SIMBOL</code> (Contoh: <code>/indicators BTCUSDT</code>).\n"
        help_text += "  <code>/scannedpairs</code> - 📡 Menampilkan kandidat pair dari pemindaian dinamis (jika aktif).\n\n"

        help_text += "🕹️ <b><u>KONTROL TRADING UTAMA</u></b> 🕹️\n"
        help_text += "  <code>/starttrade</code> - ▶️ Memulai proses trading otomatis (pilih mode).\n"
        help_text += "  <code>/stoptrade</code> - ⏹️ Menghentikan proses trading otomatis dengan aman.\n"
        help_text += "  <code>/closeall</code> - ⚠️ <b>(RIIL & HATI-HATI!)</b> Menutup SEMUA posisi terbuka di Binance.\n\n"

        help_text += "🛠️ <b><u>PENGATURAN STRATEGI & RISIKO</u></b> 🛠️\n"
        help_text += "  <i>(Catatan: Jika AI Mode aktif, AI dapat mengubah pengaturan ini)</i>\n"
        help_text += "  <code>/set PARAM NILAI</code> - 🔧 Ubah konfigurasi (Contoh: <code>/set leverage 15</code>).\n"
        help_text += "  <code>/setmode MODE</code> - 🚦 Mode (<code>safe</code>|<code>standard</code>|<code>aggressive</code>).\n"
        help_text += "  <code>/setleverage ANGKA</code> - 🔗 Leverage baru (Contoh: <code>20</code>).\n"
        help_text += "  <code>/setprofit TARGET% LIMIT%</code> - 🎯 Target profit & limit rugi harian (Contoh: <code>/setprofit 5 3</code>).\n\n"

        help_text += "↔️ <b><u>MANAJEMEN PAIR TRADING</u></b> ↔️\n"
        help_text += "  <code>/toggledynamic</code> - 🔄 Aktifkan/Nonaktifkan seleksi pair dinamis.\n"
        help_text += "  <code>/addpair SIMBOL</code> - ➕ (Jika dinamis OFF) Tambah pair statis (Contoh: <code>/addpair ETHUSDT</code>).\n"
        help_text += "  <code>/removepair SIMBOL</code> - ➖ (Jika dinamis OFF) Hapus pair statis.\n"
        help_text += "  <code>/watchlist CMD [SIMBOL,...]</code> - 📋 (Jika dinamis ON) Kelola watchlist (<code>list</code>|<code>add</code>|<code>remove</code>|<code>clear</code>).\n\n"

        help_text += "🧠 <b><u>MODE ARTIFICIAL INTELLIGENCE (AI)</u></b> 🧠\n"
        help_text += "  <code>/toggleai</code> - 💡 Aktifkan/Nonaktifkan AI Mode untuk optimasi otomatis.\n"
        help_text += "  <code>/togglegemini</code> - 💠 (Jika AI Mode ON) Aktifkan/Nonaktifkan penggunaan Gemini AI.\n"
        help_text += "  <code>/runaiopt</code> - ⚙️ (Jika AI Mode ON) Paksa siklus optimasi AI sekarang.\n\n"

        help_text += "🔩 <b><u>SISTEM & UTILITAS</u></b> 🔩\n"
        help_text += "  <code>/enablereal</code> - 🔥 Aktifkan mode trading dengan DANA RIIL (Tes API dulu!).\n"
        help_text += "  <code>/disablereal</code> - 🧪 Nonaktifkan mode riil (beralih ke SIMULASI).\n"
        help_text += "  <code>/testapi</code> - 📡 Uji koneksi API Key Anda ke Binance."

        # Penanganan pesan terlalu panjang (sudah ada dari sebelumnya, pastikan tetap ada)
        max_len = 4096
        try:
            if len(help_text) > max_len:
                logger.info(f"Help message too long ({len(help_text)} chars). Sending in chunks.")
                parts = []
                current_part = ""
                # Pecah berdasarkan grup utama (ditandai dengan <u><b>...</b></u>) atau baris kosong ganda
                # Ini adalah logika pemecahan yang lebih baik daripada sekadar per baris
                main_sections = help_text.split("\n\n") # Memecah berdasarkan dua baris baru
                
                for section in main_sections:
                    section_with_break = section + "\n\n" # Tambahkan kembali pemisahnya
                    if len(current_part) + len(section_with_break) > max_len - 50: # -50 buffer
                        if current_part: # Kirim part sebelumnya jika ada isinya
                            parts.append(current_part)
                        current_part = section_with_break
                    else:
                        current_part += section_with_break
                
                if current_part: # Sisa bagian terakhir
                    parts.append(current_part)

                if not parts and help_text: # Jika tidak terpecah tapi ada teks (sangat panjang tanpa \n\n)
                    parts.append(help_text) # Coba kirim utuh jika pemecahan gagal

                for i, part_msg in enumerate(parts):
                    if not part_msg.strip(): continue # Lewati bagian kosong
                    await update.message.reply_text(part_msg, parse_mode=constants.ParseMode.HTML)
                    if i < len(parts) - 1:
                        await asyncio.sleep(0.5) 
            else:
                await update.message.reply_text(help_text, parse_mode=constants.ParseMode.HTML)

        except BadRequest as e:
            logger.error(f"Error sending help message: {e}. Help text (or chunk) length: {len(help_text) if len(help_text) <= max_len else 'chunked'}")
            if "unsupported start tag" in str(e).lower() or "Can't parse entities" in str(e).lower():
                logger.error(f"HTML parsing error in help text: {e}")
                await update.message.reply_text("Terjadi masalah saat memformat pesan bantuan (HTML error). Pengembang telah diberitahu. Pastikan tidak ada tag HTML yang salah.")
            else:
                await update.message.reply_text(f"Terjadi kesalahan saat mengirim pesan bantuan: {e}")
        except Exception as e_general:
            logger.error(f"General error sending help message: {e_general}", exc_info=True)
            await update.message.reply_text("Terjadi kesalahan umum saat menampilkan bantuan.")
        except BadRequest as e:
            logger.error(f"Error sending help message: {e}. Help text (or chunk) length: {len(help_text) if len(help_text) <= max_len else 'chunked'}")
            # Coba kirim pesan error yang lebih sederhana jika parsing masih gagal
            if "unsupported start tag" in str(e).lower() or "Can't parse entities" in str(e).lower():
                logger.error(f"HTML parsing error in help text: {e}")
                await update.message.reply_text("Terjadi masalah saat memformat pesan bantuan (HTML error). Pengembang telah diberitahu.")
            else:
                await update.message.reply_text(f"Terjadi kesalahan saat mengirim pesan bantuan: {e}")
        except Exception as e_general:
            logger.error(f"General error sending help message: {e_general}", exc_info=True)
            await update.message.reply_text("Terjadi kesalahan umum saat menampilkan bantuan.")
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot: await msg_obj.reply_text("Bot tidak diinisialisasi."); return

        bot_cfg = self.trading_bot.config
        active_trades_list = [t for t in ACTIVE_TRADES if not t.get('completed')]
        pnl_today = DAILY_STATS.get('total_profit_usdt', 0.0)
        wins = DAILY_STATS.get('winning_trades',0); losses = DAILY_STATS.get('losing_trades',0); attempts = DAILY_STATS.get('total_trades',0)
        win_rate_attempts = (wins / attempts * 100) if attempts > 0 else 0.0

        ai_status_str = "✅ AKTIF" if bot_cfg.get("ai_mode_active") else "❌ NONAKTIF"
        gemini_usage_str = "✅ Gemini AI" if AI_MODE_CONFIG.get("use_gemini_for_analysis") and gemini_model_instance else "❌ Rule-Based"
        if not bot_cfg.get("ai_mode_active"): gemini_usage_str = "N/A (AI Nonaktif)"


        status_text = f"📊 <b>STATUS BOT SAAT INI</b> 📊\n\n"
        status_text += f"<b>Bot Berjalan:</b> {'✅ YA' if self.trading_bot.running else '❌ TIDAK'}\n"
        status_text += f"<b>Mode Trading Riil:</b> {'🔥 YA (DANA RIIL)' if bot_cfg.get('use_real_trading') else '🧪 TIDAK (SIMULASI)'}\n\n"

        status_text += f"<b><u>🤖 Pengaturan AI:</u></b>\n"
        status_text += f"  AI Mode: {ai_status_str}\n"
        status_text += f"  Analisis oleh: {gemini_usage_str}\n\n"

        status_text += f"<b><u>⚙️ Konfigurasi Trading Aktif:</u></b>\n"
        status_text += f"  Mode Strategi: {bot_cfg.get('trading_mode', 'N/A').capitalize()}\n"
        status_text += f"    Leverage: {bot_cfg.get('leverage',0)}x\n"
        status_text += f"    Take Profit: {bot_cfg.get('take_profit',0.0)}%\n"
        status_text += f"    Stop Loss: {bot_cfg.get('stop_loss',0.0)}%\n"
        status_text += f"  Profil Indikator: {INDICATOR_SETTINGS.get('description', 'N/A')}\n\n"


        status_text += f"<b><u>📈 Performa Hari Ini ({DAILY_STATS.get('date','N/A')}):</u></b>\n"
        status_text += f"  Total Trade Dicoba: {attempts}\n"
        status_text += f"  Posisi Aktif Saat Ini: {len(active_trades_list)}\n"
        status_text += f"  Profit/Loss USDT: ${pnl_today:.2f}\n"
        status_text += f"  Menang / Kalah: {wins} / {losses}\n"
        status_text += f"  Win Rate (dari total dicoba): {win_rate_attempts:.1f}%\n"
        status_text += f"  ROI Harian (Saldo Riil): {DAILY_STATS.get('roi_percentage',0.0):.2f}%\n"


        keyboard = [
            [InlineKeyboardButton("🚀 Mulai Trading", callback_data="select_trading_mode"), InlineKeyboardButton("🛑 Hentikan Trading", callback_data="stop_trading")],
            [InlineKeyboardButton("📊 Statistik Detail", callback_data="stats"), InlineKeyboardButton("📈 Lihat Posisi Binance", callback_data="positions")],
            [InlineKeyboardButton("⚙️ Lihat Konfigurasi", callback_data="config"),
             InlineKeyboardButton(f"{'🔴 Nonaktifkan' if bot_cfg.get('use_real_trading') else '🟢 Aktifkan'} Mode Riil", callback_data="toggle_real_trading")]
        ]
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
            else:
                await msg_obj.reply_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            if "message is not modified" not in str(e).lower(): logger.error(f"status_command error: {e}")
            
    async def config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global INDICATOR_SETTINGS
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot: await msg_obj.reply_text("Bot tidak diinisialisasi."); return

        cfg = self.trading_bot.config.copy() # Ambil salinan untuk ditampilkan
        cfg['api_key']='(Disembunyikan)'; cfg['api_secret']='(Disembunyikan)' # Sensor API keys

        text = f"⚙️ <b>KONFIGURASI BOT DETAIL</b> ⚙️\n\n"
        text += f"<b><u>🤖 Pengaturan Mode AI:</u></b>\n"
        text += f"  AI Mode Aktif: {'✅ YA' if cfg.get('ai_mode_active') else '❌ TIDAK'}\n"
        text += f"  Gunakan Analisis Gemini: {'✅ YA' if AI_MODE_CONFIG.get('use_gemini_for_analysis') and gemini_model_instance else '❌ TIDAK (Rule-Based atau AI Nonaktif)'}\n"
        text += f"  Interval Optimasi AI: {AI_MODE_CONFIG.get('optimization_interval_seconds', 'N/A')} detik\n\n"

        text += f"<b><u>📈 Pengaturan Trading Utama (dapat dipengaruhi AI jika aktif):</u></b>\n"
        text += f"  Mode Strategi: {cfg['trading_mode'].capitalize()}\n"
        text += f"    Leverage: {cfg['leverage']}x\n"
        text += f"    Take Profit: {cfg['take_profit']}%\n"
        text += f"    Stop Loss: {cfg['stop_loss']}%\n"
        text += f"    Ukuran Posisi (% dari saldo): {cfg['position_size_percentage']}%\n"
        text += f"    Ukuran Posisi (USDT tetap, jika % nonaktif): {cfg['fixed_position_size_usdt']} USDT\n"
        text += f"    Gunakan Persentase untuk Ukuran Posisi: {'✅ YA' if cfg['use_percentage_for_pos_size'] else '❌ TIDAK (Gunakan USDT Tetap)'}\n"
        text += f"    Maksimum Trade Harian: {cfg['max_daily_trades']}\n\n"

        text += f"<b><u>📊 Profil Indikator Teknis Saat Ini (dapat dipengaruhi AI jika aktif):</u></b>\n"
        text += f"  Deskripsi Profil: {INDICATOR_SETTINGS.get('description','N/A')}\n"
        text += f"  Periode RSI: {INDICATOR_SETTINGS.get('rsi_period','N/A')}\n"
        text += f"    RSI Oversold: {INDICATOR_SETTINGS.get('rsi_oversold','N/A')}\n"
        text += f"    RSI Overbought: {INDICATOR_SETTINGS.get('rsi_overbought','N/A')}\n"
        text += f"  Periode EMA Pendek: {INDICATOR_SETTINGS.get('ema_short_period','N/A')}\n"
        text += f"  Periode EMA Panjang: {INDICATOR_SETTINGS.get('ema_long_period','N/A')}\n"
        text += f"  Periode Bollinger Bands: {INDICATOR_SETTINGS.get('bb_period','N/A')}\n"
        text += f"    Standar Deviasi BB: {INDICATOR_SETTINGS.get('bb_std','N/A')}\n"
        text += f"  Timeframe Candle: {INDICATOR_SETTINGS.get('candle_timeframe','N/A')}\n"
        text += f"  Min. Kekuatan Sinyal: {INDICATOR_SETTINGS.get('signal_strength_threshold','N/A')}\n"
        text += f"  Limit Kline untuk Indikator: {INDICATOR_SETTINGS.get('klines_limit_for_indicator_calc','N/A')}\n\n"

        text += f"<b><u>⚙️ Pengaturan Operasional & Risiko:</u></b>\n"
        text += f"  Trading Riil Aktif: {'✅ YA (DANA RIIL)' if cfg['use_real_trading'] else '❌ TIDAK (SIMULASI)'}\n"
        text += f"  Hedge Mode (Binance): {'✅ AKTIF' if cfg['hedge_mode_enabled'] else '❌ NONAKTIF'}\n"
        text += f"  Target Profit Harian: {cfg['daily_profit_target_percentage']}% dari saldo awal\n"
        text += f"  Batas Kerugian Harian: {cfg['daily_loss_limit_percentage']}% dari saldo awal\n"
        text += f"  Interval Cek Sinyal: {cfg['signal_check_interval_seconds']} detik\n"
        text += f"  Delay Setelah Entry Trade: {cfg['post_trade_entry_delay_seconds']} detik\n\n"

        text += f"<b><u>🌐 Pengaturan Seleksi Pair Dinamis:</u></b>\n"
        text += f"  Seleksi Pair Dinamis Aktif: {'✅ YA' if cfg['dynamic_pair_selection'] else '❌ TIDAK (Gunakan Pair Statis)'}\n"
        text += f"  Pair Statis (jika dinamis nonaktif): {', '.join(cfg['static_trading_pairs']) if cfg['static_trading_pairs'] else 'Tidak Ada'}\n"
        text += f"  Watchlist untuk Pemindaian Dinamis ({len(cfg['dynamic_watchlist_symbols'])} pair): ... (lihat /watchlist list)\n" # Terlalu panjang untuk ditampilkan semua
        text += f"  Maks. Pair Dinamis Aktif Bersamaan: {cfg['max_active_dynamic_pairs']}\n"
        text += f"  Min. Volume 24jam (USDT) untuk Pindai: {cfg['min_24h_volume_usdt_for_scan']:,}\n" # Format dengan koma
        text += f"  Interval Pindai Dinamis: {cfg['dynamic_scan_interval_seconds']} detik\n"
        text += f"  Delay Panggilan API saat Pindai: {cfg['api_call_delay_seconds_in_scan']} detik\n"

        keyboard = [
            [InlineKeyboardButton("Ubah Mode Trading Manual", callback_data="select_trading_mode")],
            [InlineKeyboardButton("Kembali ke Status", callback_data="status")]
        ]
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
            else:
                await msg_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            if "message is not modified" not in str(e).lower(): logger.error(f"config_command error: {e}")
            
    async def set_config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        global INDICATOR_SETTINGS # Needed because this function can modify INDICATOR_SETTINGS
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        args = context.args
        if len(args)<2: await update.message.reply_text("Usage: /set [param] [value]"); return
        param = args[0].lower(); value_str = " ".join(args[1:])
        if self.trading_bot.config.get("ai_mode_active") and param in ["trading_mode","leverage","take_profit","stop_loss","position_size_percentage","max_daily_trades"]:
            await update.message.reply_text(f"⚠️ AI Mode ACTIVE. Manually setting '{param}' might be overridden by AI."); # Removed return
        sensitive_keys = ['api_key','api_secret']
        if param in sensitive_keys: await update.message.reply_text(f"'{param}' sensitive, set in script/env."); return
        if param in self.trading_bot.config:
            orig_val = self.trading_bot.config[param]; new_val = None
            try:
                if isinstance(orig_val,bool): new_val = value_str.lower() in ['true','1','yes','on']
                elif isinstance(orig_val,int): new_val = int(value_str)
                elif isinstance(orig_val,float): new_val = float(value_str)
                elif isinstance(orig_val,list): new_val = [item.strip().upper() for item in value_str.split(',')] if value_str else []
                else: new_val = value_str
                self.trading_bot.config[param] = new_val
                msg = f"Config '{param}' set to: {new_val}"
                if param=='trading_mode' and not self.trading_bot.config.get("ai_mode_active"): self.trading_bot.apply_trading_mode_settings(); msg+="\n(Trading mode sub-settings also applied)"
                await update.message.reply_text(msg)
            except ValueError: await update.message.reply_text(f"Invalid value for {param}. Expected {type(orig_val).__name__}.")
        elif param in INDICATOR_SETTINGS: # Note: INDICATOR_SETTINGS is already global
            if self.trading_bot.config.get("ai_mode_active") and AI_MODE_CONFIG.get("use_gemini_for_analysis"):
                await update.message.reply_text(f"⚠️ AI Mode with Gemini ACTIVE. Manually setting '{param}' may be overridden.")
            else:
                orig_indic = INDICATOR_SETTINGS[param]; new_indic = None
                try:
                    if isinstance(orig_indic,bool): new_indic = value_str.lower() in ['true','1','yes','on']
                    elif isinstance(orig_indic,int): new_indic = int(value_str)
                    elif isinstance(orig_indic,float): new_indic = float(value_str)
                    else: new_indic = value_str
                    INDICATOR_SETTINGS[param] = new_indic
                    INDICATOR_SETTINGS["description"] = "Manually Adjusted Profile"
                    await update.message.reply_text(f"Indicator '{param}' set to: {new_indic}. Profile: 'Manually Adjusted'.")
                except ValueError: await update.message.reply_text(f"Invalid value for indicator {param}. Expected {type(orig_indic).__name__}.")
        else: await update.message.reply_text(f"Unknown param: {param}")

    async def trades_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        all_trades = ACTIVE_TRADES+COMPLETED_TRADES
        if not all_trades: await update.message.reply_text("No trades yet."); return
        recent = sorted(all_trades,key=lambda x:x.get('timestamp',0),reverse=True)[:10]
        text = "📊 <b>RECENT TRADES</b> 📊\n"
        for tr in recent:
            stat = tr.get('status','COMPLETED' if tr.get('completed')else 'ACTIVE'); pnl=""
            if tr.get('completed'):pnl_v=tr.get('profit_usdt',0.0);pnl_c="🟢" if pnl_v>0 else("🔴" if pnl_v<0 else"⚪️");pnl=f"{pnl_c}PnL:${pnl_v:.2f}"
            entry_dt=datetime.fromtimestamp(tr.get('timestamp',0)).strftime('%m-%d %H:%M')
            text+=f"\n<b>{tr['symbol']}</b>({tr['action']}){entry_dt}\n Sts:{stat},E:${tr['entry_price']:.4f}{pnl}\n Q:{tr['quantity']}L:{tr['leverage']}x {'R'if tr['real_trade']else 'S'}"
        await update.message.reply_text(text,parse_mode=constants.ParseMode.HTML)

    async def stats_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot: await msg_obj.reply_text("Bot not init."); return
        stats_text = self.trading_bot.get_daily_stats_message()
        kbd = [[InlineKeyboardButton("🔙 Back to Status",callback_data="status")]]
        try:
            if update.callback_query: await update.callback_query.edit_message_text(stats_text,reply_markup=InlineKeyboardMarkup(kbd),parse_mode=constants.ParseMode.HTML)
            else: await msg_obj.reply_text(stats_text,reply_markup=InlineKeyboardMarkup(kbd),parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            if "message is not modified"not in str(e).lower():logger.error(f"stats_cmd err:{e}")

    async def balance_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot or not self.trading_bot.binance_api: await update.message.reply_text("Bot/API not init."); return
        status_msg = await update.message.reply_text("🔄 Fetching balance...")
        try:
            bal=self.trading_bot.binance_api.get_balance()
            if bal:text=(f"💰<b>ACCOUNT BALANCE</b>💰\n\nTotal:<b>${bal.get('total',0):.2f}</b>\nAvailable:${bal.get('available',0):.2f}\nUnreal PnL:${bal.get('unrealized_pnl',0):.2f}")
            else:text="❌ Failed to get balance."
            await status_msg.edit_text(text,parse_mode=constants.ParseMode.HTML)
        except Exception as e: await status_msg.edit_text(f"❌ Err getting balance:{str(e)}")

    async def positions_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj = update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot or not self.trading_bot.binance_api: await msg_obj.reply_text("Bot/API not init."); return
        status_msg = await msg_obj.reply_text("🔄 Fetching open positions...")
        try:
            pos=self.trading_bot.binance_api.get_open_positions()
            text=f"📈<b>OPEN POSITIONS ON BINANCE</b>📈\n"
            if not pos: text+="\nNo open positions found."
            else:
                found=False
                for p_item in pos:
                    if float(p_item.get('positionAmt',0))!=0:
                        found=True;side="LONG" if float(p_item['positionAmt'])>0 else "SHORT";api_ps=p_item.get('positionSide','N/A')
                        im=float(p_item.get('initialMargin',0));upnl=float(p_item.get('unrealizedProfit',0));roi=(upnl/im*100)if im!=0 else 0
                        text+=f"\n<b>{p_item['symbol']}</b>({side},API:{api_ps})\n Size:{p_item['positionAmt']},E:${float(p_item['entryPrice']):.4f}\n Mark:${float(p_item['markPrice']):.4f},Lev:{int(float(p_item['leverage']))}x\n UPnL:${upnl:.2f}(ROI:{roi:.2f}%)"
                if not found: text+="\nNo non-zero amount open positions found."
            kbd=[[InlineKeyboardButton("🔙 Back to Status",callback_data="status")]]
            await status_msg.edit_text(text,reply_markup=InlineKeyboardMarkup(kbd),parse_mode=constants.ParseMode.HTML)
        except Exception as e: await status_msg.edit_text(f"❌ Err getting positions:{str(e)}")

    async def indicators_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot or not self.trading_bot.technical_analysis: await update.message.reply_text("Bot/TA not init."); return
        args=context.args
        if not args: await update.message.reply_text("Usage:/indicators [SYMBOL]"); return
        symbol=args[0].upper();status_msg=await update.message.reply_text(f"🔄 Calc indicators for {symbol}...")
        try:
            global INDICATOR_SETTINGS
            tf=INDICATOR_SETTINGS.get('candle_timeframe','5m')
            indic=self.trading_bot.technical_analysis.calculate_indicators(symbol,tf)
            if indic:
                text=(f"📊<b>INDICATORS - {symbol}({tf})</b>📊\nProfile:{INDICATOR_SETTINGS.get('description','N/A')}\n\nClose:${indic['close']:.4f}(@{indic['timestamp'].strftime('%H:%M:%S')})\nRSI({INDICATOR_SETTINGS['rsi_period']}):{indic['rsi']:.2f}\nEMA({INDICATOR_SETTINGS['ema_short_period']}):{indic['ema_short']:.4f}\nEMA({INDICATOR_SETTINGS['ema_long_period']}):{indic['ema_long']:.4f}\nBB({INDICATOR_SETTINGS['bb_period']},{INDICATOR_SETTINGS['bb_std']}):L:${indic['bb_lower']:.4f}M:${indic['bb_middle']:.4f}U:${indic['bb_upper']:.4f}\nCandle:{indic['candle_color'].capitalize()}({indic['candle_size_pct']:.2f}%)\n")
                sig=self.trading_bot.technical_analysis.get_signal(symbol,tf)
                if sig:text+=f"\n<b>Signal:{sig['action']}(Str:{sig['strength']})</b>\nRsn:{';'.join(sig.get('reasons',[]))}"
                await status_msg.edit_text(text,parse_mode=constants.ParseMode.HTML)
            else: await status_msg.edit_text(f"❌ Failed to calc indicators for {symbol}.")
        except Exception as e: await status_msg.edit_text(f"❌ Err calc indicators {symbol}:{str(e)}")

    async def scanned_pairs_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        if not self.trading_bot.config.get("dynamic_pair_selection"): await update.message.reply_text("Dyn. pair selection OFF."); return
        info="🔎<b>Last Scanned Candidates</b>🔍\n"
        if not self.trading_bot.currently_scanned_pairs: info+="\nNo strong signals in last scan."
        else:
            for i,sig in enumerate(self.trading_bot.currently_scanned_pairs[:10]):
                info+=f"\n<b>{i+1}.{sig['symbol']}</b>:{sig['action']}(Str:{sig['strength']})\nP:${sig['price']:.4f}R:{';'.join(sig.get('reasons',[]))[:50]}"
            if len(self.trading_bot.currently_scanned_pairs)>10:info+=f"\n...and {len(self.trading_bot.currently_scanned_pairs)-10} more."
        with self.trading_bot.active_trading_pairs_lock:active_p=self.trading_bot.config.get('trading_pairs',[])
        info+=f"\n\n<b>Active:</b>{', '.join(active_p)if active_p else 'None'}"
        await update.message.reply_text(info,parse_mode=constants.ParseMode.HTML)

    async def start_trading_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        if self.trading_bot.running: await update.message.reply_text("Trading already running."); return
        await self.show_trading_mode_selection(update,context)

    async def show_trading_mode_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = "🔄 <b>PILIH MODE TRADING UNTUK MEMULAI</b> 🔄\n\n"
        keyboard = []

        if self.trading_bot and self.trading_bot.config.get("ai_mode_active"):
            text += "<i>⚠️ PERHATIAN: Mode AI sedang AKTIF.\nAI akan menentukan mode dan pengaturan optimal setelah bot dimulai. Pilihan Anda di sini mungkin bersifat sementara jika AI memutuskan berbeda.</i>\n\n"

        for mode_name, settings in TRADING_MODES.items():
            text += f"<b>{mode_name.capitalize()}</b>:\n"
            text += f"  Leverage: {settings['leverage']}x\n"
            text += f"  Take Profit: {settings['take_profit']}%\n"
            text += f"  Stop Loss: {settings['stop_loss']}%\n"
            text += f"  Ukuran Posisi: {settings['position_size_percent']}%\n"
            text += f"  Maks Trade Harian: {settings['max_daily_trades']}\n"
            text += f"  <i>Deskripsi: {settings['description']}</i>\n\n"
            keyboard.append([InlineKeyboardButton(f"🚀 Mulai dengan Mode {mode_name.capitalize()}", callback_data=f"start_mode_{mode_name}")])

        keyboard.append([InlineKeyboardButton("🔙 Batal & Lihat Status", callback_data="status")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=constants.ParseMode.HTML)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=constants.ParseMode.HTML)
        except Exception as e:
            if "message is not modified" not in str(e).lower(): logger.error(f"show_trading_mode_selection error: {e}")

    async def stop_trading_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        msg_obj=update.callback_query.message if update.callback_query else update.message
        res_text="Trading stop initiated."if self.trading_bot.stop_trading()else "Trading already stopped."
        if update.callback_query: await update.callback_query.edit_message_text(res_text)
        else: await msg_obj.reply_text(res_text)

    async def close_all_positions_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot or not self.trading_bot.binance_api: await update.message.reply_text("Bot/API not init."); return
        if not self.trading_bot.config.get("use_real_trading"): await update.message.reply_text("Real trading OFF./closeall only for real."); return
        await update.message.reply_text("⚠️ Sure to MARKET CLOSE all REAL open positions?",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Yes,Close All REAL",callback_data="confirm_close_all_real")],[InlineKeyboardButton("❌ No,Cancel",callback_data="status")]]))

    async def _confirm_close_all_positions_real(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        await update.callback_query.edit_message_text("🔄 Closing all REAL open positions...")
        closed_c,error_c=0,0
        try:
            open_pos=self.trading_bot.binance_api.get_open_positions()
            if not open_pos: await update.callback_query.edit_message_text("No open positions found."); return
            symbols_with_pos=list(set(p['symbol']for p in open_pos if float(p.get('positionAmt',0))!=0))
            if not symbols_with_pos: await update.callback_query.edit_message_text("No non-zero amount positions found."); return
            logger.warning(f"Admin CLOSE ALL REAL POSITIONS for:{symbols_with_pos}")
            for sym in symbols_with_pos:
                curr_pos=next((p for p in open_pos if p['symbol']==sym and float(p.get('positionAmt',0))!=0),None)
                if not curr_pos: continue
                amt=float(curr_pos['positionAmt']);side="SELL"if amt>0 else "BUY";pos_side="LONG"if amt>0 else "SHORT"
                close_p={'symbol':sym,'side':side,'order_type':"MARKET",'quantity':abs(amt),'reduceOnly':True}
                if self.trading_bot.config.get("hedge_mode_enabled"):close_p['positionSide']=pos_side
                logger.info(f"Closing {sym}:{side} MKT Qty:{abs(amt)} PosSide:{pos_side if self.trading_bot.config.get('hedge_mode_enabled')else 'N/A'}")
                closed_ord=self.trading_bot.binance_api.create_order(**close_p)
                if closed_ord and closed_ord.get('orderId'):
                    closed_c+=1;logger.info(f"MKT close {sym} ID:{closed_ord['orderId']}")
                    active_bot_trade=next((t for t in ACTIVE_TRADES if t['symbol']==sym and not t.get('completed')and t.get('real_trade')),None)
                    if active_bot_trade:
                        approx_exit=self.trading_bot.binance_api.get_ticker_price(sym)or float(curr_pos.get('markPrice',0))
                        self.trading_bot.complete_trade(active_bot_trade['id'],approx_exit,"manual_admin_close_all")
                else:error_c+=1;logger.error(f"Failed MKT close {sym}.Resp:{closed_ord}")
                await asyncio.sleep(0.2) # Use asyncio.sleep in async func
            res_text=f"✅ Closed orders for {closed_c} positions."
            if error_c>0:res_text+=f"\n⚠️ Failed to close {error_c} positions."
            await update.callback_query.edit_message_text(res_text)
        except Exception as e:logger.error(f"Err /closeall:{e}",exc_info=True);await update.callback_query.edit_message_text(f"❌ Err close all:{str(e)}")

    async def set_leverage_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        args=context.args
        if not args: await update.message.reply_text(f"Curr lev:{self.trading_bot.config['leverage']}x.Usage:/setleverage [val]"); return
        try:
            lev=int(args[0])
            if not 1<=lev<=125: await update.message.reply_text("Lev must be 1-125."); return
            if self.trading_bot.config.get("ai_mode_active"): await update.message.reply_text("⚠️ AI Mode ACTIVE.Leverage set by AI.This manual change may be overridden.")
            self.trading_bot.config['leverage']=lev
            await update.message.reply_text(f"Bot default leverage for NEW trades set to {lev}x.(May be overridden by AI/Trading Mode).")
        except ValueError: await update.message.reply_text("Invalid number.")

    async def set_mode_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        args=context.args
        if not args: await update.message.reply_text(f"Curr mode:{self.trading_bot.config['trading_mode']}.Usage:/setmode [safe|standard|aggressive]"); return
        mode=args[0].lower()
        if mode not in TRADING_MODES: await update.message.reply_text(f"Invalid mode.Opts:{', '.join(TRADING_MODES.keys())}"); return
        if self.trading_bot.config.get("ai_mode_active"): await update.message.reply_text("⚠️ AI Mode ACTIVE.Trading mode set by AI.This manual change will likely be overridden.")
        self.trading_bot.config['trading_mode']=mode
        self.trading_bot.apply_trading_mode_settings()
        await update.message.reply_text(f"Trading mode set to <b>{mode}</b>.Settings(L,TP,SL)applied:\nL:{self.trading_bot.config['leverage']}x,TP:{self.trading_bot.config['take_profit']}%,SL:{self.trading_bot.config['stop_loss']}%",parse_mode=constants.ParseMode.HTML)

    async def add_pair_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        args=context.args
        if not args: await update.message.reply_text(f"Static pairs:{','.join(self.trading_bot.config.get('static_trading_pairs',[]))}.Usage:/addpair SYMBOL"); return
        symbol=args[0].upper()
        if self.trading_bot.config.get("dynamic_pair_selection"): await update.message.reply_text("Dyn.pair ON.Use /watchlist."); return
        static_p=self.trading_bot.config.get("static_trading_pairs",[])
        if symbol in static_p: await update.message.reply_text(f"{symbol} already in static list."); return
        if self.trading_bot.binance_api and not self.trading_bot.binance_api.get_ticker_price(symbol): await update.message.reply_text(f"Symbol {symbol} invalid."); return
        static_p.append(symbol);self.trading_bot.config["static_trading_pairs"]=static_p
        if not self.trading_bot.config.get("dynamic_pair_selection"):
            with self.trading_bot.active_trading_pairs_lock:self.trading_bot.config["trading_pairs"]=list(static_p)
        await update.message.reply_text(f"{symbol} added to static.Curr:{','.join(static_p)}")

    async def remove_pair_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        args=context.args
        if not args: await update.message.reply_text(f"Static pairs:{','.join(self.trading_bot.config.get('static_trading_pairs',[]))}.Usage:/removepair SYMBOL"); return
        symbol=args[0].upper()
        if self.trading_bot.config.get("dynamic_pair_selection"): await update.message.reply_text("Dyn.pair ON.Use /watchlist."); return
        static_p=self.trading_bot.config.get("static_trading_pairs",[])
        if symbol not in static_p: await update.message.reply_text(f"{symbol} not in static list."); return
        static_p.remove(symbol);self.trading_bot.config["static_trading_pairs"]=static_p
        if not self.trading_bot.config.get("dynamic_pair_selection"):
            with self.trading_bot.active_trading_pairs_lock:self.trading_bot.config["trading_pairs"]=list(static_p)
        await update.message.reply_text(f"{symbol} removed.Static:{','.join(static_p)}")

    async def set_profit_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        args=context.args
        if len(args)<2: await update.message.reply_text(f"Curr Daily Profit Target:{self.trading_bot.config['daily_profit_target_percentage']}% Limit:{self.trading_bot.config['daily_loss_limit_percentage']}%.\nUsage:/setprofit [target%] [loss_limit%]"); return
        try:
            target,limit=float(args[0]),float(args[1])
            if not(0<target<=100 and 0<limit<=100):await update.message.reply_text("Perc must be 0-100."); return
            self.trading_bot.config['daily_profit_target_percentage']=target;self.trading_bot.config['daily_loss_limit_percentage']=limit
            await update.message.reply_text(f"Daily P/L limits set:Target {target}%,Loss -{limit}%")
        except ValueError: await update.message.reply_text("Invalid numbers.")

    async def enable_real_trading_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj=update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot: await msg_obj.reply_text("Bot not init."); return
        if not self.trading_bot.config["api_key"]or not self.trading_bot.config["api_secret"]: await msg_obj.reply_text("⚠️ API creds not set.Cannot enable real."); return
        if self.trading_bot.config["use_real_trading"]: await msg_obj.reply_text("Real trading already ON."); return
        status_msg=await msg_obj.reply_text("🔄 Testing API for REAL trading...")
        if self.trading_bot.binance_api:
            acc_info=self.trading_bot.binance_api.get_account_info()
            if acc_info:self.trading_bot.config["use_real_trading"]=True;await status_msg.edit_text(f"✅ Real trading ENABLED!\n⚠️ Trades use REAL funds.Monitor!");logger.warning(f"REAL TRADING ENABLED by admin.")
            else: await status_msg.edit_text("❌ API conn failed.Real NOT enabled.Check keys/perms/IP.")
        else: await status_msg.edit_text("❌ Binance API module N/A.Real NOT enabled.")

    async def disable_real_trading_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        msg_obj=update.callback_query.message if update.callback_query else update.message
        if not self.trading_bot: await msg_obj.reply_text("Bot not init."); return
        if not self.trading_bot.config["use_real_trading"]: await msg_obj.reply_text("Real trading already OFF(Sim mode)."); return
        self.trading_bot.config["use_real_trading"]=False;await msg_obj.reply_text("✅ Real trading DISABLED.Bot in Sim mode.");logger.info("Real trading disabled by admin.")

    async def test_api_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        if not self.trading_bot.config.get("api_key")or not self.trading_bot.config.get("api_secret"): await update.message.reply_text("⚠️ API creds not set."); return
        if not self.trading_bot.binance_api: await update.message.reply_text("⚠️ Binance API module not init."); return
        status_msg=await update.message.reply_text("🔄 Testing Binance API conn...")
        try:
            acc_info=self.trading_bot.binance_api.get_account_info()
            if acc_info:
                bal=self.trading_bot.binance_api.get_balance()
                text=(f"✅ API Test OK!\nAssets:{len(acc_info.get('assets',[]))},Pos:{len(acc_info.get('positions',[]))}\nUSDT Bal:${bal.get('total',0):.2f}(Avail:${bal.get('available',0):.2f})"if bal else"USDT Bal:N/A")
                await status_msg.edit_text(text)
            else: await status_msg.edit_text(f"❌ API Test Failed.\nget_account_info returned None.Check Key,Secret,Perms,IP.")
        except Exception as e: await status_msg.edit_text(f"❌ API Test Exception:{str(e)}")

    async def toggle_dynamic_selection_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        curr_stat=self.trading_bot.config.get("dynamic_pair_selection",False)
        new_stat=not curr_stat
        self.trading_bot.config["dynamic_pair_selection"]=new_stat
        if new_stat and(not self.trading_bot.dynamic_pair_scanner_thread or not self.trading_bot.dynamic_pair_scanner_thread.is_alive()):
            if self.trading_bot.running:
                logger.info("Dyn.pair ON.Starting scanner thread.")
                self.trading_bot.dynamic_pair_scanner_thread=threading.Thread(target=self.trading_bot.dynamic_pair_scan_loop,daemon=True);self.trading_bot.dynamic_pair_scanner_thread.start()
            else: logger.info("Dyn.pair ON,but bot not running.Scanner starts with /starttrade.")
        msg_suf=""
        if not new_stat:
            with self.trading_bot.active_trading_pairs_lock:self.trading_bot.config["trading_pairs"]=list(self.trading_bot.config.get("static_trading_pairs",[]))
            msg_suf=f"\nBot uses static pairs:{self.trading_bot.config['trading_pairs']}"
        else: msg_suf="\nDyn.scanner manages active pairs."
        await update.message.reply_text(f"Dyn.Pair Selection:{'✅ ON'if new_stat else'❌ OFF'}.{msg_suf}");logger.info(f"Dyn.pair selection toggled to {new_stat}.")

    async def manage_watchlist_command(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        if not self.trading_bot: await update.message.reply_text("Bot not init."); return
        args=context.args
        if not args or args[0].lower()not in['add','remove','list','clear']: await update.message.reply_text("Usage:/watchlist [add|remove|list|clear] [SYMBOL_CSV]"); return
        action=args[0].lower();watchlist=self.trading_bot.config.get("dynamic_watchlist_symbols",[])
        if action=='list': await update.message.reply_text(f"Dyn.Watchlist({len(watchlist)}):\n{','.join(watchlist)if watchlist else 'Empty'}"); return
        if action=='clear': self.trading_bot.config["dynamic_watchlist_symbols"]=[];await update.message.reply_text("Dyn.watchlist cleared.");logger.info("Dyn.watchlist cleared."); return
        if len(args)<2 and action in['add','remove']: await update.message.reply_text(f"Usage:/watchlist {action} SYMBOL1,SYMBOL2,..."); return
        syms_str=args[1];syms_proc=[s.strip().upper()for s in syms_str.split(',')]
        if action=='add':
            added_c=0
            if self.trading_bot.binance_api:
                for sym in syms_proc:
                    if self.trading_bot.binance_api.get_ticker_price(sym):
                        if sym not in watchlist:watchlist.append(sym);added_c+=1
                    else:logger.warning(f"Watchlist add:Invalid sym {sym}")
            else:
                for sym in syms_proc:
                    if sym not in watchlist:watchlist.append(sym);added_c+=1
            self.trading_bot.config["dynamic_watchlist_symbols"]=watchlist;await update.message.reply_text(f"Added {added_c} new sym(s).Total:{len(watchlist)}");
            if added_c>0:logger.info(f"Admin added to watchlist:{syms_str}")
        elif action=='remove':
            removed_c=0
            for sym in syms_proc:
                if sym in watchlist:watchlist.remove(sym);removed_c+=1
            self.trading_bot.config["dynamic_watchlist_symbols"]=watchlist;await update.message.reply_text(f"Removed {removed_c} sym(s).Total:{len(watchlist)}");
            if removed_c>0:logger.info(f"Admin removed from watchlist:{syms_str}")

    async def button_callback(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        query=update.callback_query;await query.answer();data=query.data
        if data.startswith("start_mode_"):
            if self.trading_bot.running: await query.edit_message_text("Trading already running./stoptrade first."); return
            mode=data.replace("start_mode_","")
            if mode in TRADING_MODES:
                self.trading_bot.config["trading_mode"]=mode
                if self.trading_bot.start_trading():
                    start_msg=f"✅ Trading start initiated with <b>{mode.capitalize()}</b> mode."
                    if self.trading_bot.config.get("ai_mode_active"):start_msg+="\n<i>Note:AI Mode ACTIVE and may adjust settings.</i>"
                    await query.edit_message_text(start_msg,parse_mode=constants.ParseMode.HTML)
                else: await query.edit_message_text("⚠️ Trading failed to start.Check logs.")
            else: await query.edit_message_text(f"Unknown mode:{mode}")
            return
        elif data=="select_trading_mode":await self.show_trading_mode_selection(update,context)
        elif data=="stop_trading":await self.stop_trading_command(update,context)
        elif data=="status":await self.status_command(update,context)
        elif data=="config":await self.config_command(update,context)
        elif data=="stats":await self.stats_command(update,context)
        elif data=="positions":await self.positions_command(update,context)
        elif data=="confirm_close_all_real":await self._confirm_close_all_positions_real(update,context)
        elif data=="toggle_real_trading":
            if not self.trading_bot:return
            curr_real=self.trading_bot.config.get("use_real_trading",False)
            if not curr_real:
                if not self.trading_bot.config["api_key"]or not self.trading_bot.config["api_secret"]:await query.edit_message_text("⚠️ API creds not set.");return
                if self.trading_bot.binance_api and self.trading_bot.binance_api.get_account_info():self.trading_bot.config["use_real_trading"]=True;logger.warning("REAL TRADING ENABLED via quick toggle.")
                else:await query.edit_message_text("❌ API conn test failed.");return
            else:self.trading_bot.config["use_real_trading"]=False;logger.info("Real trading disabled via quick toggle.")
            await self.status_command(update,context)

    async def handle_message(self,update:Update,context:ContextTypes.DEFAULT_TYPE):
        if not await self.is_authorized(update): return
        await update.message.reply_text("Unknown command./help for options.")

    async def error_handler(self,update:object,context:ContextTypes.DEFAULT_TYPE)->None:
        logger.error(f"Unhandled exception:{context.error}",exc_info=context.error)
        if isinstance(update,Update)and update.effective_chat:
            try:await self.application.bot.send_message(chat_id=update.effective_chat.id,text="⚠️ Internal error.Devs notified via logs.")
            except Exception as e_send:logger.error(f"Failed to send error notif:{e_send}")

    def run(self):
        logger.info("Telegram bot polling started.")
        self.application.run_polling()
        logger.info("Telegram bot polling stopped.")


def main():
    logger.info("Bot starting up...")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN=="YOUR_FALLBACK_TELEGRAM_TOKEN": logger.critical("TELEGRAM_BOT_TOKEN_ENV not set.Bot cannot start."); return
    if not ADMIN_USER_IDS: logger.critical("ADMIN_USER_IDS_ENV not set or invalid.Bot cannot auth users."); return
    if(not BINANCE_API_KEY or BINANCE_API_KEY=="YOUR_FALLBACK_BINANCE_API_KEY"or not BINANCE_API_SECRET or BINANCE_API_SECRET=="YOUR_FALLBACK_BINANCE_API_SECRET"):
        logger.warning("Binance API creds not fully set.Real trading/API functions will fail.")

    telegram_handler = TelegramBotHandler(TELEGRAM_BOT_TOKEN,ADMIN_USER_IDS)
    trading_bot_instance = TradingBot(CONFIG,telegram_handler)
    telegram_handler.set_trading_bot(trading_bot_instance)

    logger.info(f"Admin User IDs:{ADMIN_USER_IDS}")
    logger.info(f"Initial AI Mode:{CONFIG.get('ai_mode_active')},Use Gemini:{AI_MODE_CONFIG.get('use_gemini_for_analysis')and bool(gemini_model_instance)}")
    logger.info("Press Ctrl+C to stop the bot.")

    try:
        telegram_handler.run()
    except KeyboardInterrupt:
        logger.info("Ctrl+C received.Shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error in main:{e}",exc_info=True)
    finally:
        logger.info("Main:Initiating graceful shutdown of trading bot...")
        if trading_bot_instance and trading_bot_instance.running:
            trading_bot_instance.stop_trading()
        logger.info("Bot shutdown sequence complete.")

if __name__ == "__main__":
    main()
