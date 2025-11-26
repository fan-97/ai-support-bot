import logging
from telegram.ext import ContextTypes
from config.settings import ALLOWED_USER_IDS, RSI_THRESHOLD, SHADOW_RATIO
from services.storage import watchlist
from services.data_fetcher import get_binance_klines,get_current_funding_rate
from services.charting import generate_chart_image
from services.ai_service import analyze_with_gemini
from services.patterns import detect_bearish_patterns
from services.confirmations import volume_confirmation, rsi_confirmation, macd_confirmation
from services.indicators import calc_rsi, calc_macd

async def monitor_task(context: ContextTypes.DEFAULT_TYPE):
    if not watchlist: return
    for sym, interval in watchlist.items():
        try:
            logging.info(f"拉取 {sym} {interval} K线数据...")
            df = get_binance_klines(sym, interval)
            funding = get_current_funding_rate(sym)
            if df is None: continue
          # 计算指标
            df["rsi"] = calc_rsi(df["close"])
            df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])

            # 检测K线形态
            patterns = detect_bearish_patterns(df)

            # 辅助确认
            vol_ok = volume_confirmation(df)
            rsi_ok = rsi_confirmation(df)
            macd_ok = macd_confirmation(df)

            last_row = df.iloc[-1]
            ts = last_row["close_time"]
            close_price = last_row["close"]

            notify_message = f"""
            ====================================
            最新K线收盘时间:{ts}  收盘价：{close_price}
            检测到的看跌K线形态:{patterns if patterns else "无明显形态"}
            成交量放大确认：{vol_ok}
            RSI 超买回落确认：{rsi_ok}(最新RSI={df['rsi'].iloc[-1]:.2f})
            MACD 看跌确认：{macd_ok}(MACD={df['macd'].iloc[-1]:.4f}, Signal={df['macd_signal'].iloc[-1]:.4f})
            """
            logging.info(notify_message)

            
            need_ai = False
            if patterns and vol_ok and rsi_ok and macd_ok:
                logging.info("✅ 高概率看跌信号（形态 + 成交量 + RSI + MACD 全部满足）")
                need_ai = True
            elif patterns and (vol_ok or rsi_ok or macd_ok):
                logging.info("⚠ 存在一定看跌概率：有形态 + 至少一个指标确认，需要结合大级别趋势慎重判断。")
                need_ai = True
            elif patterns:
                logging.info("❗ 仅出现形态但指标未确认，可能是假信号，谨慎对待。")
            else:
                logging.info("暂无明显强烈看跌信号。")
            
            if need_ai:
                chart = generate_chart_image(df, sym, interval)
                # 使用默认 Prompt 进行简短分析
                ai = analyze_with_gemini(chart, sym, interval, df, funding)
                
                chart.seek(0)
                caption = f"🚨 **自动监控信号**\n{sym} {interval}\n建议: {ai.get('action')}\n理由: {ai.get('reason')}"
                for uid in ALLOWED_USER_IDS:
                    await context.bot.send_photo(uid, photo=chart, caption=caption)
                    
        except Exception as e:
            logging.error(f"Monitor error: {e}")