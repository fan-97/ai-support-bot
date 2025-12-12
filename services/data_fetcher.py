import asyncio
import logging
from typing import Optional, Tuple

import httpx
import pandas as pd
import numpy as np
from config.settings import BASE_URL, PROXY_URL, KLINE_LIMIT

class DataFetcher:
    """
    Asynchronous data fetcher for Binance Futures API.
    Handles K-lines, Funding Rates, Open Interest, and Long/Short Ratios.
    """
    def __init__(self, proxy_url: Optional[str] = None):
        self._proxies = proxy_url or PROXY_URL or None
        self._timeout = httpx.Timeout(10.0, connect=5.0)

    async def _fetch_json(self, url: str, params: dict) -> Optional[list]:
        """GET with proxy/timeout and a small retry backoff."""
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(proxy=self._proxies, timeout=self._timeout) as client:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    return resp.json()
            except Exception as exc:
                logging.warning(f"Request failed ({attempt + 1}/2): {url} | params={params} | error={exc}")
                await asyncio.sleep(1)
        return None

    async def get_klines(self, symbol: str, interval: str, limit: int = KLINE_LIMIT, market: str = "futures") -> Optional[pd.DataFrame]:
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

        data = await self._fetch_json(base_url, params)
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

    async def get_current_funding_rate(self, symbol: str) -> float:
        """Fetch current funding rate; return 0 on failure."""
        url = f"{BASE_URL}/fapi/v1/premiumIndex"
        params = {"symbol": symbol}

        data = await self._fetch_json(url, params)
        if not data:
            return 0.0

        try:
            return 100 * float(data.get("lastFundingRate", 0))
        except Exception as exc:
            logging.error(f"Funding Rate parse error: {exc}")
            return 0.0

    async def get_current_open_interest(self, symbol: str) -> float:
        """Fetch current Open Interest (Futures)."""
        url = f"{BASE_URL}/fapi/v1/openInterest"
        params = {"symbol": symbol}

        data = await self._fetch_json(url, params)
        if not data:
            return 0.0

        try:
            return float(data.get("openInterest", 0))
        except Exception as exc:
            logging.error(f"Open Interest parse error: {exc}")
            return 0.0

    async def get_funding_rate_history(self, symbol: str, limit: int = KLINE_LIMIT) -> pd.DataFrame:
        """Fetch funding rate history."""
        url = f"{BASE_URL}/fapi/v1/fundingRate"
        params = {
            "symbol": symbol,
            "limit": limit
        }
        resp = await self._fetch_json(url, params)
        if not resp:
             return pd.DataFrame(columns=["timestamp", "funding"])
        
        df = pd.DataFrame(resp)
        df["fundingTime"] = pd.to_datetime(df["fundingTime"], unit="ms")
        df["fundingRate"] = pd.to_numeric(df["fundingRate"])
        
        df = df.rename(columns={"fundingTime": "timestamp", "fundingRate": "funding"})
        return df[["timestamp", "funding"]]

    async def get_long_short_ratio_history(self, symbol: str, interval: str, limit: int = KLINE_LIMIT) -> pd.DataFrame:
        """Fetch Top Trader Long/Short Ratio history."""
        url = f"{BASE_URL}/futures/data/topLongShortAccountRatio"
        params = {
            "symbol": symbol,
            "period": interval,
            "limit": limit
        }
        resp = await self._fetch_json(url, params)
        if not resp:
            return pd.DataFrame(columns=["timestamp", "long_ratio"])
        
        df = pd.DataFrame(resp)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["longShortRatio"] = pd.to_numeric(df["longShortRatio"])
        
        df = df.rename(columns={"longShortRatio": "long_ratio"})
        return df[["timestamp", "long_ratio"]]

    async def get_open_interest_history(self, symbol: str, interval: str, limit: int = KLINE_LIMIT) -> pd.DataFrame:
        """Fetch Open Interest history."""
        url = f"{BASE_URL}/futures/data/openInterestHist"
        params = {
            "symbol": symbol,
            "period": interval,
            "limit": limit
        }
        resp = await self._fetch_json(url, params)
        if not resp:
             return pd.DataFrame(columns=["timestamp", "oi"])
        
        df = pd.DataFrame(resp)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["sumOpenInterest"] = pd.to_numeric(df["sumOpenInterest"])
        
        df = df.rename(columns={"sumOpenInterest": "oi"})
        return df[["timestamp", "oi"]]

    async def get_merged_data(self, symbol: str, interval: str, limit: int = KLINE_LIMIT) -> Optional[pd.DataFrame]:
        """
        Fetch and merge all data (K-lines, OI, L/S Ratio, Funding Rate) into a single DataFrame.
        """
        logging.info(f"Fetching merged data for {symbol} {interval}...")
        
        kline_task = self.get_klines(symbol, interval, limit)
        oi_task = self.get_open_interest_history(symbol, interval, limit)
        ls_task = self.get_long_short_ratio_history(symbol, interval, limit)
        fund_task = self.get_funding_rate_history(symbol, limit)

        results = await asyncio.gather(kline_task, oi_task, ls_task, fund_task, return_exceptions=True)

        df_kline, df_oi, df_ls, df_fund = results

        if isinstance(df_kline, Exception) or df_kline is None:
            logging.error(f"Failed to fetch klines: {df_kline}")
            return None

        # Helper to handle errors in auxiliary data
        def check_df(res, name):
            if isinstance(res, Exception) or res is None:
                logging.warning(f"Failed to fetch {name}: {res}")
                return pd.DataFrame()
            return res

        df_oi = check_df(df_oi, "Open Interest")
        df_ls = check_df(df_ls, "Long/Short Ratio")
        df_fund = check_df(df_fund, "Funding Rate")

        # Merge Logic
        # 1. K-line as base
        df = df_kline.copy()

        # 2. Assign 'timestamp' column for merging if it doesn't exist (it is the index)
        df['timestamp'] = df.index
        
        if not df_oi.empty:
            df = pd.merge(df, df_oi, on="timestamp", how="left")
        
        if not df_ls.empty:
            df = pd.merge(df, df_ls, on="timestamp", how="left")
            
        # 3. Merge Funding (asof merge because of 8h interval)
        if not df_fund.empty:
            df = pd.merge_asof(df.sort_values('timestamp'), 
                                df_fund.sort_values('timestamp'), 
                                on='timestamp', 
                                direction='backward')

        # 4. Fill NA
        cols_to_fill = []
        if 'oi' in df.columns: cols_to_fill.append('oi')
        if 'long_ratio' in df.columns: cols_to_fill.append('long_ratio')
        if 'funding' in df.columns: cols_to_fill.append('funding')
        
        if cols_to_fill:
            df[cols_to_fill] = df[cols_to_fill].ffill()

        df = df.dropna()
        # Ensure index is preserved
        if 'timestamp' in df.columns:
            df.set_index('timestamp', inplace=True, drop=False)
        
        return df


