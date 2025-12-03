import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import DEFAULT_BALANCE, DEFAULT_RISK_PCT
from services.storage import add_to_watchlist, get_user_watchlist, user_risk_settings
from services.data_fetcher import get_binance_klines, get_current_funding_rate, get_open_interest
from services.charting import generate_chart_image
from services.ai_service import analyze_with_ai
from services.notification import NotificationService
from utils.decorators import restricted
from services.indicators import calc_rsi, calc_macd, calc_ema, calc_bollinger_bands, calc_kdj
from services.patterns import detect_bearish_patterns



@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    text = (
        "🤖 **AI Crypto Analyst Bot Help**\n\n"
        "**Core Commands**:\n"
        "• `/start` - Open main menu\n"
        "• `/add <SYMBOL> <INTERVAL>` - Track a coin (e.g., `/add BTC 1h`)\n"
        "• `/list` - View your watchlist\n"
        "• `/ai <SYMBOL> <INTERVAL>` - Manual AI analysis\n"
        "• `/models` - Browse AI models\n"
        "• `/set <BALANCE> <RISK>` - Set risk params\n"
        "• `/calc <ENTRY> <SL>` - Calculate position size\n\n"
        "**Features**:\n"
        "• **Auto-Monitor**: I scan your watchlist every minute for bearish patterns.\n"
        "• **AI Analysis**: I use advanced AI to analyze charts and give trading plans.\n"
        "• **Risk Management**: I help you calculate position sizes based on your risk tolerance."
    )
    keyboard = [[InlineKeyboardButton("❌ Close", callback_data="close")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu for commands and buttons."""
    keyboard = [
        [InlineKeyboardButton("📜 Watchlist", callback_data='list'), InlineKeyboardButton("🔄 Scan now", callback_data='scan')],
        [InlineKeyboardButton("➕ Add symbol", callback_data='add_help'), InlineKeyboardButton("➖ Delete symbol", callback_data='del_help')],
        [InlineKeyboardButton("🤖 AI Analyze", callback_data='ai_help'), InlineKeyboardButton("🧠 AI Models", callback_data='models_menu')],
        [InlineKeyboardButton("🛡 Risk Help", callback_data='risk_help'), InlineKeyboardButton("⚙️ Settings", callback_data='set_help')],
        [InlineKeyboardButton("🧮 Position Calc", callback_data='calc_help')],
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ]

    text = (
        "🤖 **AI Crypto Analyst**\n"
        "------------------------------\n"
        "Welcome! I can help you monitor markets, analyze trends with AI, and manage risk.\n\n"
        "**Quick Actions:**"
    )
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif update.message:
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
            await update.message.reply_text("Usage: `/add BTC 1h`", parse_mode='Markdown')
            return
        symbol = args[0].upper()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        interval = args[1].lower()
        valid_intervals = ['15m', '1h', '4h', '1d']
        if interval not in valid_intervals:
             await update.message.reply_text(f"Invalid interval. Use: {', '.join(valid_intervals)}")
             return

        add_to_watchlist(update.effective_user.id, symbol, interval)
        await update.message.reply_text(f"Added: **{symbol}** ({interval})", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Add coin error: {e}")
        await update.message.reply_text("Error, try again")


@restricted
async def list_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_watchlist = get_user_watchlist(update.effective_user.id)
    msg = "📋 **Watchlist**:\n" + "\n".join([f"`{k:<10} | {v}`" for k, v in user_watchlist.items()]) if user_watchlist else "Empty list"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back"), InlineKeyboardButton("❌ Close", callback_data="close")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')


@restricted
async def set_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        balance = float(context.args[0])
        risk = float(context.args[1])
        user_risk_settings[update.effective_user.id] = {'balance': balance, 'risk': risk}
        await update.message.reply_text(f"Risk updated. Balance `{balance}U`, Risk `{risk}%`", parse_mode='Markdown')
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: `/set 1000 2` (Balance Risk%)")
    except Exception as e:
        logging.error(f"Set risk error: {e}")
        await update.message.reply_text("Error setting risk parameters.")


@restricted
async def calc_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        entry = float(context.args[0])
        sl = float(context.args[1])
        settings = user_risk_settings.get(update.effective_user.id, {'balance': DEFAULT_BALANCE, 'risk': DEFAULT_RISK_PCT})

        diff_pct = abs(entry - sl) / entry
        if diff_pct == 0:
            return

        loss_amt = settings['balance'] * (settings['risk'] / 100)
        pos_size = loss_amt / diff_pct
        lev = (1 / diff_pct) * 0.5
        if lev < 1:
            lev = 1

        await update.message.reply_text(
            f"🧮 **Position calc** ({'Short' if entry > sl else 'Long'})\n"
            f"💰 Risk amt: `-{loss_amt:.1f} U`\n"
            f"📉 SL move: `{diff_pct*100:.2f}%`\n"
            f"------------------\n"
            f"💎 **Size: {pos_size:.0f} U**\n"
            f"⚙️ Lev: `< {lev:.1f}x`",
            parse_mode='Markdown'
        )
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: `/calc entry stop` (e.g. `/calc 3000 3100`)")
    except Exception as e:
        logging.error(f"Calc position error: {e}")
        await update.message.reply_text("Error calculating position.")


@restricted
async def manual_ai_analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command: /ai SYMBOL INTERVAL [MODEL]"""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Format: `/ai SYMBOL INTERVAL [MODEL]` e.g. `/ai ETH 4h` or `/ai ETH 4h google/gemini-flash-1.5`", parse_mode='Markdown')
        return

    symbol = args[0].upper()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    interval = args[1].lower()

    model = args[2] if len(args) > 2 else None

    status_msg = await update.message.reply_text(f"Working on {symbol} {interval} ...")

    try:
        df = await get_binance_klines(symbol, interval)
        funding_rate = await get_current_funding_rate(symbol)
        open_interest = await get_open_interest(symbol, interval)
        if df is None:
            await status_msg.edit_text("Data fetch failed (symbol/network)")
            return

        df["rsi"] = calc_rsi(df["close"])
        df["rsi7"] = calc_rsi(df["close"], period=7)
        df["ema20"] = calc_ema(df["close"], span=20)
        df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])
        
        df["bb_upper"], df["bb_mid"], df["bb_lower"] = calc_bollinger_bands(df["close"])
        df["k"], df["d"], df["j"] = calc_kdj(df["high"], df["low"], df["close"])

        # chart_buf = await asyncio.to_thread(generate_chart_image, df, symbol, interval)

        last_row = df.iloc[-1]
        patterns = detect_bearish_patterns(df)

        result = await analyze_with_ai(symbol, interval, df, funding_rate, open_interest, patterns, model=model)

         
        # 6. Format and Send Report
        market_data = {
            'close': last_row['close'],
            'rsi': last_row['rsi'],
            'funding_rate': funding_rate,
            'open_interest': open_interest
        }
        
        caption, full_report = NotificationService.format_report(symbol, interval, result, market_data)
        
        await NotificationService.reply_telegram_report(update, None, caption, full_report)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)

    except Exception as e:
        logging.exception(f"Manual AI Error: {e}")
        try:
            await status_msg.edit_text(f"Error: {str(e)[:100]}")
        except Exception:
            pass
