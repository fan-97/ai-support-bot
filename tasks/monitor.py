import asyncio
import logging
from telegram.ext import ContextTypes
from config.settings import ALLOWED_USER_IDS
from services.storage import watchlist
from services.data_fetcher import get_binance_klines, get_current_funding_rate
from services.charting import generate_chart_image
from services.ai_service import analyze_with_ai
from services.patterns import detect_bearish_patterns
from services.confirmations import volume_confirmation, rsi_confirmation, macd_confirmation
from services.indicators import calc_rsi, calc_macd


async def monitor_task(context: ContextTypes.DEFAULT_TYPE):
    if not watchlist:
        return

    for sym, interval in watchlist.items():
        try:
            logging.info(f"Fetching {sym} {interval} klines...")
            df = await get_binance_klines(sym, interval)
            funding = await get_current_funding_rate(sym)
            if df is None:
                logging.warning(f"{sym} {interval} data is empty")
                continue

            df["rsi"] = calc_rsi(df["close"])
            df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])

            patterns = detect_bearish_patterns(df)
            vol_ok = volume_confirmation(df)
            rsi_ok = rsi_confirmation(df)
            macd_ok = macd_confirmation(df)

            last_row = df.iloc[-1]
            ts = last_row["close_time"]
            close_price = last_row["close"]

            notify_message = [
                "====================================",
                f"Close time: {ts}  Close: {close_price}",
                f"Bearish patterns: {patterns if patterns else 'None'}",
                f"Volume confirm: {vol_ok}",
                f"RSI confirm: {rsi_ok} (RSI={df['rsi'].iloc[-1]:.2f})",
                f"MACD confirm: {macd_ok} (MACD={df['macd'].iloc[-1]:.4f}, Signal={df['macd_signal'].iloc[-1]:.4f})",
            ]

            need_ai = False
            if patterns and vol_ok and rsi_ok and macd_ok:
                notify_message.append("High-probability bearish: pattern + vol + RSI + MACD all align")
                need_ai = True
            elif patterns and (vol_ok or rsi_ok or macd_ok):
                notify_message.append("Bearish possibility: pattern + at least one indicator confirm")
                need_ai = True
            elif patterns:
                notify_message.append("Pattern only; indicators disagree")
            else:
                notify_message.append("No strong bearish signal")

            logging.info("\n".join(notify_message))

            if need_ai:
                chart = await asyncio.to_thread(generate_chart_image, df, sym, interval)
                ai = await analyze_with_ai(chart, sym, interval, df, funding, patterns=patterns)

                chart.seek(0)
                caption = (
                    f"🚨 Auto signal\n{sym} {interval}\n"
                    f"Pattern: {patterns}\n"
                    f"Action: {ai.get('action')}\n"
                    f"Reason: {ai.get('reason')}"
                )
                for uid in ALLOWED_USER_IDS:
                    await context.bot.send_photo(uid, photo=chart, caption=caption)

        except Exception as e:
            logging.error(f"Monitor error: {e}")
