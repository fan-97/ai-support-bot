from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.storage import watchlist, save_data
from handlers.commands import list_coins, start
from tasks.monitor import monitor_task

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
