import asyncio
import json

from services.data_fetcher import prepare_market_data_for_ai
from services.ai_service import analyze_with_ai
from services.patterns import CandlePatternDetector
from services.notification import NotificationService


SYMBOL = "ETHUSDT"
INTERVAL = "4h"


async def main():
    # 获取指标
    df, df_btc = await prepare_market_data_for_ai(SYMBOL, INTERVAL)

    if df is None:
        raise RuntimeError("Data fetch failed (symbol/network)")
    # 出现看跌或者看涨形态的时候才进行AI分析
    detector  = CandlePatternDetector(df)
    match,pattern = detector.detect_patterns()
    if not match:
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
    print(result)
    caption, full_report = NotificationService.format_report(SYMBOL, INTERVAL, result)
    print(caption)
    print(full_report)  


if __name__ == "__main__":
    asyncio.run(main())
