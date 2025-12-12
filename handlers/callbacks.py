from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.storage import get_user_watchlist, remove_from_watchlist, clear_user_watchlist
from handlers.commands import list_coins, start
from handlers.model_handlers import models_command
from tasks.monitor import monitor_task, toggle_monitor_paused, is_monitor_paused


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'close':
        await query.message.delete()
        return

    if query.data == 'list':
        await list_coins(update, context)
    elif query.data == 'models_menu':
        await models_command(update, context)
    elif query.data == 'ai_help':
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]]
        await query.edit_message_text("🤖 AI analyze:\nUse `/ai BTC 1h`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == 'calc_help':
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]]
        await query.edit_message_text("🧮 Position calc:\nUse `/calc 65000 66000`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == 'set_help':
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]]
        await query.edit_message_text("⚙️ Set params:\nUse `/set 2000 3`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == 'scan':
        if is_monitor_paused():
            await query.message.reply_text("⏸ 自动监控已暂停，请先恢复后再扫描。")
        else:
            await query.message.reply_text("⏳ Scanning...")
            await monitor_task(context)
    elif query.data == 'add_help':
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]]
        await query.edit_message_text("➕ Add:\nUse `/add BTC 1h`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif query.data == 'risk_help':
        await query.edit_message_text(
            "🛡 Risk help:\n\n"
            "1) Set params: `/set 2000 3` (balance 2000U, risk 3%)\n\n"
            "2) Calc position: `/calc 65000 66000` (entry, stop)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]]),
            parse_mode='Markdown'
        )
    elif query.data == 'del_help':
        user_watchlist = get_user_watchlist(update.effective_user.id)
        keyboard = [[InlineKeyboardButton(f"🗑 {s}", callback_data=f"del_{s}")] for s in user_watchlist]
        if user_watchlist:
             keyboard.append([InlineKeyboardButton("🗑🗑 Delete All", callback_data="del_all")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")])
        await query.edit_message_text("Delete symbol:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith('del_'):
        sym = query.data.split('_')[1]
        remove_from_watchlist(update.effective_user.id, sym)
        
        user_watchlist = get_user_watchlist(update.effective_user.id)
        if not user_watchlist:
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]]
            await query.edit_message_text(f"Deleted {sym}. List is now empty.", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            keyboard = [[InlineKeyboardButton(f"🗑 {s}", callback_data=f"del_{s}")] for s in user_watchlist]
            keyboard.append([InlineKeyboardButton("🗑🗑 Delete All", callback_data="del_all")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")])
            await query.edit_message_text(f"Deleted {sym}.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'del_all':
        clear_user_watchlist(update.effective_user.id)
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]]
        await query.edit_message_text("All symbols deleted.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'toggle_monitor':
        paused = toggle_monitor_paused()
        status_text = "⏸ 自动监控已暂停" if paused else "✅ 自动监控已恢复"
        await query.message.reply_text(status_text)
        await start(update, context)
    elif query.data == 'back':
        await start(update, context)
