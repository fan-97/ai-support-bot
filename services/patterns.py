import pandas as pd
import mplfinance as mpf
import os

# ==============================================================================
# 第一部分：核心形态识别逻辑 (PatternRecognizer)
# ==============================================================================

class PatternRecognizer:
    def __init__(self, df):
        self.df = df

    def _get_candle(self, i):
        """获取第 i 根 K 线的基础数据"""
        if i < 0: i += len(self.df)
        row = self.df.iloc[i]
        body = abs(row['close'] - row['open'])
        upper = row['high'] - max(row['close'], row['open'])
        lower = min(row['close'], row['open']) - row['low']
        mid = (row['close'] + row['open']) / 2
        is_green = row['close'] > row['open']
        return {
            'open': row['open'], 'close': row['close'], 'high': row['high'], 'low': row['low'],
            'body': body, 'upper': upper, 'lower': lower, 'mid': mid, 'is_green': is_green
        }

    # --- 看涨形态 (Bullish) ---

    def is_hammer(self, i=-1):
        """[新增] 锤形线: 跌势底，形状同上吊线(下影长，上影短，实体小)"""
        c = self._get_candle(i)
        # 形状判断：下影线 >= 实体 * 2，上影线 <= 实体 * 0.5
        shape = (c['lower'] >= c['body'] * 2) and (c['upper'] <= c['body'] * 0.5)
        return shape

    def is_inverse_hammer(self, i=-1):
        """倒锤形: 跌势底，上影线长(>2倍实体)，下影线极短"""
        c = self._get_candle(i)
        return (c['upper'] >= c['body'] * 2) and (c['lower'] <= c['body'] * 0.5)

    def is_bullish_engulfing(self, i=-1):
        """多头吞噬: 前红后绿，绿包红"""
        curr = self._get_candle(i)
        prev = self._get_candle(i-1)
        color_match = (not prev['is_green']) and curr['is_green']
        engulfing = (curr['open'] <= prev['close']) and (curr['close'] >= prev['open'])
        return color_match and engulfing

    def is_piercing_line(self, i=-1):
        """穿刺线: 前长红，后长绿。低开，收盘刺入前实体50%上方"""
        curr = self._get_candle(i)
        prev = self._get_candle(i-1)
        if not ((not prev['is_green']) and curr['is_green']): return False
        prev_mid = (prev['open'] + prev['close']) / 2
        gap_down = curr['open'] <= prev['close']
        pierce = curr['close'] > prev_mid
        not_engulf = curr['close'] < prev['open']
        return gap_down and pierce and not_engulf

    def is_morning_star(self, i=-1):
        """早晨之星: 长红 -> 小星 -> 长绿"""
        c1 = self._get_candle(i-2)
        c2 = self._get_candle(i-1)
        c3 = self._get_candle(i)
        if not (not c1['is_green'] and c3['is_green']): return False
        small_body = c2['body'] < (c1['body'] * 0.5)
        low_position = c2['close'] < c1['close']
        c1_mid = (c1['open'] + c1['close']) / 2
        rebound = c3['close'] > c1_mid
        return small_body and low_position and rebound

    def is_three_white_soldiers(self, i=-1):
        """白色三兵: 三连阳，重心上移"""
        c1 = self._get_candle(i-2)
        c2 = self._get_candle(i-1)
        c3 = self._get_candle(i)
        all_green = c1['is_green'] and c2['is_green'] and c3['is_green']
        trend_up = (c2['close'] > c1['close']) and (c3['close'] > c2['close'])
        overlap = (c2['open'] > c1['open']) and (c2['open'] < c1['close']) and \
                  (c3['open'] > c2['open']) and (c3['open'] < c2['close'])
        short_shadow = (c3['upper'] < c3['body']) and (c2['upper'] < c2['body'])
        return all_green and trend_up and overlap and short_shadow

    # --- 看跌形态 (Bearish) ---

    def is_hanging_man(self, i=-1):
        """上吊线: 涨势顶，形状同锤子(下影长，上影短，实体小)"""
        c = self._get_candle(i)
        shape = (c['lower'] >= c['body'] * 2) and (c['upper'] <= c['body'] * 0.5)
        return shape

    def is_shooting_star(self, i=-1):
        """射击之星: 涨势顶，形状同倒锤(上影长，下影短，实体小)"""
        c = self._get_candle(i)
        shape = (c['upper'] >= c['body'] * 2) and (c['lower'] <= c['body'] * 0.5)
        return shape

    def is_bearish_engulfing(self, i=-1):
        """空头吞噬: 前绿后红，红包绿"""
        curr = self._get_candle(i)
        prev = self._get_candle(i-1)
        color_match = prev['is_green'] and (not curr['is_green'])
        engulfing = (curr['open'] >= prev['close']) and (curr['close'] <= prev['open'])
        return color_match and engulfing

    def is_evening_star(self, i=-1):
        """黄昏之星: 长绿 -> 小星 -> 长红"""
        c1 = self._get_candle(i-2)
        c2 = self._get_candle(i-1)
        c3 = self._get_candle(i)
        if not (c1['is_green'] and not c3['is_green']): return False
        small_body = c2['body'] < (c1['body'] * 0.5)
        high_position = c2['close'] > c1['close']
        c1_mid = (c1['open'] + c1['close']) / 2
        drop = c3['close'] < c1_mid
        return small_body and high_position and drop

    def is_three_black_crows(self, i=-1):
        """三只乌鸦: 三连阴，重心下移"""
        c1 = self._get_candle(i-2)
        c2 = self._get_candle(i-1)
        c3 = self._get_candle(i)
        all_red = (not c1['is_green']) and (not c2['is_green']) and (not c3['is_green'])
        trend_down = (c2['close'] < c1['close']) and (c3['close'] < c2['close'])
        overlap = (c2['open'] < c1['open']) and (c2['open'] > c1['close']) and \
                  (c3['open'] < c2['open']) and (c3['open'] > c2['close'])
        return all_red and trend_down and overlap

    def is_dark_cloud_cover(self, i=-1):
        """乌云盖顶: 前长绿，后长红。高开，收盘刺入前实体50%下方"""
        curr = self._get_candle(i)
        prev = self._get_candle(i-1)
        if not (prev['is_green'] and not curr['is_green']): return False
        prev_mid = (prev['open'] + prev['close']) / 2
        gap_up = curr['open'] > prev['close']
        pierce = curr['close'] < prev_mid
        not_engulf = curr['close'] > prev['open']
        return gap_up and pierce and not_engulf

    
