import asyncio
import json

from services.data_fetcher import prepare_market_data_for_ai
from services.indicators import calc_rsi, calc_macd, calc_ema, calc_bollinger_bands, calc_kdj
from services.patterns import detect_bearish_patterns
from services.ai_service import analyze_with_ai
from services.data_processor import CryptoDataProcessor
from services.notification import NotificationService


SYMBOL = "TURBOUSDT"
INTERVAL = "15m"


async def main():
    # 获取指标
    df, df_btc = await prepare_market_data_for_ai(SYMBOL, INTERVAL)

    if df is None:
        raise RuntimeError("Data fetch failed (symbol/network)")
    if not detect_bearish_patterns(df):
        print(f"[{SYMBOL} {INTERVAL}] Bearish pattern detected, skipping notification")
        return
    result = await analyze_with_ai(
        SYMBOL,
        INTERVAL,
        df,
        df_btc,
        balance=1000,
        model="deepseek/deepseek-v3.2",
    )
    caption, full_report = NotificationService.format_report(SYMBOL, INTERVAL, result)
    print(caption)
    print(full_report)  


if __name__ == "__main__":
    asyncio.run(main())
