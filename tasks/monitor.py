
import logging
from telegram.ext import ContextTypes
from config.settings import ALLOWED_USER_IDS
from services.storage import get_all_unique_pairs, get_users_watching
from services.data_fetcher import prepare_market_data_for_ai
from services.ai_service import analyze_with_ai
from services.notification import NotificationService
from services.patterns import CandlePatternDetector

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
            # 获取指标
            df, df_btc = await prepare_market_data_for_ai(sym, interval)

            if df is None:
                raise RuntimeError("Data fetch failed (symbol/network)")
            detector  = CandlePatternDetector(df)
            match,pattern = detector.detect_patterns()
            if not match:
                logging.info(f"[{sym} {interval}] Bearish pattern detected, skipping notification")
                continue
            try:
                result = await analyze_with_ai(sym, interval, df,df_btc, balance=1000)
                if result.get('decision') == 'HOLD':
                    logging.info(f"[{sym} {interval}] AI decision is hold, skipping notification")
                    continue
                caption, full_report = NotificationService.format_report(sym, interval, result)

                interested_users = get_users_watching(sym, interval)
                for uid in interested_users:
                    # Double check if user is allowed (optional, but good practice if storage gets messy)
                    if uid in ALLOWED_USER_IDS or str(uid) in [str(x) for x in ALLOWED_USER_IDS]:
                        await NotificationService.send_telegram_report(context.bot, uid, None, caption, full_report)
            except Exception as e:
                logging.exception(f"[{sym} {interval}] AI Analysis/Notification failed: {e}")

        except Exception as e:
            logging.exception(f"[{sym} {interval}] Monitor loop error: {e}")
