import logging
import json
import os
import io
import requests
import pandas as pd
import mplfinance as mpf
import google.generativeai as genai
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

# ================= ⚙️ 用户配置区域 (请修改这里) =================

# 1. Telegram 设置
BOT_TOKEN = '7953312922:AAH7ky-xXUhYt833f6xotlxYyNeZ9Sg_U5U'
ALLOWED_USER_IDS = [7643520392,8108089944]  # 允许使用机器人的用户 ID (数字)

# 2. Google Gemini 设置
GEMINI_API_KEY = "AIzaSyBXcc0iUTaMpoYVvFXco_TGhnEHKyH2Mi4"
GEMINI_MODEL = "gemini-3-pro-preview" # 使用 Flash 模型，速度快且免费额度多


# 3. 网络代理 (国内必须设置)
# export https_proxy=http://127.0.0.1:7890 (在终端运行脚本前设置)
PROXY_URL = None 

# 4. 自动监控策略参数
RSI_THRESHOLD = 70
SHADOW_RATIO = 2.0
DANGER_FUNDING_RATE = -0.05

# ===============================================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

DATA_FILE = 'watchlist.json'
BASE_URL = "https://fapi.binance.com"
watchlist = {}
user_risk_settings = {}
DEFAULT_BALANCE = 1000.0
DEFAULT_RISK_PCT = 2.0

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# === 🛠️ 基础工具函数 ===

def load_data():
    global watchlist
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f: watchlist = json.load(f)

def save_data():
    with open(DATA_FILE, 'w') as f: json.dump(watchlist, f)

def calculate_indicators(df):
    """计算 RSI 和 MACD"""
    # 1. RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # 2. MACD (12, 26, 9)
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd_dif'] = exp12 - exp26
    df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = (df['macd_dif'] - df['macd_dea']) * 2
    return df


def get_market_data(symbol, interval):
    """从币安获取K线和费率 (修复列名版)"""
    try:
        # 获取 K 线 (拿 100 根以保证指标计算准确)
        kline_url = f"{BASE_URL}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': interval, 'limit': 100}
        proxies = {'https': PROXY_URL} if PROXY_URL else None

        resp = requests.get(kline_url, params=params, proxies=proxies, timeout=10)
        data = resp.json()

        if not isinstance(data, list): return None, 0

        # === 修复核心在这里 ===
        # 我们把第6列的名称从 'v' 改成了 'volume'，这样 mplfinance 就能识别了
        df = pd.DataFrame(data, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume',
            'ct', 'qv', 'n', 'tb', 'tq', 'ig'
        ])

        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.set_index('time', inplace=True)

        # 数据类型转换也需要对应修改
        cols = ['open', 'high', 'low', 'close', 'volume']
        df[cols] = df[cols].astype(float)

        # 计算指标
        df = calculate_indicators(df)

        # 获取费率
        fund_url = f"{BASE_URL}/fapi/v1/premiumIndex"
        f_resp = requests.get(fund_url, params={'symbol': symbol}, proxies=proxies, timeout=10)
        funding_rate = float(f_resp.json().get('lastFundingRate', 0)) * 100

        return df, funding_rate
    except Exception as e:
        logging.error(f"Data error for {symbol}: {e}")
        return None, 0

