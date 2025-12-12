
import logging
from telegram.ext import ContextTypes
from config.settings import ALLOWED_USER_IDS
from services.storage import get_all_unique_pairs, get_users_watching
from services.data_fetcher import prepare_market_data_for_ai
from services.ai_service import analyze_with_ai
from services.notification import NotificationService
from services.patterns import CandlePatternDetector
from services.confirmations import volume_confirmation, rsi_confirmation, macd_confirmation
from services.model import ReversalModel
from services.data_fetcher import DataFetcher

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

async def reversal_monitor(sym, interval):
     # 获取指标
    dfr = DataFetcher()
    df = await dfr.get_merged_data(sym, interval)
    model = ReversalModel(df)
    if df is None:
        raise RuntimeError("Data fetch failed (symbol/network)")
    try:
        result = model.evaluate(index=-1)
        caption = (
            f"当前价格: {result['price']:.2f}\n"
            f"RSI数值: {result['rsi']:.2f}\n"
            f"当前趋势: {result['trend']}\n"
            f"信号方向: {'做多反转 (Bullish)' if result['signal_type'] == 'long_reversal' else '做空反转 (Bearish)'}\n"
            f"综合评分: {result['total_score']} / 100\n"
            f"{'-' * 30}\n"
            "得分详情:\n"
        )
        for k, v in result['details'].items():
            caption += f"  - {k}: +{v}\n"
        caption += f"{'-' * 30}\n"
        
        score = result['total_score']
        if score < 30:
            caption += "建议: 观望 (风险低但机会也低)"
        elif score < 60:
            caption += "建议: 观察区 (等待更多信号)"
        elif score < 80:
            caption += "建议: 重点关注 (轻仓尝试 + 紧止损)"
        else:
            caption += "建议: ⚠️ 极端反转区 (高胜率，由于波动大需挂单进场)"
        #full_report = caption  # Assuming full_report is just the caption for now based on usage below
        return caption, None
    except Exception as e:
        logging.exception(f"[{sym} {interval}] Reversal monitor error: {e}")
def monitor_ai_analysis():
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
        return caption, full_report
    except Exception as e:
        logging.exception(f"[{sym} {interval}] AI Analysis/Notification failed: {e}")
async def monitor_task(context: ContextTypes.DEFAULT_TYPE):
    if is_monitor_paused():
        logging.info("Monitor task is paused; skipping this cycle.")
        return None,None

    unique_pairs = get_all_unique_pairs()
    if not unique_pairs:
        return

    for sym, interval in unique_pairs:
        try:
            caption, full_report = await reversal_monitor(sym, interval)
            # monitor_ai_analysis(sym, interval)
            interested_users = get_users_watching(sym, interval)
            for uid in interested_users:
                # Double check if user is allowed (optional, but good practice if storage gets messy)
                if uid in ALLOWED_USER_IDS or str(uid) in [str(x) for x in ALLOWED_USER_IDS]:
                    await NotificationService.send_telegram_report(context.bot, uid, None, caption, full_report)
        except Exception as e:
            logging.exception(f"[{sym} {interval}] Monitor loop error: {e}")
