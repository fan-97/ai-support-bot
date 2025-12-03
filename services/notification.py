import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

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
        decision = (result.get('decision', 'hold') or 'hold').upper()
        confidence = result.get('confidence', 0)
        reasoning = result.get('reasoning', 'N/A')
        analysis_process = result.get('analysis_process', 'N/A')

        stop_loss = result.get('stop_loss')
        take_profit = result.get('take_profit')
        position_size_usd = result.get('position_size_usd') or 0
        leverage = result.get('leverage') or 0

        current_price = market_data.get('close', 0)
        rsi_value = f"{market_data.get('rsi', 0):.1f}"
        funding_value = f"{market_data.get('funding_rate', 0):.4f}%"
        oi_value = f"{market_data.get('open_interest', 0):.0f}"

        def _format_level(level):
            if level is None:
                return "N/A"
            try:
                value = float(level)
                return f"{value}"
            except (TypeError, ValueError):
                return str(level)

        def _md(value):
            if value is None:
                return "N/A"
            return escape_markdown(str(value), version=1)

        sl_info = _format_level(stop_loss)
        tp_info = _format_level(take_profit)

        next_levels = result.get('next_watch_levels', {})
        resistance_levels = [str(level) for level in next_levels.get('resistance', [])]
        support_levels = [str(level) for level in next_levels.get('support', [])]

        emoji = "🔥" if confidence >= 80 else "🤔"
        if decision == "HOLD":
            emoji = "⏳"
        
        # Short caption (for image)
        short_caption = (
            f"🤖 **AI 交易计划** | {_md(symbol)} {_md(interval)}\n"
            f"---------------------------\n"
            f"🚀 **操作**: {_md(decision)} {emoji} (信心: {_md(confidence)})\n"
            f"💰 **仓位**: {_md(f'{position_size_usd:.0f}U')} ({_md(f'{leverage:.1f}x')})\n"
            f"🛑 **止损**: {_md(sl_info)}\n"
            f"🎯 **止盈**: {_md(tp_info)}\n"
            f"⬇️ _查看下方详细逻辑_"
        )
        
        # Full report (text message)
        full_report = (
            f"📄 **{_md(symbol)} 深度研报**\n"
            f"-------------------------------\n"
            f"📊 **分析流程**:\n"
            #f"{_md(analysis_process)}\n"
            #f"-------------------------------\n"
            f"📊 **市场数据**:\n"
            f"• 现价: {_md(current_price)}\n"
            f"• RSI: {_md(rsi_value)}\n"
            f"• 费率: {_md(funding_value)}\n"
            f"• 持仓: {_md(oi_value)}\n"
            f"-------------------------------\n"
            f"**AI 模型**: {_md(result.get('ai_model', 'N/A'))}\n"
            f"💡 **AI 结论**:\n• {_md(reasoning)}\n"
            f"-------------------------------\n"
            f"👁️ **关注区间**:\n"
            f"• 阻力: {_md(', '.join(resistance_levels) if resistance_levels else 'N/A')}\n"
            f"• 支撑: {_md(', '.join(support_levels) if support_levels else 'N/A')}\n"
            f"-------------------------------\n"
            f"🧮 **仓位建议**:\n"
            f"• 名义价值: {_md(f'{position_size_usd:.1f}U')}\n"
            f"• 杠杆倍数: {_md(f'{leverage:.1f}x')}\n"
            f"• 止损/止盈: {_md(sl_info)} / {_md(tp_info)}\n"
        )
        
        return short_caption, full_report

    @staticmethod
    async def send_telegram_report(bot, chat_id, chart_buf, caption, full_report):
        """
        Send the report via Telegram.
        """
        try:
            if chart_buf:
                chart_buf.seek(0)
                await bot.send_photo(chat_id=chat_id, photo=chart_buf, caption=caption, parse_mode='Markdown')
            else:
                await bot.send_message(chat_id=chat_id, text=caption, parse_mode='Markdown')
            await bot.send_message(chat_id=chat_id, text=full_report, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to send Telegram report to {chat_id}: {e}")

    @staticmethod
    async def reply_telegram_report(update: Update, chart_buf, caption, full_report):
        """
        Reply to a Telegram command with the report.
        """
        try:
            if chart_buf:
                chart_buf.seek(0)
                await update.message.reply_photo(photo=chart_buf, caption=caption, parse_mode='Markdown')
            else:
                await update.message.reply_text(caption, parse_mode='Markdown')
            await update.message.reply_text(full_report, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Failed to reply Telegram report: {e}")
