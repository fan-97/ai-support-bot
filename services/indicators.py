# indicators.py
import numpy as np
import pandas as pd

from config.settings import (
    RSI_PERIOD,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
)


def calc_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """计算 RSI (Wilder 简化版)"""
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    gain = pd.Series(gain, index=series.index)
    loss = pd.Series(loss, index=series.index)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calc_macd(series: pd.Series,
              fast: int = MACD_FAST,
              slow: int = MACD_SLOW,
              signal: int = MACD_SIGNAL):
    """计算 MACD 指标"""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def calc_ema(series: pd.Series, span: int) -> pd.Series:
    """Calculate Exponential Moving Average"""
    return series.ewm(span=span, adjust=False).mean()


def calc_ma(series: pd.Series, period: int) -> pd.Series:
    """Calculate Simple Moving Average"""
    return series.rolling(window=period).mean()


def calc_bollinger_bands(series: pd.Series, period: int = 20, std_dev: int = 2):
    """Calculate Bollinger Bands"""
    ma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)
    return upper, ma, lower


def calc_kdj(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 9, k_period: int = 3, d_period: int = 3):
    """Calculate KDJ Indicator"""
    low_min = low.rolling(window=period).min()
    high_max = high.rolling(window=period).max()
    
    rsv = (close - low_min) / (high_max - low_min + 1e-9) * 100
    
    # K = 2/3 * PrevK + 1/3 * RSV
    # D = 2/3 * PrevD + 1/3 * K
    # J = 3 * K - 2 * D
    
    # Pandas ewm doesn't directly support the custom alpha for KDJ recursion easily in one line without loop or custom adjust
    # Using simple SMA for K and D as common approximation or standard EMA with alpha=1/period
    # Standard KDJ uses Wilder's smoothing (alpha=1/3) equivalent to ewm(com=2)
    
    k = rsv.ewm(com=k_period-1, adjust=False).mean()
    d = k.ewm(com=d_period-1, adjust=False).mean()
    j = 3 * k - 2 * d
    
    return k, d, j