# ==============================================================================
# 第二部分：K线数据生成器 (PatternDataGenerator)
# ==============================================================================

class DataGenerator:
    def create_base_trend(self, direction='down', length=3):
        """生成前置趋势"""
        data = []
        price = 100.0
        for _ in range(length):
            if direction == 'down':
                op = price
                cl = price - 2
                hi = price + 0.5
                lo = price - 2.5
                price -= 2
            else:
                op = price
                cl = price + 2
                hi = price + 2.5
                lo = price - 0.5
                price += 2
            data.append([op, hi, lo, cl])
        return data, price

    def generate(self, pattern_type):
        # --- 看涨形态 (需要前置跌势) ---
        bullish_patterns = ['hammer', 'inverse_hammer', 'bullish_engulfing', 
                           'piercing_line', 'morning_star', 'three_white_soldiers']
        
        if pattern_type in bullish_patterns:
            data, last_price = self.create_base_trend('down', 3)
            
            if pattern_type == 'hammer':
                # [新增] 锤形线: 实体小(绿)，下影长
                op = last_price - 1
                cl = op + 0.5   # 实体0.5
                hi = cl + 0.1   # 上影极短
                lo = op - 1.5   # 下影线1.5 (实体3倍)
                data.append([op, hi, lo, cl])
                
            elif pattern_type == 'inverse_hammer':
                op = last_price - 1
                cl = op + 0.5 
                hi = cl + 3.0 
                lo = op - 0.1 
                data.append([op, hi, lo, cl])
                
            elif pattern_type == 'bullish_engulfing':
                data[-1] = [94, 94.5, 91.5, 92] 
                data.append([91.5, 96, 91, 95]) 
                
            elif pattern_type == 'piercing_line':
                data[-1] = [95, 95.5, 90, 90.5] 
                data.append([90, 93.5, 89.5, 93])
                
            elif pattern_type == 'morning_star':
                data[-1] = [98, 98.5, 92, 92.5] 
                data.append([91, 91.5, 90, 90.5]) 
                data.append([91, 96, 90.5, 96]) 
                
            elif pattern_type == 'three_white_soldiers':
                start = last_price - 2
                data.append([start, start+2.2, start-0.2, start+2])
                data.append([start+1, start+3.2, start+0.8, start+3])
                data.append([start+2, start+4.2, start+1.8, start+4])

        # --- 看跌形态 (需要前置涨势) ---
        else:
            data, last_price = self.create_base_trend('up', 3)
            
            if pattern_type == 'hanging_man':
                op = last_price + 1
                cl = op - 0.5 
                hi = op + 0.1 
                lo = cl - 3.0 
                data.append([op, hi, lo, cl])
                
            elif pattern_type == 'shooting_star':
                op = last_price + 1
                cl = op - 0.5 
                hi = op + 3.0 
                lo = cl - 0.1
                data.append([op, hi, lo, cl])
                
            elif pattern_type == 'bearish_engulfing':
                data[-1] = [106, 108.5, 105.5, 108] 
                data.append([108.5, 109, 104, 105]) 
                
            elif pattern_type == 'evening_star':
                data[-1] = [102, 108, 101.5, 107.5] 
                data.append([109, 109.5, 108.5, 108.5]) 
                data.append([108, 108.5, 101, 101]) 
                
            elif pattern_type == 'three_black_crows':
                start = last_price + 2
                data.append([start, start+0.2, start-2.2, start-2])
                data.append([start-1, start-0.8, start-3.2, start-3])
                data.append([start-2, start-1.8, start-4.2, start-4])
                
            elif pattern_type == 'dark_cloud_cover':
                data[-1] = [105, 110, 104.5, 109.5] 
                data.append([111, 111.5, 105.5, 106])

        df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close'])
        df.index = pd.date_range(start='2024-01-01', periods=len(df), freq='D')
        return df


