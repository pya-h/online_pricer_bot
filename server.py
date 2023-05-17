from telegram.ext import *
from telegram import *
from currency_api import *
from coins_api import *
from decouple import config
from account import Account
import json


# contants such as keyboard button texts
COMMANDS = (CMD_GET, CMD_SELECT_COINS, CMD_SELECT_CURRENCIES, CMD_LEAVE) = ('دریافت قیمت ها', 'تنظیم بازار رمزارزها', "تنظیم بازار ارز، سکه و نفت", 'ترک بات')
# environment values
BOT_TOKEN = config('API_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
SCHEDULE_JOB_NAME = config('SCHEDULE_JOB_NAME')
CMC_API_KEY = config('COINMARKETCAP_API_KEY')
CURRENCY_TOKEN = config('CURRENCY_TOKEN')

# main keyboard (soft keyboard of course)
menu_main = [
    [KeyboardButton(CMD_GET)],
    [KeyboardButton(CMD_SELECT_COINS)],
    [KeyboardButton(CMD_SELECT_CURRENCIES)],
]

# this function creates inline keyboard for selecting coin/currency as desired ones
def newInlineKeyboard(name, all_choices: dict, selected_ones: list = [], show_full_names = False):
    btns = []
    row = []
    i = 0
    for choice in all_choices:
        btn_text = choice if not show_full_names else all_choices[choice]
        i += 1 + int(len(btn_text) / 5)
        if choice in selected_ones:
            btn_text += "✅"
        row.append(InlineKeyboardButton(btn_text, callback_data=json.dumps({"type": name, "value": choice})))
        if i >= 5:
            btns.append(row)
            row = []
            i = 0

    btns.append([InlineKeyboardButton("ثبت!", callback_data=json.dumps({"type": name, "value": "#OK"}))])
    return InlineKeyboardMarkup(btns)

# global variables
cryptoManager = CoinMarketCap(CMC_API_KEY)  # api manager object: instance of CoinGecko or CoinMarketCap
currencyManager = SourceArena(CURRENCY_TOKEN)
is_channel_updates_started = False


def construct_new_message(desired_coins=None, desired_currencies=None, extactly_right_now=True) -> str:
    try:
        currencies = currencyManager.get(desired_currencies) if extactly_right_now else currencyManager.get_latest(desired_currencies)
    except Exception as ex:
        print("Something went wrong while obtaining: Currencies -> ", ex)
        currencies = "متاسفانه دریافت اطلاعات بازار ارز، سکه و طلا و نفت ناموفق بود!"
    try:
        cryptos = cryptoManager.get(desired_coins) if extactly_right_now else cryptoManager.get_latest(desired_coins)
    except:
        print("Something went wrong while obtaining: Cryptos -> ", ex)
        cryptos = "متاسفانه دریافت اطلاعات بازار رمزارزها ناموفق بود!"
    return cryptos + "\n\n\n" + currencies

async def notify_changes(context):
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"منبع قیمت ها به {cryptoManager.Source} تغییر یافت.")


async def anounce_prices(context):
    global cryptoManager
    global currencyManager
    res = ''
    try:
        res = construct_new_message()
    except Exception as ex:
        print(f"Geting api failed: ", ex)
        if cryptoManager.Source.lower() == 'coinmarketcap.com':
            cryptoManager = CoinGecko()
        else:
            cryptoManager = CoinMarketCap(CMC_API_KEY)
        res = construct_new_message()
        await notify_changes(context)

    await context.bot.send_message(chat_id=CHANNEL_ID, text=res)


