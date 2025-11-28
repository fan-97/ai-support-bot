import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import DEFAULT_BALANCE, DEFAULT_RISK_PCT
from services.storage import add_to_watchlist, get_user_watchlist, user_risk_settings
from services.data_fetcher import get_binance_klines, get_current_funding_rate
from services.charting import generate_chart_image
from services.ai_service import analyze_with_ai
from utils.decorators import restricted
from services.indicators import calc_rsi, calc_macd
from services.patterns import detect_bearish_patterns


@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu for commands and buttons."""
    keyboard = [
        [InlineKeyboardButton("📜 Watchlist", callback_data='list'), InlineKeyboardButton("🔄 Scan now", callback_data='scan')],
        [InlineKeyboardButton("➕ Add symbol", callback_data='add_help'), InlineKeyboardButton("➖ Delete symbol", callback_data='del_help')],
        [InlineKeyboardButton("🛡 Risk help", callback_data='risk_help'), InlineKeyboardButton("🤖 AI analyze", callback_data='ai_help')],
        [InlineKeyboardButton("⚙️ Set params", callback_data='set_help'), InlineKeyboardButton("🧮 Position calc", callback_data='calc_help')]
    ]

    text = (
        "🤖 **AI Short Assistant**\n"
        f"Provider: OpenRouter\n"
        "------------------------------\n"
        "Choose an action:"
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
    if update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, parse_mode='Markdown')


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
        if df is None:
            await status_msg.edit_text("Data fetch failed (symbol/network)")
            return

        df["rsi"] = calc_rsi(df["close"])
        df["macd"], df["macd_signal"], df["macd_hist"] = calc_macd(df["close"])

        chart_buf = await asyncio.to_thread(generate_chart_image, df, symbol, interval)

        last_row = df.iloc[-1]
        patterns = detect_bearish_patterns(df)

        result = await analyze_with_ai(chart_buf, symbol, interval, df, funding_rate, patterns, model=model)

        trend = result.get('trend', 'N/A')
        pattern = result.get('pattern', 'N/A')
        levels = result.get('key_levels', 'N/A')
        reason = result.get('reason', 'N/A')
        action = result.get('action', 'WAIT')
        score = result.get('score', 0)

        emoji = "🔥" if score >= 8 else "😐"
        short_caption = (
            f"🤖 **AI Summary** | {symbol} {interval}\n"
            f"🎯 Action: {action} {emoji}\n"
            f"🧠 Score: {score}/10\n"
            f"📉 Trend: {trend}\n"
            f"⬇️ See full report below"
        )

        full_report = (
            f"📄 **{symbol} Report**\n"
            f"-------------------------------\n"
            f"👀 Pattern: {pattern}|{patterns}\n"
            f"🧱 Levels: {levels}\n"
            f"-------------------------------\n"
            f"📊 Data:\n"
            f"• RSI: `{last_row['rsi']:.1f}`\n"
            f"• MACD hist: `{last_row['macd_hist']:.5f}`\n"
            f"• Funding: `{funding_rate*100:.4f}%`\n"
            f"-------------------------------\n"
            f"💡 Reasoning:\n{reason}\n"
        )

        chart_buf.seek(0)
        await update.message.reply_photo(photo=chart_buf, caption=short_caption, parse_mode='Markdown')
        await update.message.reply_text(full_report, parse_mode='Markdown')
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)

    except Exception as e:
        logging.exception(f"Manual AI Error: {e}")
        try:
            await status_msg.edit_text(f"Error: {str(e)[:100]}")
        except Exception:
            pass