# ==============================================================================
# 第三部分：测试与可视化 (Visualizer)
# ==============================================================================

def run_tests():
    output_dir = "pattern_tests"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    generator = DataGenerator()
    
    # 所有的测试项
    patterns = {
        'hammer': 'is_hammer',                  # [新增]
        'inverse_hammer': 'is_inverse_hammer',
        'bullish_engulfing': 'is_bullish_engulfing',
        'piercing_line': 'is_piercing_line',
        'morning_star': 'is_morning_star',
        'three_white_soldiers': 'is_three_white_soldiers',
        
        'hanging_man': 'is_hanging_man',
        'shooting_star': 'is_shooting_star',
        'bearish_engulfing': 'is_bearish_engulfing',
        'evening_star': 'is_evening_star',
        'three_black_crows': 'is_three_black_crows',
        'dark_cloud_cover': 'is_dark_cloud_cover'
    }

    print(f"开始测试，图片将保存至 {output_dir}/ 文件夹...\n")

    for p_name, func_name in patterns.items():
        print(f"正在测试: [{p_name}]...", end=" ")
        
        df = generator.generate(p_name)
        recognizer = PatternRecognizer(df)
        check_func = getattr(recognizer, func_name)
        is_detected = check_func() 
        
        status = "✅ 成功" if is_detected else "❌ 失败"
        print(status)
        
        # 绘图设置
        title = f"{p_name} ({status})"
        save_path = f"{output_dir}/{p_name}.png"
        mc = mpf.make_marketcolors(up='green', down='red', edge='inherit', wick='inherit', volume='in')
        s = mpf.make_mpf_style(marketcolors=mc)
        mpf.plot(df, type='candle', style=s, title=title, savefig=save_path)

    print(f"\n所有测试完成！请检查 '{output_dir}' 文件夹中的图片。")

if __name__ == "__main__":
    run_tests()