async def cmd_welcome(update, context):
    Account.Get(update.effective_chat.id)  # get old or create new account => automatically will be added to Account.Instances
    await update.message.reply_text("خوش آمدید!", reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def cmd_get_prices(update, context):
    account = Account.Get(update.effective_chat.id)
    is_latest_data_valid = currencyManager and currencyManager.latest_data and cryptoManager and cryptoManager.latest_data and is_channel_updates_started
    message = construct_new_message(desired_coins=account.desired_coins, desired_currencies=account.desired_currencies, extactly_right_now=not is_latest_data_valid)

    await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def cmd_select_coins(update, context):
    account = Account.Get(update.effective_chat.id)
    await update.message.reply_text("سکه های مورد علاقه تان را انتخاب کنید:", reply_markup=newInlineKeyboard("coins", COINS_PERSIAN_NAMES, account.desired_coins))

async def cmd_select_currencies(update, context):
    account = Account.Get(update.effective_chat.id)
    await update.message.reply_text("سکه های مورد علاقه تان را انتخاب کنید:", reply_markup=newInlineKeyboard("currencies", CURRENCIES_PERSIAN_NAMES, account.desired_currencies, True))


async def cmd_schedule_channel_update(update, context):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        interval = 5
        try:
            if context.args:
                interval = float(context.args[-1])
        except:
            pass
        global is_channel_updates_started
        if not is_channel_updates_started:
            is_channel_updates_started = True
            #threading.Timer(5.0, send_to_channel, args=(context, )).start()
            context.job_queue.run_repeating(anounce_prices, interval=interval*60, first=1, name=SCHEDULE_JOB_NAME)
            await update.message.reply_text(f'زمان بندی {interval} دقیقه ای با موفقیت انجام شد.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
        else:
            await update.message.reply_text("فرآیند به روزرسانی قبلا شروع شده است.", reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!')


async def cmd_stop_schedule(update, context):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        global is_channel_updates_started
        current_jobs = context.job_queue.get_jobs_by_name(SCHEDULE_JOB_NAME)
        for job in current_jobs:
            job.schedule_removal()
        is_channel_updates_started = False
        cryptoManager.latest_prices = ''
        await update.message.reply_text('به روزرسانی خودکار کانال متوقف شد.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!')


async def cmd_change_source_to_coingecko(update, context):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        global cryptoManager
        cryptoManager = CoinGecko()
        await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
        await notify_changes(context)
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!')

async def cmd_change_source_to_coinmarketcap(update, context):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        global cryptoManager
        cryptoManager = CoinMarketCap(CMC_API_KEY)
        await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
        await notify_changes(context)
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!')


async def cmd_admin_login(update, context):
    account = Account.Get(update.effective_chat.id)
    await update.message.reply_text('اکانت شما به عنوان ادمین تایید اعتبار شد و می توانید از امکانات ادمین استفاده کنید.' if account.authorization(context.args)

                               else 'اطلاعات وارد شده صحیح نیستند!')

async def cmd_leave(update, context):
    await update.message.reply_text('اطلاعات و شخصی سازی های شما حذف خواهند شد. ادامه می دهید؟', reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("آره", callback_data=json.dumps({"type": "leave", 'value': True})) , InlineKeyboardButton("نه", callback_data=json.dumps({"type": "leave", 'value': False}))]
    ]))


async def handle_messages(update, context):
    msg = update.message.text

    if msg == CMD_GET:
        await cmd_get_prices(update, context)
    elif msg == CMD_SELECT_COINS:
        await cmd_select_coins(update, context)
    elif msg == CMD_SELECT_CURRENCIES:
        await cmd_select_currencies(update, context)
    elif msg == CMD_LEAVE:
        await cmd_leave(update, context)
    else:
        await update.message.reply_text("متوجه نشدم! دوباره تلاش کن...")



async def handle_inline_keyboard_callbacks(update, context):
    query = update.callback_query
    account = Account.Get(update.effective_chat.id)
    await query.answer()
    data = json.loads(query.data)
    if data["type"] == "urcoins":
        if data["value"] != "#OK" and len(account.desired_coins) < Account.MaxDesiredCoins:
            if not data["value"] in account.desired_coins:
                account.desired_coins.append(data["value"])
            else:
                account.desired_coins.remove(data["value"])
            await query.edit_message_text(text=f"سکه های موردنظر شما (حداکثر {Account.MaxDesiredCoins} مورد): \n" + '، '.join([COINS_PERSIAN_NAMES[x] for x in account.desired_coins]), \
                                          reply_markup=newInlineKeyboard("coins", COINS_PERSIAN_NAMES, account.desired_coins))
        else:
            await query.edit_message_text(text="لیست نهایی سکه های موردنظر شما: \n" + '، '.join([COINS_PERSIAN_NAMES[x] for x in account.desired_coins]))
    elif data["type"] == "urcurrs":
        if data["value"] != "#OK" and len(account.desired_currencies) < Account.MaxDesiredCurrencies:
            if not data["value"] in account.desired_currencies:
                account.desired_currencies.append(data["value"])
            else:
                account.desired_currencies.remove(data["value"])
            await query.edit_message_text(text=f"انتخاب های شما در بازار ارز و سکه و ... (حداکثر {Account.MaxDesiredCurrencies} مورد): \n" + \
                                          '، '.join([CURRENCIES_PERSIAN_NAMES[x] for x in account.desired_currencies]), \
                                              reply_markup=newInlineKeyboard("currencies", CURRENCIES_PERSIAN_NAMES, account.desired_currencies, True))
        else:
            await query.edit_message_text(text="لیست نهایی بازار ارز و سکه و ...  موردنظر شما: \n" + '، '.join([CURRENCIES_PERSIAN_NAMES[x] for x in account.desired_currencies]))
    elif data['type'] == 'leave':
        if data['value']:
            Account.Leave(update.effective_chat.id)
            await query.edit_message_text(text="به سلامت!")
        else:
            await query.edit_message_text(text="عملیات ترک بات لغو شد.")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).read_timeout(20.0).write_timeout(20.0).build()
    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("selectcoins", cmd_select_coins))
    app.add_handler(CommandHandler("selectcurrencies", cmd_select_currencies))
    app.add_handler(CommandHandler("leave", cmd_leave))

    # ADMIN SECTION
    app.add_handler(CommandHandler("god", cmd_admin_login))
    app.add_handler(CommandHandler("schedule", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("stop", cmd_stop_schedule))
    app.add_handler(CommandHandler("gecko", cmd_change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", cmd_change_source_to_coinmarketcap))
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    app.add_handler(CallbackQueryHandler(handle_inline_keyboard_callbacks))

    print("Server is up and running...")

    app.run_polling()

if __name__ == '__main__':
    main()
