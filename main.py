import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from config.settings import BOT_TOKEN, PROXY_URL
from services.storage import load_data
from handlers.commands import start, add_coin, list_coins, set_risk, calc_position, manual_ai_analyze
from handlers.callbacks import button_handler
from tasks.monitor import monitor_task

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

if __name__ == '__main__':
    load_data()

    builder = ApplicationBuilder().token(BOT_TOKEN)
    if PROXY_URL:
        builder = builder.proxy_url(PROXY_URL).get_updates_proxy_url(PROXY_URL)
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("back", start))
    app.add_handler(CommandHandler("add", add_coin))
    app.add_handler(CommandHandler("list", list_coins))
    app.add_handler(CommandHandler("set", set_risk))
    app.add_handler(CommandHandler("calc", calc_position))
    app.add_handler(CommandHandler("ai", manual_ai_analyze))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(monitor_task, interval=60, first=5)

    print("🚀 Bot started")
    app.run_polling()
