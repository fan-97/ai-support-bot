import os

# 1. Telegram 设置
BOT_TOKEN = ''
ALLOWED_USER_IDS = [7643520392, 8108089944]  # 允许使用机器人的用户 ID (数字)

# 2. Google Gemini 设置
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-2.5-flash" # 使用 Flash 模型，速度快且免费额度多

# 3. 网络代理 (国内必须设置)
# export https_proxy=http://127.0.0.1:7890 (在终端运行脚本前设置)
PROXY_URL = None 

# 4. 自动监控策略参数
RSI_THRESHOLD = 70
SHADOW_RATIO = 2.0
DANGER_FUNDING_RATE = -0.05

# 5. 文件路径
DATA_FILE = 'watchlist.json'
BASE_URL = "https://fapi.binance.com"

# 6. 默认风控设置
DEFAULT_BALANCE = 1000.0
DEFAULT_RISK_PCT = 2.0

# RSI 参数
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70

# MACD 参数
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# 成交量确认参数
VOLUME_LOOKBACK = 20            # 向前看多少根K线
VOLUME_MULTIPLIER = 1.5         # 成交量放大倍数


# 开盘时间
KLINE_INDEX_OPEN_TIME= 0
# 开盘价
KLINE_INDEX_OPEN_PRICE = 1
# 最高价
KLINE_INDEX_HIGH_PRICE = 2
# 最低价
KLINE_INDEX_LOW_PRICE = 3
# 收盘价(当前K线未结束的即为最新价)
KLINE_INDEX_CLOSE_PRICE = 4
# 成交量
KLINE_INDEX_VOLUME = 5
# 收盘时间
KLINE_INDEX_CLOSE_TIME = 6
# 成交额
KLINE_INDEX_QUOTE_ASSET_VOLUME = 7
# 成交笔数
KLINE_INDEX_NUMBER_OF_TRADES = 8
# 主动买入成交量
KLINE_INDEX_TAKER_BASE_ASSET_VOLUME = 9
# 主动买入成交额
KLINE_INDEX_TAKER_QUOTE_ASSET_VOLUME = 10