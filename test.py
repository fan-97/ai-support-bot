import asyncio
import json

from services.data_fetcher import prepare_market_data_for_ai
from services.indicators import calc_rsi, calc_macd, calc_ema, calc_bollinger_bands, calc_kdj
from services.ai_service import analyze_with_ai
from services.data_processor import CryptoDataProcessor
from services.notification import NotificationService
from services.model import ReversalModel
from services.data_fetcher import DataFetcher


SYMBOL = "POWERUSDT"
INTERVAL = "5m"


async def main():
    dfr = DataFetcher()
    df = await dfr.get_merged_data(SYMBOL, INTERVAL)
    print("正在初始化模型...")
    model = ReversalModel(df)
    
    print("\n--- 分析最新一根 K 线 ---")
    result = model.evaluate(index=-1)
    
    print(f"当前价格: {result['price']:.2f}")
    print(f"RSI数值: {result['rsi']:.2f}")
    print(f"当前趋势: {result['trend']}")
    print(f"信号方向: {'做多反转 (Bullish)' if result['signal_type'] == 'long_reversal' else '做空反转 (Bearish)'}")
    print(f"综合评分: {result['total_score']} / 100")
    print("-" * 30)
    print("得分详情:")
    for k, v in result['details'].items():
        print(f"  - {k}: +{v}")
    
    print("-" * 30)
    score = result['total_score']
    if score < 30: print("建议: 观望 (风险低但机会也低)")
    elif score < 60: print("建议: 观察区 (等待更多信号)")
    elif score < 80: print("建议: 重点关注 (轻仓尝试 + 紧止损)")
    else: print("建议: ⚠️ 极端反转区 (高胜率，由于波动大需挂单进场)")


if __name__ == "__main__":
    asyncio.run(main())
