import pandas as pd
import numpy as np

class ReversalModel:
    def __init__(self, df):
        """
        初始化模型
        df: 包含 ['open', 'high', 'low', 'close', 'volume', 'oi', 'long_ratio', 'funding'] 的 DataFrame
        数据频率建议: 15m 或 1h
        """
        self.df = df.copy()
        self._calculate_indicators()

    def _calculate_indicators(self):
        """计算基础技术指标"""
        # 1. EMA
        self.df['ema50'] = self.df['close'].ewm(span=50, adjust=False).mean()
        self.df['ema200'] = self.df['close'].ewm(span=200, adjust=False).mean()

        # 2. RSI (14)
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        self.df['rsi'] = 100 - (100 / (1 + gain / loss))

        # 3. MACD
        exp12 = self.df['close'].ewm(span=12, adjust=False).mean()
        exp26 = self.df['close'].ewm(span=26, adjust=False).mean()
        self.df['dif'] = exp12 - exp26
        self.df['dea'] = self.df['dif'].ewm(span=9, adjust=False).mean()
        self.df['macd_hist'] = (self.df['dif'] - self.df['dea']) * 2

        # 4. 辅助计算：OI 变化率 (过去 5 根均值对比)
        self.df['oi_ma'] = self.df['oi'].rolling(window=5).mean()
        self.df['oi_change'] = (self.df['oi'] - self.df['oi_ma'].shift(1)) / self.df['oi_ma'].shift(1)

        # 5. 辅助计算：成交量比率
        self.df['vol_ma'] = self.df['volume'].rolling(window=10).mean()
        self.df['vol_ratio'] = self.df['volume'] / self.df['vol_ma'].shift(1)

    def _check_divergence(self, index, lookback=15, direction="bullish"):
        """
        简单的背离检测 (最近 lookback 根K线)
        bullish: 价格创新低，RSI 没创新低
        bearish: 价格创新高，RSI 没创新高
        """
        if index < lookback: return False
        
        current_price = self.df['close'].iloc[index]
        current_rsi = self.df['rsi'].iloc[index]
        
        # 提取过去窗口的数据（不包含当前K线）
        past_window = self.df.iloc[index-lookback:index]
        
        if direction == "bullish":
            # 价格必须接近或低于过去窗口的最低价
            min_price = past_window['close'].min()
            min_rsi = past_window['rsi'].min()
            
            # 逻辑：当前价格破了(或接近)前低，但当前RSI高于前低RSI
            if current_price <= min_price * 1.001 and current_rsi > min_rsi + 1:
                return True
                
        elif direction == "bearish":
            max_price = past_window['close'].max()
            max_rsi = past_window['rsi'].max()
            
            if current_price >= max_price * 0.999 and current_rsi < max_rsi - 1:
                return True
                
        return False

    def evaluate(self, index=-1):
        """
        核心评估函数
        index: 评估哪一行的数据，默认 -1 (最新)
        """
        # 修正 index 为整数位置
        if index < 0: index = len(self.df) + index
        
        row = self.df.iloc[index]
        prev_row = self.df.iloc[index-1]
        
        # --- 第一步：判断趋势方向 ---
        # 简单逻辑：价格 < EMA200 且 EMA50 < EMA200 -> 下跌趋势 (寻找做多机会)
        # 否则如果价格 > EMA200 且 EMA50 > EMA200 -> 上涨趋势 (寻找做空机会)
        # 其他 -> 震荡 (这里为了简化，震荡偏空则按做多算，震荡偏多按做空算，或者降权)
        
        trend = "neutral"
        mode = "wait"
        
        if row['close'] < row['ema200'] and row['ema50'] < row['ema200']:
            trend = "downtrend"
            mode = "long_reversal" # 重点算 Bullish Score
        elif row['close'] > row['ema200'] and row['ema50'] > row['ema200']:
            trend = "uptrend"
            mode = "short_reversal" # 重点算 Bearish Score
        else:
            # 震荡市，看当前价格在 EMA200 上方还是下方来决定倾向
            if row['close'] < row['ema200']: mode = "long_reversal"
            else: mode = "short_reversal"

        score = 0
        details = {}

        # --- 第二步：计算分数 ---
        
        if mode == "long_reversal": # 下跌 -> 向上反转 (做多)
            
            # 1. 技术超卖 & 背离 (Max 40 -> 优化建议 30)
            sub_score = 0
            if row['rsi'] < 30: sub_score += 15
            if row['rsi'] < 20: sub_score += 5
            if self._check_divergence(index, direction="bullish"): sub_score += 10 # 降低了背离权重防止误判
            score += sub_score
            details['Tech_RSI'] = sub_score

            # 2. MACD 动能衰竭 (Max 20)
            sub_score = 0
            # 柱子连续缩短 (绿柱变短或红柱变短) - 这里简化判断 Histogram 变大 (负值变大趋向0，或正值变大)
            if row['macd_hist'] > prev_row['macd_hist']: sub_score += 10
            # 金叉附近
            if row['dif'] > row['dea'] and prev_row['dif'] < prev_row['dea']: sub_score += 10
            elif (row['dif'] - row['dea']) > 0 and (row['dif'] - row['dea']) < 5: sub_score += 5 # 已经在上方不远
            score += min(sub_score, 20)
            details['MACD'] = min(sub_score, 20)

            # 3. OI & 资金行为 (Max 20 -> 优化建议 25)
            sub_score = 0
            # 价格跌 + OI 大降 (多头爆仓)
            if row['oi_change'] < -0.03: sub_score += 15
            # 或者：轧空前兆 (OI 增 + 费率极负) - 实战优化
            elif row['oi_change'] > 0.03 and row['funding'] < -0.0005: sub_score += 15
            
            # 价格新低 OI 未新高 (简化判断)
            if row['close'] < prev_row['close'] and row['oi'] < prev_row['oi']: sub_score += 5
            score += min(sub_score, 25)
            details['OI_Funding'] = min(sub_score, 25)

            # 4. 多空结构 (Max 10) - 假设 long_ratio 是 大户多头占比
            sub_score = 0
            # 散户狂多，大户狂空 -> 此时 long_ratio (大户) 应该很低
            if row['long_ratio'] < 0.35: sub_score += 5
            if row['long_ratio'] < 0.25: sub_score += 5
            score += sub_score
            details['LS_Ratio'] = sub_score

            # 5. 量能与K线 (Max 10 -> 优化建议 15)
            sub_score = 0
            # 放量
            if row['vol_ratio'] > 2.0: sub_score += 5
            # 长下影线 (下影线长度 > 实体 * 2)
            lower_shadow = min(row['open'], row['close']) - row['low']
            body = abs(row['open'] - row['close'])
            if body > 0 and lower_shadow > body * 2: sub_score += 10
            score += min(sub_score, 15)
            details['Vol_Candle'] = min(sub_score, 15)

        else: # mode == "short_reversal" (做空)
            
            # 1. 技术超买 & 背离
            sub_score = 0
            if row['rsi'] > 70: sub_score += 15
            if row['rsi'] > 80: sub_score += 5
            if self._check_divergence(index, direction="bearish"): sub_score += 10
            score += sub_score
            details['Tech_RSI'] = sub_score

            # 2. MACD
            sub_score = 0
            if row['macd_hist'] < prev_row['macd_hist']: sub_score += 10
            if row['dif'] < row['dea'] and prev_row['dif'] > prev_row['dea']: sub_score += 10
            score += min(sub_score, 20)
            details['MACD'] = min(sub_score, 20)

            # 3. OI
            sub_score = 0
            if row['oi_change'] < -0.03: sub_score += 15 # 高位减仓
            elif row['oi_change'] > 0.03 and row['funding'] > 0.0005: sub_score += 15 # 诱多
            score += min(sub_score, 25)
            details['OI_Funding'] = min(sub_score, 25)

            # 4. 多空结构 (大户多头过度拥挤)
            sub_score = 0
            if row['long_ratio'] > 0.65: sub_score += 5
            if row['long_ratio'] > 0.75: sub_score += 5
            score += sub_score
            details['LS_Ratio'] = sub_score

            # 5. 量能
            sub_score = 0
            if row['vol_ratio'] > 2.0: sub_score += 5
            upper_shadow = row['high'] - max(row['open'], row['close'])
            body = abs(row['open'] - row['close'])
            if body > 0 and upper_shadow > body * 2: sub_score += 10
            score += min(sub_score, 15)
            details['Vol_Candle'] = min(sub_score, 15)

        # 最终封顶
        total_score = min(score, 100)
        
        return {
            "timestamp": str(row.name) if isinstance(row.name, pd.Timestamp) else index,
            "trend": trend,
            "signal_type": mode,
            "total_score": total_score,
            "details": details,
            "price": row['close'],
            "rsi": row['rsi']
        }

