from telegram.ext import *
from telegram import *
from coins_api import *
from decouple import config
# from threading import Thread


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

COMMANDS = (CMD_GET, CMD_SELECT_COINS, ) = ('دریافت قیمت ها', 'تنظیم لیست سکه ها',)
menu_main = [[KeyboardButton(CMD_GET), KeyboardButton(CMD_SELECT_COINS)]]


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
    await update.message.reply_text(priceSourceObject.latest_prices if priceSourceObject.latest_prices else priceSourceObject.get(),
                                    reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def stop_schedule(update, context):
    global channel_sequence_initiated
    current_jobs = context.job_queue.get_jobs_by_name(SCHEDULE_JOB_NAME)

    for job in current_jobs:
        job.schedule_removal()
    channel_sequence_initiated = False
    await update.message.reply_text('به روزرسانی خودکار کانال متوقف شد.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def change_source_to_coingecko(update, context):
    global priceSourceObject
    priceSourceObject = CoinGecko(COIN_NAMES)
    await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def change_source_to_coinmarketcap(update, context):
    global priceSourceObject
    priceSourceObject = CoinMarketCap(CMC_API_KEY, COIN_NAMES)
    await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def handle_messages(update, context):
    msg = update.message.text

    if msg == CMD_GET:
        await cmd_get_prices(update, context)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("stop", stop_schedule))
    app.add_handler(CommandHandler("gecko", change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", change_source_to_coinmarketcap))
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    # app.add_handler(MessageHandler(filters.ALL, message_handler))

    print("Server is up and running...")
    # main_thread = Thread(target=app.run_polling)
    # main_thread.run()

    app.run_polling()


if __name__ == '__main__':
    main()
