from telegram.ext import *
from telegram import *
from coins_api import *
from decouple import config
# from threading import Event
# from time import sleep


BOT_TOKEN = config('API_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
SCHEDULE_JOB_NAME = config('SCHEDULE_JOB_NAME')
is_channel_updates_started = False

CMC_API_KEY = config('COINMARKETCAP_API_KEY')

priceSourceObject = CoinMarketCap(CMC_API_KEY)

COMMANDS = (CMD_GET, CMD_SELECT_COINS, ) = ('دریافت قیمت ها', 'تنظیم لیست سکه ها',)
menu_main = [
    [KeyboardButton(CMD_GET), KeyboardButton(CMD_SELECT_COINS)],
]

coins_keyboard = []
desired_coins = {}

def construct_coins_keyboard():
    global coins_keyboard
    btns = []
    row = []
    i = 0
    for coin in COIN_NAMES:
        row.append(InlineKeyboardButton(COIN_NAMES[coin], callback_data=coin))
        i += 1 + int(len(COIN_NAMES[coin]) / 10)
        if i >= 5:
            btns.append(row)
            row = []
            i = 0
    btns.append([InlineKeyboardButton("حله!", callback_data="#OK")])
    coins_keyboard = InlineKeyboardMarkup(btns)

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
            priceSourceObject = CoinGecko()
            res = priceSourceObject.get()
        else:
            priceSourceObject = CoinMarketCap(CMC_API_KEY)
            res = priceSourceObject.get()
        await notify_changes(context)

    await context.bot.send_message(chat_id=CHANNEL_ID, text=res)


async def cmd_welcome(update, context):
    await update.message.reply_text("خوش آمدید!", reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def cmd_get_prices(update, context):
    cid = update.effective_chat.id
    dc = desired_coins[cid] if cid in desired_coins else None
    await update.message.reply_text(priceSourceObject.get_latest(dc)
                                    if priceSourceObject.latest_data and is_channel_updates_started
                                    else priceSourceObject.get(dc),
                reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def handle_messages(update, context):
    msg = update.message.text

    if msg == CMD_GET:
        await cmd_get_prices(update, context)
    elif msg == CMD_SELECT_COINS:
        global desired_coins
        desired_coins[update.effective_chat.id] = []
        if not coins_keyboard:
            construct_coins_keyboard()
        await update.message.reply_text("سکه های مورد علاقه تان را انتخاب کنید:", reply_markup=coins_keyboard)


async def select_next_coin(update, context):
    query = update.callback_query
    cid = update.effective_chat.id

    await query.answer()
    if query.data != "#OK":
        if not cid in desired_coins:
            desired_coins[cid] = []

        desired_coins[cid].append(query.data)
        await query.edit_message_text(text="سکه های موردنظر شما: \n" + ', '.join(desired_coins[cid]), reply_markup=coins_keyboard)
    else:
        await query.edit_message_text(text="لیست نهایی سکه های موردنظر شما: \n" + ', '.join(desired_coins[cid]))

async def cmd_schedule_channel_update(update, context):
    global is_channel_updates_started
    if not is_channel_updates_started:
        is_channel_updates_started = True
        #threading.Timer(5.0, send_to_channel, args=(context, )).start()
        context.job_queue.run_repeating(anounce_prices, interval=60, first=1, name=SCHEDULE_JOB_NAME)
        await update.message.reply_text('زمان بندی با موفقیت انجام شد.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    else:
        await update.message.reply_text("فرآیند به روزرسانی قبلا شروع شده است.", reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

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
    priceSourceObject = CoinGecko()
    await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    await notify_changes(context)


async def cmd_change_source_to_coinmarketcap(update, context):
    global priceSourceObject
    priceSourceObject = CoinMarketCap(CMC_API_KEY)
    await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    await notify_changes(context)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(20.0).write_timeout(20.0).build()
    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    # ADMIN SECTION
    app.add_handler(CommandHandler("schedule", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("stop", cmd_stop_schedule))
    app.add_handler(CommandHandler("gecko", cmd_change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", cmd_change_source_to_coinmarketcap))
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    app.add_handler(CallbackQueryHandler(select_next_coin))

    print("Server is up and running...")
    # main_thread = Thread(target=app.run_polling)
    # main_thread.run()
    app.run_polling()


if __name__ == '__main__':
    main()
