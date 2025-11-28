import io
import mplfinance as mpf


def generate_chart_image(df, symbol: str, interval: str):
    """Plot candle + MACD + volume to BytesIO."""
    buf = io.BytesIO()
    plot_df = df.tail(100)

    # Color MACD bars by sign for quick visual bias
    macd_colors = ['green' if v >= 0 else 'red' for v in plot_df['macd_hist']]

    apds = [
        mpf.make_addplot(plot_df['macd'], panel=1, color='orange', width=1.0, ylabel='MACD'),
        mpf.make_addplot(plot_df['macd_signal'], panel=1, color='blue', width=1.0),
        mpf.make_addplot(plot_df['macd_hist'], panel=1, type='bar', color=macd_colors, alpha=0.5),
    ]

    mc = mpf.make_marketcolors(up='green', down='red', edge='i', wick='i', volume='in', inherit=True)
    style = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc)

    mpf.plot(
        plot_df,
        type='candle',
        mav=(7, 25),
        addplot=apds,
        volume=True,
        volume_panel=2,
        title=f"{symbol} - {interval}",
        style=style,
        panel_ratios=(6, 3, 2),
        savefig=buf,
    )
    buf.seek(0)
    return buf
