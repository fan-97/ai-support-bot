# confirmations.py
import pandas as pd

from config.settings import (
    VOLUME_LOOKBACK,
    VOLUME_MULTIPLIER,
    RSI_OVERBOUGHT,
)


def volume_confirmation(df: pd.DataFrame) -> bool:
    """成交量放大确认：最后一根成交量 > 过去N根平均 * 倍数"""
    if len(df) <= VOLUME_LOOKBACK:
        return False

    last_vol = df["volume"].iloc[-1]
    avg_vol = df["volume"].iloc[-VOLUME_LOOKBACK-1:-1].mean()
    return last_vol > avg_vol * VOLUME_MULTIPLIER


def rsi_confirmation(df: pd.DataFrame) -> bool:
    """RSI 超买且出现回落迹象"""
    if "rsi" not in df.columns:
        return False
    if len(df) < 3:
        return False

    rsi_last = df["rsi"].iloc[-1]
    rsi_prev = df["rsi"].iloc[-2]

    return (rsi_last < rsi_prev) and (rsi_prev > RSI_OVERBOUGHT)


def macd_confirmation(df: pd.DataFrame) -> bool:
    """MACD 死叉 或 明显走弱"""
    if "macd" not in df.columns or "macd_signal" not in df.columns:
        return False
    if len(df) < 3:
        return False

    macd_last = df["macd"].iloc[-1]
    sig_last = df["macd_signal"].iloc[-1]
    macd_prev = df["macd"].iloc[-2]
    sig_prev = df["macd_signal"].iloc[-2]

    # 死叉
    dead_cross = (macd_prev >= sig_prev) and (macd_last < sig_last)
    # 在零轴上方拐头向下
    weakening = (macd_last < macd_prev) and (macd_last > 0)

    return dead_cross or weakening
