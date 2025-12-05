import logging

from telegram import Update
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

class NotificationService:
    @staticmethod
    def format_report(symbol, interval, result):
        """
        Format the AI analysis result into a caption and a full report.
        
        :param symbol: Trading pair symbol (e.g., BTCUSDT)
        :param interval: Timeframe (e.g., 1h)
        :param result: Dictionary returned by AI analysis
        :return: (short_caption, full_report)
        """
        decision = (result.get('decision', 'hold') or 'hold').upper()
        confidence = result.get('confidence_score', 0)
        
        market_context = result.get('market_context', 'N/A')
        signal_analysis = result.get('signal_analysis', {})
        trade_plan = result.get('trade_plan', {})

        stop_loss = trade_plan.get('stop_loss_price')
        take_profit_levels = trade_plan.get('take_profit_levels', [])
        position_size_usd = trade_plan.get('position_size_usd') or 0
        leverage = trade_plan.get('leverage') or 0
        entry_zone = trade_plan.get('entry_zone', 'N/A')
        reasoning_size = trade_plan.get('reasoning_for_size', 'N/A')
        mark_data = result.get('market_data', {})
        current_price = mark_data.get('close')
        rsi_value = mark_data.get('rsi')
        funding_value = mark_data.get('funding_rate')
        oi_value = mark_data.get('open_interest')
        ai_model = result.get('ai_model')

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
        
        if isinstance(take_profit_levels, list):
            tp_info = ", ".join([_format_level(tp) for tp in take_profit_levels])
        else:
            tp_info = _format_level(take_profit_levels)

        emoji = "🔥" if isinstance(confidence, (int, float)) and confidence >= 80 else "🤔"
        if decision == "HOLD":
            emoji = "⏳"
        
        # Short caption (for image)
        short_caption = (
            f"🤖 **AI 交易计划** | {_md(symbol)} {_md(interval)}\n"
            f"---------------------------\n"
            f"🚀 **操作**: {_md(decision)} {emoji} (信心: {_md(confidence)})\n"
            f"💰 **仓位**: {_md(f'{position_size_usd}U')} ({_md(f'{leverage}x')})\n"
            f"🛑 **止损**: {_md(sl_info)}\n"
            f"🎯 **止盈**: {_md(tp_info)}\n"
            f"⬇️ _查看下方详细逻辑_"
        )
        
        # Full report (text message)
        full_report = (
            f"📄 **{_md(symbol)} 深度研报**\n"
            f"-------------------------------\n"
            f"🌍 **市场背景**: {_md(market_context)}\n"
            f"-------------------------------\n"
            f"📊 **信号分析**:\n"
            f"• 技术面: {_md(signal_analysis.get('technical', 'N/A'))}\n"
            f"• 量能/OI: {_md(signal_analysis.get('volume_oi', 'N/A'))}\n"
            f"• 情绪面: {_md(signal_analysis.get('sentiment', 'N/A'))}\n"
            f"-------------------------------\n"
            f"📊 **市场数据**:\n"
            f"• 现价: {_md(current_price)}\n"
            f"• RSI: {_md(rsi_value)}\n"
            f"• 费率: {_md(funding_value)}\n"
            f"• 持仓: {_md(oi_value)}\n"
            f"• AI模型: {_md(ai_model)}\n"
            f"-------------------------------\n"
            f"🧮 **交易计划**:\n"
            f"• 入场区间: {_md(entry_zone)}\n"
            f"• 止损价格: {_md(sl_info)}\n"
            f"• 止盈目标: {_md(tp_info)}\n"
            f"• 杠杆倍数: {_md(f'{leverage}x')}\n"
            f"• 保证金: {_md(f'{position_size_usd}U')}\n"
            f"• 仓位逻辑: {_md(reasoning_size)}\n"
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
