import logging
from telegram.ext import ContextTypes
from config.settings import ALLOWED_USER_IDS, RSI_THRESHOLD, SHADOW_RATIO
from services.storage import watchlist
from services.market_data import get_market_data
from services.charting import generate_chart_image
from services.ai_service import analyze_with_gemini

async def monitor_task(context: ContextTypes.DEFAULT_TYPE):
    if not watchlist: return
    for sym, interval in watchlist.items():
        try:
            df, funding = get_market_data(sym, interval)
            if df is None: continue
            
            # 简单的硬过滤 (RSI + 插针)
            # 注意: 这里需要手动提取 last_row 传给 analyze_with_gemini
            tech_data = df.iloc[-2] # 倒数第二根(收盘)
            
            # 这里的过滤逻辑:
            body = abs(tech_data['close'] - tech_data['open'])
            upper_shadow = tech_data['high'] - max(tech_data['close'], tech_data['open'])
            is_shooting_star = upper_shadow > (body * SHADOW_RATIO) if body > 0 else False
            is_overbought = tech_data['rsi'] > RSI_THRESHOLD
            
            if is_shooting_star and is_overbought:
                chart = generate_chart_image(df, sym, interval)
                # 使用默认 Prompt 进行简短分析
                ai = analyze_with_gemini(chart, sym, interval, tech_data, funding)
                
                chart.seek(0)
                caption = f"🚨 **自动监控信号**\n{sym} {interval}\n建议: {ai.get('action')}\n理由: {ai.get('reason')}"
                for uid in ALLOWED_USER_IDS:
                    await context.bot.send_photo(uid, photo=chart, caption=caption)
                    
        except Exception as e:
            logging.error(f"Monitor error: {e}")