def generate_chart_image(df, symbol, interval):
    """绘制 K线 + MACD + 成交量 (修复面板数量版)"""
    buf = io.BytesIO()
    
    # 截取最近 60 根用于绘图
    plot_df = df.tail(60)
    
    # MACD 柱子颜色 (涨红跌绿)
    macd_colors = ['green' if v >= 0 else 'red' for v in plot_df['macd_hist']]
    
    # 配置副图 (MACD) -> 放在 Panel 1
    apds = [
        mpf.make_addplot(plot_df['macd_dif'], panel=1, color='orange', width=1.0, ylabel='MACD'),
        mpf.make_addplot(plot_df['macd_dea'], panel=1, color='blue', width=1.0),
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
def analyze_with_gemini(image_buf, symbol, interval, last_row, funding_rate, prompt_override=None):

    """通用 AI 分析函数"""
    try:
        image_buf.seek(0)
        img = Image.open(image_buf)
        
        # 提取最新指标数据
        rsi = last_row['rsi']
        macd_dif = last_row['macd_dif']
        macd_hist = last_row['macd_hist']
        close_price = last_row['close']
        
        # 默认 Prompt (自动监控用)
        base_prompt = f"""
        Role: Crypto Expert Trader.
        Symbol: {symbol} ({interval}) | Price: {close_price}
        
        **Technical Indicators:**
        1. **RSI**: {rsi:.1f}
        2. **Funding Rate**: {funding_rate:.4f}%
        3. **MACD**: DIF={macd_dif:.4f}, Histogram={macd_hist:.4f} (Check for divergence or crossover)
        
        **Visual Task:** Analyze the chart image (Candles + MACD + Volume).
        Identify patterns (Head & Shoulders, Flags, Pinbars) and Trend status.
        
        **Output ONLY JSON:**
        {{
            "score": 0-10 (10 = Strong Short Signal),
            "reason": "Technical analysis summary.",
            "action": "WAIT" or "SHORT"
        }}
        """
        
        # 如果是手动调用 /ai，使用更详细的 Prompt
        if prompt_override:
            base_prompt = prompt_override.format(
                symbol=symbol, interval=interval, price=close_price,
                rsi=rsi, funding=funding_rate, dif=macd_dif, hist=macd_hist
            )

        response = model.generate_content([base_prompt, img])
        text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logging.error(f"AI Error: {e}")
        return {"score": 0, "reason": f"AI Error: {e}", "action": "WAIT"}

# === 🤖 机器人命令 ===

# 权限装饰器
def restricted(func):
    async def wrapped(update, context, *args, **kwargs):
        if update.effective_user.id not in ALLOWED_USER_IDS: return
        return await func(update, context, *args, **kwargs)
    return wrapped
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
        df, funding_rate = get_market_data(symbol, interval)
        if df is None:
            await status_msg.edit_text("❌ 获取数据失败，请检查币种拼写或网络。")
            return

        last_row = df.iloc[-1]
        
        # 3. 生成图表
        chart_buf = generate_chart_image(df, symbol, interval)
        
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
        
        # 5. 调用 AI
        result = analyze_with_gemini(chart_buf, symbol, interval, last_row, funding_rate, prompt_override=detailed_prompt)
        
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
        try:
            await status_msg.edit_text(f"❌ 分析出错: {str(e)[:100]}") # 截断错误信息防止太长
        except:
            # 如果消息发不出，就在后台打印日志，不让机器人崩掉
            pass
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'list':
        await list_coins(update, context)
    elif query.data == 'ai_help':
        await query.edit_message_text("🤖 **主动分析指令**:\n发送 `/ai BTC 1h`", parse_mode='Markdown')
    elif query.data == 'calc_help':
        await query.edit_message_text("🧮 **仓位计算指令**:\n发送 `/calc 65000 66000`", parse_mode='Markdown')
    elif query.data == 'set_help':
        await query.edit_message_text("⚙️ **设置参数**:\n发送 `/set 2000 3`", parse_mode='Markdown')
    elif query.data == 'scan':
        await query.message.reply_text("⏳ 手动扫描中...")
        await monitor_task(context)
    elif query.data == 'add_help':
        await query.edit_message_text("➕ **添加指令**:\n发送 `/add BTC 1h`", parse_mode='Markdown')
    elif query.data == 'risk_help':
        await query.edit_message_text(
            "🛡 **风控指令说明**:\n\n"
            "1️⃣ **设置参数**: `/set 2000 3`\n(本金2000U，单笔风险3%)\n\n"
            "2️⃣ **计算仓位**: `/calc 65000 66000`\n(开仓价 止损价)", 
            parse_mode='Markdown'
        )
    elif query.data == 'del_help':
        keyboard = [[InlineKeyboardButton(f"🗑 {s}", callback_data=f"del_{s}")] for s in watchlist]
        keyboard.append([InlineKeyboardButton("🔙 返回", callback_data="back")])
        await query.edit_message_text("👇 点击删除:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('del_'):
        sym = query.data.split('_')[1]
        if sym in watchlist: del watchlist[sym]
        save_data()
        await query.edit_message_text(f"✅ 已删除 {sym}")
    elif query.data == 'back':
        await start(update, context)

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

# === 🛡 风险管理模块 ===

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

# === 后台任务 (自动监控) ===
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

    # === 修复核心 ===
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

if __name__ == '__main__':
    load_data()
    # 注册原来的命令...
    # 请确保把 set_risk, calc_position, list_coins, add_coin 等都加上
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    if PROXY_URL:
        app = ApplicationBuilder().token(BOT_TOKEN).proxy_url(PROXY_URL).get_updates_proxy_url(PROXY_URL).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("back", start))
    app.add_handler(CommandHandler("add", add_coin))
    app.add_handler(CommandHandler("list", list_coins))
    app.add_handler(CommandHandler("set", set_risk))
    app.add_handler(CommandHandler("calc", calc_position))
    app.add_handler(CommandHandler("ai", manual_ai_analyze)) # <--- 新增这行
    app.add_handler(CallbackQueryHandler(button_handler))
    # ... 注册其他 Handler (add, list, set, calc) ...
    # ⚠️ 注意: 请把之前脚本里的 add_coin, list_coins, set_risk, calc_position 等函数都保留在文件里，并在这里注册
    
    app.job_queue.run_repeating(monitor_task, interval=60, first=5)
    
    print("🚀 机器人启动完毕")
    app.run_polling()
