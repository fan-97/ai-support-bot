import requests
import pandas as pd
import logging
from config.settings import BASE_URL, PROXY_URL

def calculate_indicators(df):
    """计算 RSI 和 MACD"""
    # 1. RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # 2. MACD (12, 26, 9)
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd_dif'] = exp12 - exp26
    df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = (df['macd_dif'] - df['macd_dea']) * 2
    return df

def get_market_data(symbol, interval):
    """从币安获取K线和费率"""
    try:
        # 获取 K 线 (拿 100 根以保证指标计算准确)
        kline_url = f"{BASE_URL}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': 100}
        proxies = {'https': PROXY_URL} if PROXY_URL else None

        resp = requests.get(kline_url, params=params, proxies=proxies, timeout=10)
        data = resp.json()

        if not isinstance(data, list): return None, 0

        # 修复列名
        df = pd.DataFrame(data, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'ct', 'qv', 'n', 'tb', 'tq', 'ig'
        ])

        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.set_index('time', inplace=True)

        # 数据类型转换
        cols = ['open', 'high', 'low', 'close', 'volume']
        df[cols] = df[cols].astype(float)

        # 计算指标
        df = calculate_indicators(df)

        # 获取费率
        fund_url = f"{BASE_URL}/fapi/v1/premiumIndex"
        f_resp = requests.get(fund_url, params={'symbol': symbol}, proxies=proxies, timeout=10)
        funding_rate = float(f_resp.json().get('lastFundingRate', 0)) * 100

        return df, funding_rate
    except Exception as e:
        logging.error(f"Data error for {symbol}: {e}")
        return None, 0
