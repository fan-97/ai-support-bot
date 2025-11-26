import requests
import pandas as pd
import logging
from config.settings import BASE_URL, PROXY_URL



def get_binance_klines(symbol: str, interval: str, limit: int = 200, market: str = "futures") -> pd.DataFrame:
    """
    从 Binance 获取 K 线数据，返回 DataFrame
    market = "futures" 使用合约接口；"spot" 使用现货接口
    """
    if market == "futures":
        base_url = f"{BASE_URL}/fapi/v1/klines"
    else:
        base_url = f"{BASE_URL}/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    resp = requests.get(base_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume",
        "ignore"
    ]
    df = pd.DataFrame(data, columns=cols)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
    df.set_index('open_time', inplace=True)
    price_cols = ["open", "high", "low", "close", "volume"]
    df[price_cols] = df[price_cols].astype(float)

    return df

def get_current_funding_rate(symbol: str) -> float:
    """获取当前资金费率"""
    url = f"{BASE_URL}/fapi/v1/premiumIndex"
    params = {"symbol": symbol}
    try:
        resp = requests.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return float(data.get("lastFundingRate", 0))
    except Exception as e:
        logging.error(f"Funding Rate Error: {e}")
        return 0.0