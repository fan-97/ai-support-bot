
import asyncio
import logging
from telegram.ext import ContextTypes
from config.settings import ALLOWED_USER_IDS
from services.storage import get_all_unique_pairs, get_users_watching
from services.data_fetcher import get_binance_klines, get_current_funding_rate, get_open_interest
from services.charting import generate_chart_image
from services.ai_service import analyze_with_ai
from services.notification import NotificationService
from services.patterns import detect_bearish_patterns
from services.confirmations import volume_confirmation, rsi_confirmation, macd_confirmation
from services.indicators import calc_rsi, calc_macd, calc_ema, calc_bollinger_bands, calc_kdj

_monitor_paused = False


def is_monitor_paused() -> bool:
    return _monitor_paused


def set_monitor_paused(paused: bool) -> None:
    global _monitor_paused
    _monitor_paused = paused


def toggle_monitor_paused() -> bool:
    global _monitor_paused
    _monitor_paused = not _monitor_paused
    return _monitor_paused


async def monitor_task(context: ContextTypes.DEFAULT_TYPE):
    if is_monitor_paused():
        logging.info("Monitor task is paused; skipping this cycle.")
        return

    unique_pairs = get_all_unique_pairs()
    if not unique_pairs:
        return

    for sym, interval in unique_pairs:
        try:
            # logging.info(f"Fetching {sym} {interval} klines...")
            df = await get_binance_klines(sym, interval)
            funding = await get_current_funding_rate(sym)
            open_interest = await get_open_interest(sym, interval)
            if df is None:
                logging.warning(f"[{sym} {interval}] Data is empty or fetch failed")
                continue

            df["rsi"] = calc_rsi(df["close"])
            df["rsi7"] = calc_rsi(df["close"], period=7)
            df["ema20"] = calc_ema(df["close"], span=20)
            df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])
            
            df["bb_upper"], df["bb_mid"], df["bb_lower"] = calc_bollinger_bands(df["close"])
            df["k"], df["d"], df["j"] = calc_kdj(df["high"], df["low"], df["close"])

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
            need_ai = True
            if need_ai:
                try:
                    # chart = await asyncio.to_thread(generate_chart_image, df, sym, interval) # Image no longer needed
                    result = await analyze_with_ai(sym, interval, df, funding, open_interest, patterns=patterns)
                    if result.get('decision') == 'hold':
                        logging.info(f"[{sym} {interval}] AI decision is hold, skipping notification")
                        continue
                    # 6. Format and Send Report
                    market_data = {
                        'close': last_row['close'],
                        'rsi': df['rsi'].iloc[-1],
                        'funding_rate': funding,
                        'open_interest': open_interest
                    }
                    
                    caption, full_report = NotificationService.format_report(sym, interval, result, market_data)

                    interested_users = get_users_watching(sym, interval)
                    for uid in interested_users:
                        # Double check if user is allowed (optional, but good practice if storage gets messy)
                        if uid in ALLOWED_USER_IDS or str(uid) in [str(x) for x in ALLOWED_USER_IDS]:
                            await NotificationService.send_telegram_report(context.bot, uid, None, caption, full_report)
                except Exception as e:
                    logging.exception(f"[{sym} {interval}] AI Analysis/Notification failed: {e}")

        except Exception as e:
            logging.exception(f"[{sym} {interval}] Monitor loop error: {e}")
