import os

# 1. Telegram 设置
BOT_TOKEN = '7953312922:AAH7ky-xXUhYt833f6xotlxYyNeZ9Sg_U5U'
ALLOWED_USER_IDS = [7643520392, 8108089944]  # 允许使用机器人的用户 ID (数字)

# 2. Google Gemini 设置
GEMINI_API_KEY = "AIzaSyBXcc0iUTaMpoYVvFXco_TGhnEHKyH2Mi4"
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
