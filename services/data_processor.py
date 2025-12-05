import json
import numpy as np
import pandas as pd
import pandas_ta as ta


class CryptoDataProcessor:
    def __init__(self, limit: int = 50):
        self.limit = limit

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """基础指标（目标币与BTC共用）"""
        df['EMA20'] = ta.ema(df['close'], length=20)
        df['RSI'] = ta.rsi(df['close'], length=14)
        return df

    def calculate_target_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """目标币种的扩展指标"""
        df = self.calculate_indicators(df)

        macd = ta.macd(df['close'])
        df['MACD_Hist'] = macd['MACDh_12_26_9']

        bb = ta.bbands(df['close'], length=20, std=2)
        upper_col = next((c for c in bb.columns if c.startswith("BBU_")), None)
        lower_col = next((c for c in bb.columns if c.startswith("BBL_")), None)
        if upper_col is None or lower_col is None:
            missing = "BBU_*" if upper_col is None else "BBL_*"
            raise KeyError(f"Bollinger Band column {missing} not found in result: {bb.columns.tolist()}")
        df['BB_Upper'] = bb[upper_col]
        df['BB_Lower'] = bb[lower_col]

        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['Vol_Ratio'] = df['volume'] / ta.sma(df['volume'], length=20)
        return df

    def format_for_ai(self, df_target: pd.DataFrame, df_btc: pd.DataFrame, symbol: str, balance: float = 100) -> str:
        """生成AI输入：目标币与BTC 4h序列分开提供，不再合并"""
        recent_target = df_target.tail(self.limit).copy()
        recent_btc = df_btc.tail(self.limit).copy()
        recent_target = recent_target.where(pd.notnull(recent_target), None)
        recent_btc = recent_btc.where(pd.notnull(recent_btc), None)

        last_target = recent_target.iloc[-1]
        last_btc = recent_btc.iloc[-1]

        btc_context = {
            "trend": "BULLISH" if last_btc['close'] > last_btc['EMA20'] else "BEARISH",
            "rsi": last_btc['RSI'],
            "current_price": last_btc['close']
        }

        # 兼容不同时间列；若无列则使用索引
        t_col_target = 'timestamp' if 'timestamp' in recent_target.columns else ('open_time' if 'open_time' in recent_target.columns else None)
        t_col_btc = 'timestamp' if 'timestamp' in recent_btc.columns else ('open_time' if 'open_time' in recent_btc.columns else None)

        target_timestamps = (
            recent_target[t_col_target].astype(str).tolist()
            if t_col_target
            else recent_target.index.astype(str).tolist()
        )
        btc_timestamps = (
            recent_btc[t_col_btc].astype(str).tolist()
            if t_col_btc
            else recent_btc.index.astype(str).tolist()
        )

        target_sequences = {
            "timestamps": target_timestamps,
            "close": recent_target['close'].tolist(),
            "high": recent_target['high'].tolist(),
            "low": recent_target['low'].tolist(),
            "volume": recent_target['volume'].tolist(),
            "ema20": recent_target['EMA20'].tolist(),
            "rsi": recent_target['RSI'].tolist(),
            "macd_hist": recent_target['MACD_Hist'].tolist(),
            "bb_upper": recent_target['BB_Upper'].tolist(),
            "bb_lower": recent_target['BB_Lower'].tolist(),
            "atr": recent_target['ATR'].tolist(),
            "vol_ratio": recent_target['Vol_Ratio'].tolist(),
            "open_interest": recent_target['open_interest'].tolist() if 'open_interest' in recent_target else [],
            "funding_rate": recent_target['funding_rate'].tolist() if 'funding_rate' in recent_target else []
        }

        btc_sequences = {
            "timestamps": btc_timestamps,
            "close": recent_btc['close'].tolist(),
            "high": recent_btc['high'].tolist() if 'high' in recent_btc else [],
            "low": recent_btc['low'].tolist() if 'low' in recent_btc else [],
            "volume": recent_btc['volume'].tolist() if 'volume' in recent_btc else [],
            "ema20": recent_btc['EMA20'].tolist(),
            "rsi": recent_btc['RSI'].tolist()
        }

        ai_input = {
            "account_info": {
                "balance": balance,
                "available_margin": balance * 0.88
            },
            "market_context": {
                "target_symbol": symbol,
                "btc_context": btc_context,
                "current_price": last_target['close'],
                "volatility_atr": last_target['ATR']
            },
            "data_sequences": {
                "target": target_sequences,
                "btc": btc_sequences
            }
        }

        return json.dumps(ai_input, indent=2)


# ==========================================
# Demo run
# ==========================================
if __name__ == "__main__":
    dates = pd.date_range(start='2023-01-01', periods=100, freq='15min')
    df_target = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.uniform(1500, 1600, 100),
        'high': np.random.uniform(1500, 1600, 100),
        'low': np.random.uniform(1500, 1600, 100),
        'close': np.random.uniform(1500, 1600, 100),
        'volume': np.random.uniform(1000, 5000, 100)
    })
    df_target['high'] = df_target[['open', 'close']].max(axis=1) * 1.01
    df_target['low'] = df_target[['open', 'close']].min(axis=1) * 0.99

    df_btc = pd.DataFrame({
        'timestamp': dates,
        'close': np.random.uniform(20000, 21000, 100),
        'open': np.random.uniform(20000, 21000, 100),
        'high': np.random.uniform(20000, 21000, 100),
        'low': np.random.uniform(20000, 21000, 100),
        'volume': np.random.uniform(5000, 10000, 100)
    })

    processor = CryptoDataProcessor(limit=30)
    df_target = processor.calculate_target_indicators(df_target)
    df_btc = processor.calculate_indicators(df_btc)

    json_output = processor.format_for_ai(df_target, df_btc, symbol="ETHUSDT")
    print(json_output)
