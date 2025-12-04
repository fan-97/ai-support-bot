import asyncio

from services.data_fetcher import (
    get_binance_klines,
    get_current_funding_rate,
    get_open_interest,
)
from services.indicators import calc_rsi, calc_macd, calc_ema, calc_bollinger_bands, calc_kdj
from services.patterns import detect_bearish_patterns
from services.ai_service import analyze_with_ai


SYMBOL = "PIPPINUSDT"
INTERVAL = "15m"


async def main():
    df = await get_binance_klines(SYMBOL, interval=INTERVAL)
    funding_rate = await get_current_funding_rate(SYMBOL)
    open_interest = await get_open_interest(SYMBOL, INTERVAL)

    if df is None:
        raise RuntimeError("Data fetch failed (symbol/network)")

    df["rsi"] = calc_rsi(df["close"])
    df["rsi7"] = calc_rsi(df["close"], period=7)
    df["ema20"] = calc_ema(df["close"], span=20)
    df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])

    df["bb_upper"], df["bb_mid"], df["bb_lower"] = calc_bollinger_bands(df["close"])
    df["k"], df["d"], df["j"] = calc_kdj(df["high"], df["low"], df["close"])

    patterns = detect_bearish_patterns(df)

    result = await analyze_with_ai(
        SYMBOL,
        INTERVAL,
        df,
        funding_rate,
        open_interest,
        patterns,
        model="deepseek/deepseek-v3.2",
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
