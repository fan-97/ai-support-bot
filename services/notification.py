import logging
from telegram.ext import ContextTypes
from telegram import Update

class NotificationService:
    @staticmethod
    def format_report(symbol, interval, result, market_data):
        """
        Format the AI analysis result into a caption and a full report.
        
        :param symbol: Trading pair symbol (e.g., BTCUSDT)
        :param interval: Timeframe (e.g., 1h)
        :param result: Dictionary returned by AI analysis
        :param market_data: Dictionary containing 'close', 'rsi', 'funding_rate'
        :return: (short_caption, full_report)
        """
        trend = result.get('trend', 'N/A')
        pattern = result.get('pattern', 'N/A')
        score = result.get('score', 0)
        action = result.get('action', 'WAIT').upper()
        reason = result.get('reason', 'N/A').replace('\n', '\n• ') # Optimize layout
        
        # Parse trade setup
        setup = result.get('trade_setup', {})
        sl_price = setup.get('sl', 0)
        tp_price = setup.get('tp', 0)
        rr_ratio = setup.get('rr_ratio', 0)
        
        # Calculate percentage distance
        current_price = market_data.get('close', 0)
        sl_info = "N/A"
        tp_info = "N/A"
        
        if sl_price and sl_price > 0 and current_price > 0:
            sl_pct = (sl_price - current_price) / current_price * 100
            # sign = "+" if sl_pct > 0 else ""
            # sl_info = f"`{sl_price}` ({sign}{sl_pct:.2f}%)"
            # Logic from original code:
            sign = "+" if sl_pct > 0 else ""
            sl_info = f"`{sl_price}` ({sign}{sl_pct:.2f}%)"

        if tp_price and tp_price > 0 and current_price > 0:
            tp_pct = (tp_price - current_price) / current_price * 100
            sign = "+" if tp_pct > 0 else ""
            tp_info = f"`{tp_price}` ({sign}{tp_pct:.2f}%)"

        # Build message content
        emoji = "🔥" if score >= 8 else "🤔"
        if action == "WAIT": emoji = "⏳"
        
        # Short caption (for image)
        short_caption = (
            f"🤖 **AI 交易计划** | {symbol} {interval}\n"
            f"---------------------------\n"
            f"🚀 **操作**: {action} {emoji} (信心: {score})\n"
            f"🛑 **止损**: {sl_info}\n"
            f"🎯 **止盈**: {tp_info}\n"
            f"⚖️ **盈亏比**: `{rr_ratio}`\n"
            f"⬇️ _查看下方详细逻辑_"
        )
        
        # Full report (text message)
        full_report = (
            f"📄 **{symbol} 深度研报**\n"
            f"-------------------------------\n"
            f"📈 **当前趋势**: {trend}\n"
            f"👀 **识别形态**: {pattern}\n"
            f"-------------------------------\n"
            f"📊 **市场数据**:\n"
            f"• 现价: `{current_price}`\n"
            f"• RSI: `{market_data.get('rsi', 0):.1f}`\n"
            f"• 费率: `{market_data.get('funding_rate', 0):.4f}%`\n"
            f"-------------------------------\n"
            f"💡 **AI 逻辑分析**:\n• {reason}\n"
        )
        
        return short_caption, full_report

    @staticmethod
    async def send_telegram_report(bot, chat_id, chart_buf, caption, full_report):
        """
        Send the report via Telegram.
        """
        try:
            chart_buf.seek(0)
            await bot.send_photo(chat_id=chat_id, photo=chart_buf, caption=caption, parse_mode='Markdown')
            await bot.send_message(chat_id=chat_id, text=full_report, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to send Telegram report to {chat_id}: {e}")

    @staticmethod
    async def reply_telegram_report(update: Update, chart_buf, caption, full_report):
        """
        Reply to a Telegram command with the report.
        """
        try:
            chart_buf.seek(0)
            await update.message.reply_photo(photo=chart_buf, caption=caption, parse_mode='Markdown')
            await update.message.reply_text(full_report, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to reply Telegram report: {e}")

    # Placeholder for other notification channels
    # @staticmethod
    # async def send_email_report(...):
    #     pass
