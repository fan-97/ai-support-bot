import asyncio
import logging
from typing import Optional

import httpx
import pandas as pd
from config.settings import BASE_URL, PROXY_URL

# HTTP client config (shared across calls)
_PROXIES = PROXY_URL or None
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


async def _fetch_json(url: str, params: dict) -> Optional[list]:
    """GET with proxy/timeout and a small retry backoff."""
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(proxy=_PROXIES, timeout=_TIMEOUT) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logging.warning(f"Request failed ({attempt + 1}/2): {url} | params={params} | error={exc}")
            await asyncio.sleep(1)
    return None


async def get_binance_klines(symbol: str, interval: str, limit: int = 200, market: str = "futures") -> Optional[pd.DataFrame]:
    """Fetch Binance kline data asynchronously."""
    if market == "futures":
        base_url = f"{BASE_URL}/fapi/v1/klines"
    else:
        base_url = f"{BASE_URL}/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    data = await _fetch_json(base_url, params)
    if not data:
        return None

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


async def get_current_funding_rate(symbol: str) -> float:
    """Fetch current funding rate; return 0 on failure."""
    url = f"{BASE_URL}/fapi/v1/premiumIndex"
    params = {"symbol": symbol}

    data = await _fetch_json(url, params)
    if not data:
        return 0.0

    try:
        return float(data.get("lastFundingRate", 0))
    except Exception as exc:
        logging.error(f"Funding Rate parse error: {exc}")
        return 0.0


async def get_open_interest(symbol: str, interval: str) -> float:
    """Fetch current Open Interest (Futures)."""
    url = f"{BASE_URL}/fapi/v1/openInterest"
    params = {"symbol": symbol}

    data = await _fetch_json(url, params)
    if not data:
        return 0.0

    try:
        return float(data.get("openInterest", 0))
    except Exception as exc:
        logging.error(f"Open Interest parse error: {exc}")
        return 0.0
