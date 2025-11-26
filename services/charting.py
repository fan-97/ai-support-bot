import io
import mplfinance as mpf

def generate_chart_image(df, symbol, interval):
    """绘制 K线 + MACD + 成交量 (修复面板数量版)"""
    buf = io.BytesIO()
    # 截取最近 60 根用于绘图
    plot_df = df.tail(100)

    
    # MACD 柱子颜色 (涨红跌绿)
    macd_colors = ['green' if v >= 0 else 'red' for v in plot_df['macd_hist']]
    
    # 配置副图 (MACD) -> 放在 Panel 1
    apds = [
        mpf.make_addplot(plot_df['macd'], panel=1, color='orange', width=1.0, ylabel='MACD'),
        mpf.make_addplot(plot_df['macd_signal'], panel=1, color='blue', width=1.0),
        mpf.make_addplot(plot_df['macd_hist'], panel=1, type='bar', color=macd_colors, alpha=0.5),
    ]

    # 定义颜色和样式
    mc = mpf.make_marketcolors(up='green', down='red', edge='i', wick='i', volume='in', inherit=True)
    s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)
    
    # 绘图
    mpf.plot(
        plot_df, 
        type='candle', 
        mav=(7, 25), 
        addplot=apds, 
        volume=True, 
        volume_panel=2,          # <--- 【关键修复】将成交量指定到 Panel 2
        title=f"{symbol} - {interval}",
        style=s,
        panel_ratios=(6, 3, 2),  # 高度比例: 主图(0)=6, MACD(1)=3, 成交量(2)=2
        savefig=buf
    )
    buf.seek(0)
    return buf
