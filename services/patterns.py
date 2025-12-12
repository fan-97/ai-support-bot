import logging
from services.data_processor import CryptoDataProcessor

logger = logging.getLogger(__name__)


class CandlePatternDetector:
    """
    形态检测器

    df 要包含至少: ['open', 'high', 'low', 'close']
    index 为时间顺序递增
    """

    def __init__(self, df, trend_lookback=5, trend_threshold=0.002):
        self.df = df
        self.trend_lookback = trend_lookback
        self.trend_threshold = trend_threshold  # 比如 0.2% 以上才算明显趋势

    # ================== 基础工具 ==================

    def _get_candle(self, i):
        """获取第 i 根 K 线的基础数据"""
        if i < 0:
            i += len(self.df)
        row = self.df.iloc[i]

        body = abs(row["close"] - row["open"])
        upper = row["high"] - max(row["close"], row["open"])
        lower = min(row["close"], row["open"]) - row["low"]
        mid = (row["close"] + row["open"]) / 2
        is_green = row["close"] > row["open"]

        return {
            "open": float(row["open"]),
            "close": float(row["close"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "body": float(body),
            "upper": float(upper),
            "lower": float(lower),
            "mid": float(mid),
            "is_green": bool(is_green),
        }
    def detect_patterns(self):
        patterns = []
        for i in range(len(self.df)):
            if self.is_hammer(i):
                patterns.append('Hammer')
            elif self.is_inverse_hammer(i):
                patterns.append('Inverse Hammer')
            elif self.is_bullish_engulfing(i):
                patterns.append('Bullish Engulfing')
            elif self.is_piercing_line(i):
                patterns.append('Piercing Line')
            elif self.is_morning_star(i):
                patterns.append('Morning Star')
            elif self.is_three_white_soldiers(i):
                patterns.append('Three White Soldiers')
            elif self.is_hanging_man(i):
                patterns.append('Hanging Man')
            elif self.is_shooting_star(i):
                patterns.append('Shooting Star')
            elif self.is_bearish_engulfing(i):
                patterns.append('Bearish Engulfing')
            elif self.is_evening_star(i):
                patterns.append('Evening Star')
            elif self.is_three_black_crows(i):
                patterns.append('Three Black Crows')
            elif self.is_dark_cloud_cover(i):
                patterns.append('Dark Cloud Cover')
        return patterns

    def _get_trend(self, i=-1, lookback=None):
        
        """
        使用 EMA 的方向来判断趋势：

        返回:
          1  = EMA 明显向上（上涨趋势）
         -1  = EMA 明显向下（下跌趋势）
          0  = EMA 基本走平（震荡/无明显趋势）
        """
        if lookback is None:
            lookback = self.trend_lookback

        # 处理负索引
        if i < 0:
            i += len(self.df)
        processor = CryptoDataProcessor()
        processor.calculate_indicators(self.df)
        if "EMA20" not in self.df.columns:
            return 0  # 防御性处理

        start = max(0, i - lookback + 1)
        emas = self.df["EMA20"].iloc[start : i + 1]

        if len(emas) < 2:
            return 0

        # 用 EMA 的变化比例来判断方向
        ema_start = emas.iloc[0]
        ema_end = emas.iloc[-1]

        if ema_start == 0:
            return 0

        change = ema_end / ema_start - 1  # 比例变化
        if change > self.trend_threshold:
            return 1      # 上涨趋势
        elif change < -self.trend_threshold:
            return -1     # 下跌趋势
        else:
            return 0      # 震荡

    def _has_min_body(self, c, min_ratio=0.1):
        """
        简单过滤极小实体（十字星之类）
        min_ratio: 实体相对全长的最小比例
        """
        full_range = c["high"] - c["low"]
        if full_range <= 0:
            return False
        return c["body"] / full_range >= min_ratio

    # ================== 总入口 ==================

    def detect_patterns(self, i=-1):
        """
        检测第 i 根 K 线附近的形态

        返回:
            (matched, pattern_name)
            matched: True/False
            pattern_name: str or None
        你如果想保持跟原来一样只要 True/False，可以只用 matc    hed.
        """
        trend = self._get_trend(i)
        print(f"Local trend at {i}: {trend}")
        logger.debug(f"Local trend at {i}: {trend}")

        bullish_patterns = [
            self.is_hammer,
            self.is_inverse_hammer,
            self.is_bullish_engulfing,
            self.is_piercing_line,
            self.is_morning_star,
            self.is_three_white_soldiers,
        ]

        bearish_patterns = [
            self.is_hanging_man,
            self.is_shooting_star,
            self.is_bearish_engulfing,
            self.is_evening_star,
            self.is_three_black_crows,
            self.is_dark_cloud_cover,
        ]

        # 按你说的逻辑：
        #   下跌趋势 -> 只找看涨反转
        #   上涨趋势 -> 只找看跌反转
        #   震荡 -> 两边都看（你可以改成直接返回 False）
        if trend == -1:
            candidates = bullish_patterns
        elif trend == 1:
            candidates = bearish_patterns
        else:
            return False,None

        for p in candidates:
            if p(i):
                logger.info(f"Pattern MATCH: {p.__name__} at index {i}")
                return True, p.__name__

        return False, None

    # ================== 看涨形态 (Bullish) ==================

    def is_hammer(self, i=-1):
        """锤形线: 跌势底部，下影长，上影短，实体小"""
        # 必须在跌势
        if self._get_trend(i) != -1:
            return False

        c = self._get_candle(i)
        if not self._has_min_body(c):
            return False

        shape = (c["lower"] >= c["body"] * 2) and (c["upper"] <= c["body"] * 0.5)
        if shape:
            logger.debug(
                f"Hammer detected at {i}: lower={c['lower']:.4f}, body={c['body']:.4f}"
            )
        return shape

    def is_inverse_hammer(self, i=-1):
        """倒锤形: 跌势底，上影线长(>2倍实体)，下影线极短"""
        if self._get_trend(i) != -1:
            return False

        c = self._get_candle(i)
        if not self._has_min_body(c):
            return False

        shape = (c["upper"] >= c["body"] * 2) and (c["lower"] <= c["body"] * 0.5)
        if shape:
            logger.debug(
                f"Inverse Hammer detected at {i}: upper={c['upper']:.4f}, body={c['body']:.4f}"
            )
        return shape

    def is_bullish_engulfing(self, i=-1):
        """多头吞噬: 前一根为阴，后一根为阳，阳线实体完全包住前一根实体"""
        if self._get_trend(i) != -1:
            return False

        curr = self._get_candle(i)
        prev = self._get_candle(i - 1)

        # 颜色检查: prev 红, curr 绿
        if prev["is_green"] or (not curr["is_green"]):
            return False

        # 实体不能太小
        if not (self._has_min_body(curr) and self._has_min_body(prev)):
            return False

        engulfing = (curr["open"] <= prev["close"]) and (curr["close"] >= prev["open"])
        if engulfing:
            logger.debug(
                f"Bullish Engulfing at {i}: "
                f"Prev({prev['open']}->{prev['close']}), "
                f"Curr({curr['open']}->{curr['close']})"
            )
        return engulfing

    def is_piercing_line(self, i=-1):
        """穿刺线: 前长阴，后长阳。低开，收盘刺入前实体50%以上但未完全吞没"""
        if self._get_trend(i) != -1:
            return False

        curr = self._get_candle(i)
        prev = self._get_candle(i - 1)

        if not ((not prev["is_green"]) and curr["is_green"]):
            return False

        if not (self._has_min_body(curr) and self._has_min_body(prev)):
            return False

        prev_mid = (prev["open"] + prev["close"]) / 2

        # gap_down 条件放宽处理（加密货币 24/7 没法严格 gap）
        gap_down = curr["open"] <= prev["close"]
        pierce = curr["close"] > prev_mid
        not_engulf = curr["close"] < prev["open"]

        if gap_down and pierce and not_engulf:
            logger.debug(
                f"Piercing Line at {i}: "
                f"gap_down={gap_down}, pierce={pierce}, not_engulf={not_engulf}"
            )
            return True
        return False

    def is_morning_star(self, i=-1):
        """早晨之星: 长阴 -> 小实体星线 -> 长阳，出现在跌势底部"""
        if self._get_trend(i) != -1:
            return False

        c1 = self._get_candle(i - 2)
        c2 = self._get_candle(i - 1)
        c3 = self._get_candle(i)

        if not ((not c1["is_green"]) and c3["is_green"]):
            return False

        if not (self._has_min_body(c1) and self._has_min_body(c3)):
            return False

        small_body = c2["body"] < (c1["body"] * 0.5)
        low_position = c2["close"] < c1["close"]
        c1_mid = (c1["open"] + c1["close"]) / 2
        rebound = c3["close"] > c1_mid

        res = small_body and low_position and rebound
        if res:
            logger.debug(
                f"Morning Star at {i}: "
                f"small_body={small_body}, low_pos={low_position}, rebound={rebound}"
            )
        return res

    def is_three_white_soldiers(self, i=-1):
        """白色三兵: 三连阳，重心上移，出现在跌势末端"""
        if self._get_trend(i) != -1:
            return False

        c1 = self._get_candle(i - 2)
        c2 = self._get_candle(i - 1)
        c3 = self._get_candle(i)

        all_green = c1["is_green"] and c2["is_green"] and c3["is_green"]
        trend_up = (c2["close"] > c1["close"]) and (c3["close"] > c2["close"])

        # 开盘在前一根实体内部
        overlap = (
            (c2["open"] > min(c1["open"], c1["close"]))
            and (c2["open"] < max(c1["open"], c1["close"]))
            and (c3["open"] > min(c2["open"], c2["close"]))
            and (c3["open"] < max(c2["open"], c2["close"]))
        )

        # 影线不宜太长
        short_shadow = (c3["upper"] < c3["body"]) and (c2["upper"] < c2["body"])

        res = all_green and trend_up and overlap and short_shadow
        if res:
            logger.debug(f"Three White Soldiers at {i}")
        return res

    # ================== 看跌形态 (Bearish) ==================

    def is_hanging_man(self, i=-1):
        """上吊线: 涨势顶，下影长，上影短，实体小"""
        if self._get_trend(i) != 1:
            return False

        c = self._get_candle(i)
        if not self._has_min_body(c):
            return False

        shape = (c["lower"] >= c["body"] * 2) and (c["upper"] <= c["body"] * 0.5)
        if shape:
            logger.debug(
                f"Hanging Man detected at {i}: lower={c['lower']:.4f}, body={c['body']:.4f}"
            )
        return shape

    def is_shooting_star(self, i=-1):
        """射击之星: 涨势顶，上影长，下影短，实体小"""
        if self._get_trend(i) != 1:
            return False

        c = self._get_candle(i)
        if not self._has_min_body(c):
            return False

        shape = (c["upper"] >= c["body"] * 2) and (c["lower"] <= c["body"] * 0.5)
        if shape:
            logger.debug(
                f"Shooting Star detected at {i}: upper={c['upper']:.4f}, body={c['body']:.4f}"
            )
        return shape

    def is_bearish_engulfing(self, i=-1):
        """空头吞噬: 前阳后阴，阴线实体完全包住前一根实体"""
        if self._get_trend(i) != 1:
            return False

        curr = self._get_candle(i)
        prev = self._get_candle(i - 1)

        if (not prev["is_green"]) or curr["is_green"]:
            return False

        if not (self._has_min_body(curr) and self._has_min_body(prev)):
            return False

        engulfing = (curr["open"] >= prev["close"]) and (curr["close"] <= prev["open"])
        if engulfing:
            logger.debug(
                f"Bearish Engulfing at {i}: "
                f"Prev({prev['open']}->{prev['close']}), "
                f"Curr({curr['open']}->{curr['close']})"
            )
        return engulfing

    def is_evening_star(self, i=-1):
        """黄昏之星: 长阳 -> 小星 -> 长阴，出现在涨势顶部"""
        if self._get_trend(i) != 1:
            return False

        c1 = self._get_candle(i - 2)
        c2 = self._get_candle(i - 1)
        c3 = self._get_candle(i)

        if not (c1["is_green"] and (not c3["is_green"])):
            return False

        if not (self._has_min_body(c1) and self._has_min_body(c3)):
            return False

        small_body = c2["body"] < (c1["body"] * 0.5)
        high_position = c2["close"] > c1["close"]
        c1_mid = (c1["open"] + c1["close"]) / 2
        drop = c3["close"] < c1_mid

        res = small_body and high_position and drop
        if res:
            logger.debug(
                f"Evening Star at {i}: small={small_body}, high_pos={high_position}, drop={drop}"
            )
        return res

    def is_three_black_crows(self, i=-1):
        """三只乌鸦: 三连阴，重心下移，出现在涨势顶部"""
        if self._get_trend(i) != 1:
            return False

        c1 = self._get_candle(i - 2)
        c2 = self._get_candle(i - 1)
        c3 = self._get_candle(i)

        all_red = (not c1["is_green"]) and (not c2["is_green"]) and (not c3["is_green"])
        trend_down = (c2["close"] < c1["close"]) and (c3["close"] < c2["close"])

        # 开盘在前一根实体内部（注意前一根是阴线，open>close）
        overlap = (
            (c2["open"] < c1["open"])
            and (c2["open"] > c1["close"])
            and (c3["open"] < c2["open"])
            and (c3["open"] > c2["close"])
        )

        res = all_red and trend_down and overlap
        if res:
            logger.debug(f"Three Black Crows at {i}")
        return res

    def is_dark_cloud_cover(self, i=-1):
        """乌云盖顶: 前长阳，后长阴。高开，收盘跌入前实体50%以下但未完全吞没"""
        if self._get_trend(i) != 1:
            return False

        curr = self._get_candle(i)
        prev = self._get_candle(i - 1)

        if not (prev["is_green"] and (not curr["is_green"])):
            return False

        if not (self._has_min_body(curr) and self._has_min_body(prev)):
            return False

        prev_mid = (prev["open"] + prev["close"]) / 2
        gap_up = curr["open"] > prev["close"]
        pierce = curr["close"] < prev_mid
        not_engulf = curr["close"] > prev["open"]

        res = gap_up and pierce and not_engulf
        if res:
            logger.debug(
                f"Dark Cloud Cover at {i}: gap_up={gap_up}, pierce={pierce}, not_engulf={not_engulf}"
            )
        return res