# --- 模拟数据生成与测试 ---
def generate_fake_data(n=300):
    """生成模拟的下跌然后反转的数据"""
    np.random.seed(42)
    prices = [50000]
    oi = [10000]
    
    # 模拟一个下跌趋势
    for i in range(1, n):
        change = np.random.normal(-50, 200) # 总体偏跌
        if i > 280: change = np.random.normal(100, 300) # 最后暴力反弹
        
        prices.append(prices[-1] + change)
        
        # 模拟OI：价格跌OI跌 (多头爆仓)
        oi_change = np.random.normal(0, 100)
        if i > 250 and i < 280: oi_change = -500 # 大跌时OI剧减
        oi.append(max(1000, oi[-1] + oi_change))

    df = pd.DataFrame({
        'close': prices,
        'open': [p + np.random.normal(0, 50) for p in prices],
        'high': [p + abs(np.random.normal(0, 100)) for p in prices],
        'low': [p - abs(np.random.normal(0, 100)) for p in prices],
        'volume': np.random.randint(100, 1000, n),
        'oi': oi,
        'long_ratio': np.random.uniform(0.2, 0.8, n),
        'funding': np.random.uniform(-0.001, 0.001, n)
    })
    
    # 手动制造最后一根K线的极端情况 (插针、RSI低、放量)
    df.iloc[-1, df.columns.get_loc('low')] = df.iloc[-1]['close'] * 0.98 # 长下影
    df.iloc[-1, df.columns.get_loc('volume')] = df['volume'].mean() * 3 # 巨量
    df.iloc[-1, df.columns.get_loc('long_ratio')] = 0.20 # 没什么人敢做多了
    df.iloc[-1, df.columns.get_loc('funding')] = -0.0006 # 费率负
    
    return df

# --- 运行示例 ---
if __name__ == "__main__":
    print("正在生成模拟数据...")
    df = generate_fake_data()
    
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