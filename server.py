from telegram.ext import *
from telegram import *
from coins_api import *
from decouple import config


BOT_TOKEN = config('API_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
SCHEDULE_JOB_NAME = config('SCHEDULE_JOB_NAME')
channel_sequence_initiated = False


CMC_API_KEY = config('COINMARKETCAP_API_KEY')

COIN_NAMES = {
    'BTC': 'بیت کوین',
    "ETH": 'اتریوم',
    'USDT': 'تتر',
    "BNB": 'بایننس کوین',
    'XRP': 'ریپل',
    "ADA": 'کاردانو',
    'SOL': 'سولانا',
    "MATIC": 'پالیگان',
    'DOT': 'پولکادات',
    "TRX": 'ترون',
    'AVAX': 'آوالانچ',
    "LTC": 'لایت کوین',
    'BCH': 'بیت کوین کش',
    "XMR": 'مونرو',
    'DOGE': 'دوج کوین',
    'SHIB': 'شیبا اینو'
}

priceSourceObject = CoinMarketCap(CMC_API_KEY, COIN_NAMES)
# priceSourceObject = CoinGecko(COIN_NAMES)

async def anounce_prices(context):
    res = priceSourceObject.get()
    await context.bot.send_message(chat_id=CHANNEL_ID, text=res)

async def cmd_schedule_channel_update(update, context):
    global channel_sequence_initiated

    if channel_sequence_initiated == False:
        channel_sequence_initiated = True
        #threading.Timer(5.0, send_to_channel, args=(context, )).start()
        context.job_queue.run_repeating(anounce_prices, interval=300, first=1, name=SCHEDULE_JOB_NAME)
        await update.message.reply_text('زمان بندی با موفقیت انجام شد.')


async def cmd_get_prices(update, context):
    text = priceSourceObject.get()
    await update.message.reply_text(text)


async def stop_schedule(update, context):
    global channel_sequence_initiated
    current_jobs = context.job_queue.get_jobs_by_name(SCHEDULE_JOB_NAME)

    for job in current_jobs:
        job.schedule_removal()
    channel_sequence_initiated = False
    await update.message.reply_text('به روزرسانی خودکار کانال متوقف شد.')

async def change_source_to_coingecko(update, context):
    global priceSourceObject
    priceSourceObject = CoinGecko(COIN_NAMES)
    await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.')

async def change_source_to_coinmarketcap(update, context):
    global priceSourceObject
    priceSourceObject = CoinMarketCap(CMC_API_KEY, COIN_NAMES)
    await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.')


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("stop", stop_schedule))
    app.add_handler(CommandHandler("gecko", change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", change_source_to_coinmarketcap))

    # app.add_handler(MessageHandler(filters.ALL, message_handler))

    print("Server is up and running...")
    app.run_polling()
