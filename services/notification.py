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
        reason = result.get('reason', 'N/A')
        
        # Parse trade setup
        setup = result.get('trade_setup', {})
        sl_price = setup.get('sl', 0)
        tp_price = setup.get('tp', 0)
        rr_ratio = setup.get('rr_ratio', 0)
        entry_price = setup.get('entry', market_data.get('close', 0))
        
        # Calculate percentage distance
        current_price = market_data.get('close', 0)
        sl_info = "N/A"
        tp_info = "N/A"
        
        # Position Calculation (Fixed 100 USDT Principal)
        PRINCIPAL = 100.0
        MARGIN_RATE = 0.88
        available_margin = PRINCIPAL * MARGIN_RATE
        position_size_usd = 0
        leverage = 1
        actual_coins = 0
        
        if sl_price and sl_price > 0 and entry_price > 0:
            sl_pct = (sl_price - entry_price) / entry_price * 100
            sign = "+" if sl_pct > 0 else ""
            sl_info = f"`{sl_price}` ({sign}{sl_pct:.2f}%)"
            
            # Calculate Position Size
            # Strategy: Risk 3% of principal per trade
            dist_pct = abs(entry_price - sl_price) / entry_price
            if dist_pct > 0:
                risk_amount = PRINCIPAL * 0.03 
                position_size_usd = risk_amount / dist_pct
                # Cap leverage to max 20x to be safe? Or just raw calc?
                # Let's raw calc but ensure available margin covers it
                leverage = position_size_usd / available_margin
                if leverage < 1: leverage = 1
                actual_coins = position_size_usd / entry_price
            
        if tp_price and tp_price > 0 and entry_price > 0:
            tp_pct = (tp_price - entry_price) / entry_price * 100
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
            f"💰 **仓位**: `{position_size_usd:.0f}U` ({leverage:.1f}x)\n"
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
            f"• 持仓: `{market_data.get('open_interest', 0):.0f}`\n"
            f"-------------------------------\n"
            f"💡 **AI 逻辑分析**:\n• {reason}\n"
            f"-------------------------------\n"
            f"🧮 **建议仓位 (本金100U)**:\n"
            f"• 保证金: `{available_margin:.1f}U`\n"
            f"• 名义价值: `{position_size_usd:.1f}U`\n"
            f"• 杠杆倍数: `{leverage:.1f}x`\n"
            f"• 开仓数量: `{actual_coins:.4f} {symbol.replace('USDT','')}`\n"
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
