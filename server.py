from telegram.ext import *
from telegram import *
from coins_api import *
from decouple import config
# from threading import Thread


BOT_TOKEN = config('API_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
SCHEDULE_JOB_NAME = config('SCHEDULE_JOB_NAME')
is_channel_updates_started = False

CMC_API_KEY = config('COINMARKETCAP_API_KEY')
desired_coins = list(COIN_NAMES.keys())

priceSourceObject = CoinMarketCap(CMC_API_KEY, desired_coins)

COMMANDS = (CMD_GET, CMD_SELECT_COINS, ) = ('دریافت قیمت ها', 'تنظیم لیست سکه ها',)
menu_main = [
    [KeyboardButton(CMD_GET), KeyboardButton(CMD_SELECT_COINS)],
]

async def notify_changes(context):
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"منبع قیمت ها به {priceSourceObject.Source} تغییر یافت.")

async def anounce_prices(context):
    global priceSourceObject
    res = ''
    try:
        res = priceSourceObject.get()
    except Exception as ex:
        print(f"Geting api from {priceSourceObject.Source} failed: ", ex)
        if priceSourceObject.Source.lower() == 'coinmarketcap':
            priceSourceObject = CoinGecko(desired_coins)
            res = priceSourceObject.get()
        else:
            priceSourceObject = CoinMarketCap(desired_coins)
            res = priceSourceObject.get()
        await notify_changes(context)

    await context.bot.send_message(chat_id=CHANNEL_ID, text=res)


async def cmd_welcome(update, context):
    await update.message.reply_text("خوش آمدید!")

async def cmd_get_prices(update, context):
    await update.message.reply_text(priceSourceObject.get_latest() if priceSourceObject.latest_data and is_channel_updates_started else priceSourceObject.get(),
                reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def handle_messages(update, context):
    msg = update.message.text

    if msg == CMD_GET:
        await cmd_get_prices(update, context)

async def cmd_schedule_channel_update(update, context):
    global is_channel_updates_started
    if not is_channel_updates_started:
        is_channel_updates_started = True
        #threading.Timer(5.0, send_to_channel, args=(context, )).start()
        context.job_queue.run_repeating(anounce_prices, interval=10, first=1, name=SCHEDULE_JOB_NAME)
        await update.message.reply_text('زمان بندی با موفقیت انجام شد.')
    else:
        await update.message.reply_text("فرآیند به روزرسانی قبلا شروع شده است.")

async def cmd_stop_schedule(update, context):
    global is_channel_updates_started
    current_jobs = context.job_queue.get_jobs_by_name(SCHEDULE_JOB_NAME)
    for job in current_jobs:
        job.schedule_removal()
    is_channel_updates_started = False
    priceSourceObject.latest_prices = ''
    await update.message.reply_text('به روزرسانی خودکار کانال متوقف شد.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def cmd_change_source_to_coingecko(update, context):
    global priceSourceObject
    priceSourceObject = CoinGecko(desired_coins)
    await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    await notify_changes(context)


async def cmd_change_source_to_coinmarketcap(update, context):
    global priceSourceObject
    priceSourceObject = CoinMarketCap(CMC_API_KEY, desired_coins)
    await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    await notify_changes(context)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    # ADMIN SECTION
    app.add_handler(CommandHandler("schedule", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("stop", cmd_stop_schedule))
    app.add_handler(CommandHandler("gecko", cmd_change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", cmd_change_source_to_coinmarketcap))

    app.add_handler(MessageHandler(filters.ALL, handle_messages))

    print("Server is up and running...")
    # main_thread = Thread(target=app.run_polling)
    # main_thread.run()

    app.run_polling()


if __name__ == '__main__':
    main()
