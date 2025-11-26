import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import DEFAULT_BALANCE, DEFAULT_RISK_PCT
from services.storage import watchlist, save_data, user_risk_settings
from services.data_fetcher import get_binance_klines, get_current_funding_rate
from services.charting import generate_chart_image
from services.ai_service import analyze_with_gemini
from utils.decorators import restricted
from services.indicators import calc_rsi, calc_macd
from services.patterns import detect_bearish_patterns

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    主菜单函数 (修复版：同时支持命令和按钮回调)
    """
    keyboard = [
        [InlineKeyboardButton("📜 查看监控", callback_data='list'), InlineKeyboardButton("🔄 立即扫描", callback_data='scan')],
        [InlineKeyboardButton("➕ 添加币种", callback_data='add_help'), InlineKeyboardButton("➖ 删除币种", callback_data='del_help')],
        [InlineKeyboardButton("❓ 风控计算帮助", callback_data='risk_help'),InlineKeyboardButton("🤖 主动分析", callback_data='ai_help')],
        [InlineKeyboardButton("⚙️ 设置参数", callback_data='set_help'),InlineKeyboardButton("🧮 仓位计算", callback_data='calc_help')]
    ]
    
    text = (
        "🤖 **AI 智能做空助手 (Gemini版)**\n"
        "------------------------------\n"
        "请选择操作:"
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        # 情况 A: 如果是点击 "返回" 按钮调用的 -> 编辑当前消息
        await update.callback_query.edit_message_text(
            text=text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    elif update.message:
        # 情况 B: 如果是用户发送 /start 调用的 -> 发送新消息
        await update.message.reply_text(
            text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

@restricted
async def add_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("❌ 用法: `/add BTC 1h`", parse_mode='Markdown')
            return
        symbol = args[0].upper()
        if not symbol.endswith('USDT'): symbol += 'USDT'
        watchlist[symbol] = args[1].lower()
        save_data()
        await update.message.reply_text(f"✅ 添加监控: **{symbol}** ({args[1]})", parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ 错误")

@restricted
async def list_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📋 **监控列表**:\n" + "\n".join([f"`{k:<10} | {v}`" for k, v in watchlist.items()]) if watchlist else "📭 列表为空"
    if update.callback_query: await update.callback_query.edit_message_text(msg, parse_mode='Markdown')
    else: await update.message.reply_text(msg, parse_mode='Markdown')

@restricted
async def set_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = float(context.args[0])
        risk = float(context.args[1])
        user_risk_settings[update.effective_user.id] = {'balance': balance, 'risk': risk}
        await update.message.reply_text(f"✅ 风控已更新: 本金 `{balance}U`, 风险 `{risk}%`", parse_mode='Markdown')
    except:
        await update.message.reply_text("❌ 用法: `/set 1000 2`")

@restricted
async def calc_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        entry = float(context.args[0])
        sl = float(context.args[1])
        settings = user_risk_settings.get(update.effective_user.id, {'balance': DEFAULT_BALANCE, 'risk': DEFAULT_RISK_PCT})
        
        diff_pct = abs(entry - sl) / entry
        if diff_pct == 0: return
        
        loss_amt = settings['balance'] * (settings['risk'] / 100)
        pos_size = loss_amt / diff_pct
        lev = (1 / diff_pct) * 0.5
        if lev < 1: lev = 1
        
        await update.message.reply_text(
            f"🧮 **仓位计算** ({'Short' if entry > sl else 'Long'})\n"
            f"💰 风险金额: `-{loss_amt:.1f} U`\n"
            f"📉 止损幅度: `{diff_pct*100:.2f}%`\n"
            f"------------------\n"
            f"💎 **建议仓位: {pos_size:.0f} U**\n"
            f"⚙️ 建议杠杆: `< {lev:.1f}x`",
            parse_mode='Markdown'
        )
    except:
        await update.message.reply_text("❌ 用法: `/calc 开仓价 止损价`")

@restricted
async def manual_ai_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    指令: /ai 币种 周期 (修复版：图文分离 + 异常处理)
    """
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ 格式错误。\n用法: `/ai 币种 周期`\n例如: `/ai ETH 4h`", parse_mode='Markdown')
        return

    symbol = args[0].upper()
    if not symbol.endswith('USDT'): symbol += 'USDT'
    interval = args[1].lower()

    # 1. 发送等待提示 (记录这个消息对象，后续要用)
    status_msg = await update.message.reply_text(f"🧠 正在请求 AI 分析 **{symbol}** ({interval})...\n(这可能需要几秒钟)")

    try:
        # 2. 获取数据 & 计算
        df = get_binance_klines(symbol, interval)
        funding_rate = get_current_funding_rate(symbol)
        if df is None:
            await status_msg.edit_text("❌ 获取数据失败，请检查币种拼写或网络。")
            return
        # 计算指标
        df["rsi"] = calc_rsi(df["close"])
        df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])
        
        # 3. 生成图表
        chart_buf = generate_chart_image(df, symbol, interval)

        last_row = df.iloc[-1]
        ts = last_row["close_time"]
        close_price = last_row["close"]
        # 4. 构建深度分析 Prompt
        detailed_prompt = """
        You are a Top-Tier Crypto Analyst. Analyze {symbol} on {interval} timeframe.
        Current Price: {price}
        
        **Data Panel:**
        - **RSI(14)**: {rsi:.1f}
        - **MACD**: DIF={dif:.5f}, Histogram={hist:.5f}
        - **Funding Rate**: {funding:.4f}%
        
        **Chart Analysis Task:**
        Look at the provided image (Candlesticks + MACD Subplot + Volume).
        1. **Trend & Pattern**: Identify the current structure.
        2. **Momentum**: Is momentum fading? Any divergences?
        
        **Output Format (JSON):**
        {{
            "trend": "Bullish/Bearish/Neutral",
            "pattern": "Key Pattern",
            "key_levels": "Resistance/Support",
            "score": 0-10,
            "reason": "Detailed reasoning (Keep it under 300 words).",
            "action": "LONG / SHORT / WAIT"
        }}
        """
        patterns = detect_bearish_patterns(df)
        # 5. 调用 AI
        result = analyze_with_gemini(chart_buf, symbol, interval, df, funding_rate, patterns)
        
        # 6. 解析结果
        trend = result.get('trend', 'N/A')
        pattern = result.get('pattern', 'N/A')
        levels = result.get('key_levels', 'N/A')
        reason = result.get('reason', 'N/A')
        action = result.get('action', 'WAIT')
        score = result.get('score', 0)
        
        # === 核心修复：图文分离 ===
        
        # A. 简短的图片说明 (防止超过1024字符)
        emoji = "🔥" if score >= 8 else "😐"
        short_caption = (
            f"🤖 **AI 分析摘要** | {symbol} {interval}\n"
            f"🎯 **建议**: {action} {emoji}\n"
            f"🧠 **信心**: {score}/10\n"
            f"📉 **趋势**: {trend}\n"
            f"⬇️ _查看下方完整研报_"
        )
        
        # B. 完整的文字研报 (支持长文本)
        full_report = (
            f"📄 **{symbol} 深度研报**\n"
            f"-------------------------------\n"
            f"👀 **形态**: {pattern}\n"
            f"🧱 **关键位**: {levels}\n"
            f"-------------------------------\n"
            f"📊 **数据指标**:\n"
            f"• RSI: `{last_row['rsi']:.1f}`\n"
            f"• MACD柱: `{last_row['macd_hist']:.5f}`\n"
            f"• 费率: `{funding_rate:.4f}%`\n"
            f"-------------------------------\n"
            f"💡 **AI 逻辑分析**:\n{reason}\n"
        )

        chart_buf.seek(0)
        
        # 7. 先发图片
        await update.message.reply_photo(photo=chart_buf, caption=short_caption, parse_mode='Markdown')
        
        # 8. 后发长文本
        await update.message.reply_text(full_report, parse_mode='Markdown')
        
        # 9. 一切成功后，再删除"正在分析"的提示
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)

    except Exception as e:
        # 如果中间出错了，status_msg 还在，可以用来报错
        logging.error(f"Manual AI Error: {e}")
        traceback.print_exc()   
        try:
            await status_msg.edit_text(f"❌ 分析出错: {str(e)[:100]}") # 截断错误信息防止太长
        except:
            # 如果消息发不出，就在后台打印日志，不让机器人崩掉
            pass
