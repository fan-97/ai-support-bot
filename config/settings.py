import os
from dotenv import load_dotenv

load_dotenv()

# Telegram settings
BOT_TOKEN = os.getenv('BOT_TOKEN')
ALLOWED_USER_IDS = [7643520392, 8108089944]
TELEGRAM_CONNECT_TIMEOUT = 30.0
TELEGRAM_READ_TIMEOUT = 60.0

# OpenRouter (Unified Provider)
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_BASE_URL = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'google/gemini-2.5-flash')
AI_TIMEOUT = 120

# Site info for OpenRouter rankings (optional)
SITE_URL = os.getenv('SITE_URL', 'https://github.com/your-repo/ai-support-bot')
SITE_NAME = os.getenv('SITE_NAME', 'AI Crypto Analyst')

# Proxy (optional)
PROXY_URL = os.getenv('PROXY_URL',None)

# Strategy params
RSI_THRESHOLD = 70
SHADOW_RATIO = 2.0
DANGER_FUNDING_RATE = -0.05

# Paths / endpoints
DATA_FILE = 'watchlist.json'
BASE_URL = "https://fapi.binance.com"

# Default risk settings
DEFAULT_BALANCE = 1000.0
DEFAULT_RISK_PCT = 2.0

# RSI params
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70

# MACD params
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# Volume confirmation params
VOLUME_LOOKBACK = 20  # 向前看多少根K线
VOLUME_MULTIPLIER = 1.5  # 成交量放大倍数

# Kline index reference
KLINE_INDEX_OPEN_TIME = 0
KLINE_INDEX_OPEN_PRICE = 1
KLINE_INDEX_HIGH_PRICE = 2
KLINE_INDEX_LOW_PRICE = 3
KLINE_INDEX_CLOSE_PRICE = 4
KLINE_INDEX_VOLUME = 5
KLINE_INDEX_CLOSE_TIME = 6
KLINE_INDEX_QUOTE_ASSET_VOLUME = 7
KLINE_INDEX_NUMBER_OF_TRADES = 8
KLINE_INDEX_TAKER_BASE_ASSET_VOLUME = 9
KLINE_INDEX_TAKER_QUOTE_ASSET_VOLUME = 10
