import asyncio
import logging
from typing import Optional

import httpx
import pandas as pd
import numpy as np
from config.settings import BASE_URL, PROXY_URL, KLINE_LIMIT

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


async def get_binance_klines(symbol: str, interval: str, limit: int = KLINE_LIMIT, market: str = "futures") -> Optional[pd.DataFrame]:
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
        return 100*float(data.get("lastFundingRate", 0))
    except Exception as exc:
        logging.error(f"Funding Rate parse error: {exc}")
        return 0.0


async def get_open_interest(symbol: str) -> float:
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


async def prepare_market_data_for_ai(symbol: str, interval: str) -> tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Fetch and prepare market data for AI analysis.
    Returns (df, df_btc).
    """
    # Parallel fetch
    results = await asyncio.gather(
        get_binance_klines(symbol, interval=interval),
        get_current_funding_rate(symbol),
        get_open_interest(symbol),
        get_binance_klines("BTCUSDT", interval=interval),
        return_exceptions=True
    )

    df = results[0]
    funding_rate = results[1]
    open_interest = results[2]
    df_btc = results[3]

    # Check for errors in critical data
    if isinstance(df, Exception) or df is None:
        logging.error(f"Failed to fetch klines for {symbol}: {df}")
        return None, None
    
    if isinstance(df_btc, Exception) or df_btc is None:
        logging.warning(f"Failed to fetch BTC klines: {df_btc}")
        # We might proceed without BTC data or handle it upstream, 
        # but for now let's return None to be safe if it's required
        # or maybe just log it. The original code didn't explicitly handle df_btc failure 
        # other than potentially crashing. Let's return None for safety.
        return None, None

    # Handle other results being exceptions (defaults are 0.0 in original functions but gather returns Exception if raised)
    # Our get_current_funding_rate and get_open_interest swallow errors and return 0.0, 
    # so they shouldn't be Exceptions unless something really weird happens.
    if isinstance(funding_rate, Exception): funding_rate = 0.0
    if isinstance(open_interest, Exception): open_interest = 0.0

    # Apply mock high/low logic (from user's code)
    # Note: Using numpy for random generation as in original code
    try:
        df['high'] = df[['open', 'close']].max(axis=1) + np.random.uniform(0, 50, len(df))
        df['low'] = df[['open', 'close']].min(axis=1) - np.random.uniform(0, 50, len(df))
    except Exception as e:
        logging.error(f"Error generating mock high/low: {e}")
        # Fallback to existing high/low if calculation fails
        pass

    df['funding_rate'] = funding_rate
    df['open_interest'] = open_interest

    return df, df_btc