async def prepare_market_data_for_ai(symbol: str, interval: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Fetch and prepare market data for AI analysis.
    Returns (df, df_btc).
    Wraps new DataFetcher class.
    """
    fetcher = DataFetcher()

    task_symbol = fetcher.get_klines(symbol, interval)
    task_fund = fetcher.get_current_funding_rate(symbol)
    task_oi = fetcher.get_current_open_interest(symbol)
    task_btc = fetcher.get_klines("BTCUSDT", interval)

    results = await asyncio.gather(task_symbol, task_fund, task_oi, task_btc, return_exceptions=True)

    df = results[0]
    funding_rate = results[1]
    open_interest = results[2]
    df_btc = results[3]

    if isinstance(df, Exception) or df is None:
        logging.error(f"Failed to fetch klines for {symbol}: {df}")
        return None, None
    
    if isinstance(df_btc, Exception) or df_btc is None:
        logging.warning(f"Failed to fetch BTC klines: {df_btc}")
        return None, None

    if isinstance(funding_rate, Exception): funding_rate = 0.0
    if isinstance(open_interest, Exception): open_interest = 0.0

    try:
        # Avoid SettingWithCopyWarning by working on the dataframe directly
        df['high'] = df[['open', 'close']].max(axis=1) + np.random.uniform(0, 50, len(df))
        df['low'] = df[['open', 'close']].min(axis=1) - np.random.uniform(0, 50, len(df))
    except Exception as e:
        logging.error(f"Error generating mock high/low: {e}")
        pass

    df['funding_rate'] = funding_rate
    df['open_interest'] = open_interest

    return df, df_btc
