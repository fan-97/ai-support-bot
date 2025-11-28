from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.storage import get_user_watchlist, remove_from_watchlist
from handlers.commands import list_coins, start
from tasks.monitor import monitor_task


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'list':
        await list_coins(update, context)
    elif query.data == 'ai_help':
        await query.edit_message_text("🤖 AI analyze:\nUse `/ai BTC 1h`", parse_mode='Markdown')
    elif query.data == 'calc_help':
        await query.edit_message_text("🧮 Position calc:\nUse `/calc 65000 66000`", parse_mode='Markdown')
    elif query.data == 'set_help':
        await query.edit_message_text("⚙️ Set params:\nUse `/set 2000 3`", parse_mode='Markdown')
    elif query.data == 'scan':
        await query.message.reply_text("⏳ Scanning...")
        await monitor_task(context)
    elif query.data == 'add_help':
        await query.edit_message_text("➕ Add:\nUse `/add BTC 1h`", parse_mode='Markdown')
    elif query.data == 'risk_help':
        await query.edit_message_text(
            "🛡 Risk help:\n\n"
            "1) Set params: `/set 2000 3` (balance 2000U, risk 3%)\n\n"
            "2) Calc position: `/calc 65000 66000` (entry, stop)",
            parse_mode='Markdown'
        )
    elif query.data == 'del_help':
        user_watchlist = get_user_watchlist(update.effective_user.id)
        keyboard = [[InlineKeyboardButton(f"🗑 {s}", callback_data=f"del_{s}")] for s in user_watchlist]
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
        await query.edit_message_text("Delete symbol:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('del_'):
        sym = query.data.split('_')[1]
        remove_from_watchlist(update.effective_user.id, sym)
        await query.edit_message_text(f"Deleted {sym}")
    elif query.data == 'back':
        await start(update, context)
