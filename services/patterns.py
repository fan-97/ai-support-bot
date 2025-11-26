# patterns.py
import pandas as pd


def is_bearish_engulfing(prev: pd.Series, last: pd.Series) -> bool:
    """看跌吞没：第二根大阴线实体包住第一根阳线实体"""
    o1, h1, l1, c1 = prev["open"], prev["high"], prev["low"], prev["close"]
    o2, h2, l2, c2 = last["open"], last["high"], last["low"], last["close"]

    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)

    return (
        c1 > o1 and          # 第一根为阳线
        c2 < o2 and          # 第二根为阴线
        body2 > body1 * 1.1 and
        o2 >= c1 and         # 高开/平开在前一收盘之上
        c2 <= o1             # 收盘跌破前一开盘，实体包住
    )


def is_dark_cloud_cover(prev: pd.Series, last: pd.Series) -> bool:
    """乌云盖顶：第二根阴线高开后，收盘深入前一阳线实体 50%以上"""
    o1, h1, l1, c1 = prev["open"], prev["high"], prev["low"], prev["close"]
    o2, h2, l2, c2 = last["open"], last["high"], last["low"], last["close"]

    body1 = abs(c1 - o1)
    mid1 = (o1 + c1) / 2

    return (
        c1 > o1 and          # 第一根阳线
        c2 < o2 and          # 第二根阴线
        o2 > c1 and          # 高开在前一收盘之上
        c2 < mid1 and        # 收盘跌破前一实体中点
        c2 > o1              # （可选条件）未跌破前一开盘
    )


def is_shooting_star(last: pd.Series) -> bool:
    """射击之星：长上影、小实体、下影短，多数出现在高位"""
    o, h, l, c = last["open"], last["high"], last["low"], last["close"]

    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l

    if body == 0:
        body = 1e-8

    return (
        upper > body * 2 and   # 上影至少是实体2倍
        lower < body * 0.5 and # 下影明显较短
        c <= o                 # 阴线偏看跌
    )


def is_evening_star(k1: pd.Series, k2: pd.Series, k3: pd.Series) -> bool:
    """黄昏之星：长阳 → 小实体 → 长阴（简化版）"""
    o1, c1 = k1["open"], k1["close"]
    o2, c2 = k2["open"], k2["close"]
    o3, c3 = k3["open"], k3["close"]

    body1 = abs(c1 - o1)
    body2 = abs(c2 - o2)
    body3 = abs(c3 - o3)

    cond_body = (
        c1 > o1 and
        body1 > body2 * 2 and
        c3 < o3 and
        body3 > body2 * 2
    )

    # 第二根在第一根实体上半部分附近
    cond_star_pos = (
        min(o2, c2) > (o1 + c1) / 2
    )

    # 第三根收盘跌入第一根实体下半部分
    cond_third_close = (
        c3 < (o1 + c1) / 2
    )

    return cond_body and cond_star_pos and cond_third_close


def detect_bearish_patterns(df: pd.DataFrame):
    """检测最近K线是否出现看跌形态,返回形态列表"""
    patterns = []

    if len(df) < 3:
        return patterns

    last = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]

    if is_bearish_engulfing(prev, last):
        patterns.append("Bearish Engulfing")

    if is_dark_cloud_cover(prev, last):
        patterns.append("Dark Cloud Cove")

    if is_shooting_star(last):
        patterns.append("Shooting Star")

    if is_evening_star(prev2, prev, last):
        patterns.append("Evening Star")

    return patterns
