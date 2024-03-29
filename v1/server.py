from telegram.ext import *
from telegram import *
from currency_api import *
from coins_api import *
from decouple import config
from account import Account
import json

# constants such as keyboard button texts
COMMANDS = (CMD_GET, CMD_SELECT_COINS, CMD_SELECT_CURRENCIES, CMD_SELECT_GOLDS) = (
    'مشاهده لیست قیمت من', 'ارز دیجیتال', "ارز", "طلا")
ADMIN_COMMANDS = (CMD_ADMIN_POST, CMD_ADMIN_START_SCHEDULE, CMD_ADMIN_STOP_SCHEDULE, CMD_ADMIN_STATISTICS) \
    = ('اطلاع رسانی', 'زمانبندی کانال', 'توقف زمانبندی', 'آمار')

# environment values
BOT_TOKEN = config('API_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
SCHEDULE_JOB_NAME = config('SCHEDULE_JOB_NAME')
CMC_API_KEY = config('COINMARKETCAP_API_KEY')
CURRENCY_TOKEN = config('CURRENCY_TOKEN')
SECOND_CHANNEL_ID = config('SECOND_CHANNEL_ID')
# WEBHOOK_URL = config("WEBHOOK_URL")
# WEBHOOK_PORT = int(config("WEBHOOK_PORT", 80))
schedule_interval = 5

# main keyboard (soft keyboard of course)
menu_main = [
    [KeyboardButton(CMD_GET)],
    [KeyboardButton(CMD_SELECT_COINS), KeyboardButton(CMD_SELECT_CURRENCIES), KeyboardButton(CMD_SELECT_GOLDS)],
]

admin_keyboard = [
    *menu_main,
    [KeyboardButton(CMD_ADMIN_POST), KeyboardButton(CMD_ADMIN_STATISTICS)],
    [KeyboardButton(CMD_ADMIN_START_SCHEDULE), KeyboardButton(CMD_ADMIN_STOP_SCHEDULE)],

]

async def is_a_member(account: Account, context: CallbackContext):
    chat1 = await context.bot.get_chat_member(CHANNEL_ID, account.chat_id)
    chat2 = await context.bot.get_chat_member(SECOND_CHANNEL_ID, account.chat_id)
    return chat1.status != ChatMember.LEFT and chat2.status != ChatMember.LEFT


async def ask2join(update):
    await update.message.reply_text('''کاربر عزیز🌷🙏

⚠️ برای استفاده از ۱۴۸ بازار مالی مختلف در [ ربات قیمت لحظه ای ] باید عضو کانال های زیر شوید:

🆔 @Online_pricer
🆔 @Crypto_AKSA

✅ بعد از عضویت در این کانال ها، دوباره بر روی گزینه دلخواه خود کلیک کنید.''',
                                    reply_markup=InlineKeyboardMarkup([
                                        [InlineKeyboardButton("@Crypto_AKSA", url="https://t.me/Crypto_AKSA"),
                                         InlineKeyboardButton("@Online_pricer", url="https://t.me/Online_pricer")]
                                    ]))


# this function creates inline keyboard for selecting coin/currency as desired ones
def new_inline_keyboard(name, all_choices: dict, selected_ones: list, show_full_names: bool=False):
    if not selected_ones:
        selected_ones = []
    buttons = []
    row = []
    i = 0
    for choice in all_choices:
        btn_text = choice if not show_full_names else all_choices[choice]
        i += 1 + int(len(btn_text) / 5)
        if choice in selected_ones:
            btn_text += "✅"
        row.append(InlineKeyboardButton(btn_text, callback_data=json.dumps({"type": name, "value": choice})))
        if i >= 5:
            buttons.append(row)
            row = []
            i = 0
    # buttons.append([InlineKeyboardButton("ثبت!", callback_data=json.dumps({"type": name, "value": "#OK"}))])
    return InlineKeyboardMarkup(buttons)


# global variables
cryptoManager = CoinMarketCap(CMC_API_KEY)  # api manager object: instance of CoinGecko or CoinMarketCap
currencyManager = SourceArena(CURRENCY_TOKEN)
is_channel_updates_started = False


def signed_message(message: str, for_channel: bool=True) -> str:
    timestamp = tools.timestamp()
    interval_fa = tools.persianify(schedule_interval.__str__())
    header = f'✅ بروزرسانی قیمت ها (هر {interval_fa} دقیقه)\n' if for_channel else ''
    header += timestamp + '\n' # + '🆔 آدرس کانال: @Online_pricer\n⚜️ آدرس دیگر مجموعه های ما: @Crypto_AKSA\n'
    footer = '🆔 @Online_pricer\n🤖 @Online_pricer_bot'
    return f'{header}\n{message}\n{footer}'

def construct_new_message(desired_coins=None, desired_currencies=None, exactly_right_now=True, short_text=True, for_channel=True) -> str:
    currencies = cryptos = ''

    try:
        if desired_currencies or (not desired_coins and not desired_currencies):
            # this condition is for preventing default values, when user has selected just cryptos
            currencies = currencyManager.get(desired_currencies, short_text=short_text) if exactly_right_now else \
                currencyManager.get_latest(desired_currencies)
    except Exception as ex:
        tools.log("Cannot obtain Currencies! ", ex)
        currencies = currencyManager.get_latest(desired_currencies, short_text=short_text)
    try:
        if desired_coins or (not desired_coins and not desired_currencies):
            # this condition is for preventing default values, when user has selected just currencies
            cryptos = cryptoManager.get(desired_coins, short_text=short_text) if exactly_right_now else \
                cryptoManager.get_latest(desired_coins)
    except Exception as ex:
        tools.log("Cannot obtain Cryptos! ", ex)
        cryptos = cryptoManager.get_latest(desired_coins, short_text=short_text)
    return signed_message(currencies + cryptos, for_channel=for_channel)


async def notify_changes(context: CallbackContext):
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"منبع قیمت ها به {cryptoManager.Source} تغییر یافت.")


async def announce_prices(context: CallbackContext):
    global cryptoManager
    global currencyManager
    res = construct_new_message()
    await context.bot.send_message(chat_id=CHANNEL_ID, text=res)


async def cmd_welcome(update: Update, context: CallbackContext):
    acc = Account.Get(update.effective_chat.id)
    # get old or create new account => automatically will be added to Account.Instances
    if await is_a_member(acc, context):
        await update.message.reply_text(f'''کاربر {update.message.chat.first_name}\nبه [ ربات قیمت لحظه ای] خوش آمدید🌷🙏

اگر برای اولین بار است که میخواهید از این ربات استفاده کنید توصیه میکنیم از طریق لینک زیر آموزش ویدیوئی ربات را مشاهده کنید:
🎥 https://t.me/Online_pricer/3443''', disable_web_page_preview=True,
                                        reply_markup=ReplyKeyboardMarkup(menu_main if not acc.is_admin else admin_keyboard, resize_keyboard=True))
    else:
        await ask2join(update)


async def cmd_get_prices(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if await is_a_member(account, context):
        is_latest_data_valid = currencyManager and currencyManager.latest_data and cryptoManager \
                               and cryptoManager.latest_data and is_channel_updates_started
        message = construct_new_message(desired_coins=account.desired_coins,
                                        desired_currencies=account.desired_currencies, for_channel=False, short_text=False,
                                        exactly_right_now=not is_latest_data_valid, )

        await update.message.reply_text(message, reply_markup=ReplyKeyboardMarkup(menu_main if not account.is_admin else admin_keyboard, resize_keyboard=True))
    else:
        await ask2join(update)


async def cmd_select_coins(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if await is_a_member(account, context):
        await update.message.reply_text('''📌 #لیست_بازار_ارز_دیجیتال

👈 با فعال کردن تیک (✅) گزینه های مد نظرتان، آنها را در لیست خود قرار دهید.
👈 با دوباره کلیک کردن، تیک () برداشته شده و آن گزینه از لیستتان حذف می شود.
👈 شما میتوانید نهایت ۲۰ گزینه را در لیست خود قرار دهید.''',
                                        reply_markup=new_inline_keyboard("coins", cryptoManager.dict_persian_names,
                                                                         account.desired_coins))
    else:
        await ask2join(update)


async def cmd_select_currencies(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if await is_a_member(account, context):
        await update.message.reply_text('''📌 #لیست_بازار_ارز

👈 با فعال کردن تیک (✅) گزینه های مد نظرتان، آنها را در لیست خود قرار دهید.
👈 با دوباره کلیک کردن، تیک () برداشته شده و آن گزینه از لیستتان حذف می شود.
👈 شما میتوانید نهایت ۲۰ گزینه را در لیست خود قرار دهید.''',
                                        reply_markup=new_inline_keyboard("currencies", currencyManager.just_currency_names,
                                                                         account.desired_currencies, True))
    else:
        await ask2join(update)


# TODO: complete this
async def cmd_select_golds(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if await is_a_member(account, context):
        await update.message.reply_text(    '''📌 #لیست_بازار_طلا

👈 با فعال کردن تیک (✅) گزینه های مد نظرتان، آنها را در لیست خود قرار دهید.
👈 با دوباره کلیک کردن، تیک () برداشته شده و آن گزینه از لیستتان حذف می شود.
👈 شما میتوانید نهایت ۲۰ گزینه را در لیست خود قرار دهید.''',
                                        reply_markup=new_inline_keyboard("golds", currencyManager.just_gold_names,
                                                                         account.desired_currencies, True))
    else:
        await ask2join(update)


async def cmd_schedule_channel_update(update: Update, context: CallbackContext):
    global schedule_interval
    if Account.Get(update.effective_chat.id).authorization(context.args):
        schedule_interval = 5
        try:
            if context.args:
                try:
                    schedule_interval = int(context.args[-1])
                except ValueError:
                    schedule_interval = float(context.args[-1])

        except Exception as e:
            tools.log("Something went wrong while scheduling: ", e)
            pass
        global is_channel_updates_started
        if not is_channel_updates_started:
            is_channel_updates_started = True
            context.job_queue.run_repeating(announce_prices, interval=schedule_interval * 60, first=1,
                                            name=SCHEDULE_JOB_NAME)
            await update.message.reply_text(f'زمان بندی {schedule_interval} دقیقه ای با موفقیت انجام شد.',
                                            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text("فرآیند به روزرسانی قبلا شروع شده است.",
                                            reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def cmd_stop_schedule(update: Update, context: CallbackContext):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        global is_channel_updates_started
        current_jobs = context.job_queue.get_jobs_by_name(SCHEDULE_JOB_NAME)
        for job in current_jobs:
            job.schedule_removal()
        is_channel_updates_started = False
        cryptoManager.latest_prices = ''
        await update.message.reply_text('به روزرسانی خودکار کانال متوقف شد.',
                                        reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def cmd_change_source_to_coingecko(update: Update, context: CallbackContext):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        global cryptoManager
        cryptoManager = CoinGecko()
        await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.',
                                        reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
        await notify_changes(context)
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def cmd_change_source_to_coinmarketcap(update: Update, context: CallbackContext):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        global cryptoManager
        cryptoManager = CoinMarketCap(CMC_API_KEY)
        await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.',
                                        reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
        await notify_changes(context)
    else:
        await update.message.reply_text('شما مجاز به انجام چنین کاری نیستید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))


async def cmd_admin_login(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if await is_a_member(account, context):
        if account.authorization(context.args):
            await update.message.reply_text(
                'اکانت شما به عنوان ادمین تایید اعتبار شد و می توانید از امکانات ادمین استفاده کنید.', reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
        else:
            await update.message.reply_text('اطلاعات وارد شده صحیح نیستند!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))
    else:
        await ask2join(update)

async def cmd_send_post(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if account.authorization(context.args):
        account.state = Account.STATE_SEND_POST
        await update.message.reply_text('پستی که میخواهید برای کاران ارسال شود را بفرستید:', reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text('شما اجازه چنین کاری را ندارید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def cmd_report_statistics(update: Update, context: CallbackContext):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        stats = Account.Statistics()
        await update.message.reply_text(f'''تعداد کاربران فعال:
    امروز: {stats['daily']}
    هفته اخیر: {stats['weekly']}
    ماه اخیر: {stats['monthly']}
تعداد کل کاربران ربات: {stats['all']}''', reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text('شما اجازه چنین کاری را ندارید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def handle_messages(update: Update, context: CallbackContext):
    if update and update.message:
        msg = update.message.text

        if msg == CMD_GET:
            await cmd_get_prices(update, context)
        elif msg == CMD_SELECT_COINS:
            await cmd_select_coins(update, context)
        elif msg == CMD_SELECT_CURRENCIES:
            await cmd_select_currencies(update, context)
        elif msg == CMD_SELECT_GOLDS:
            await cmd_select_golds(update, context)
        elif msg == CMD_ADMIN_POST:
            await cmd_send_post(update, context)
        elif msg == CMD_ADMIN_START_SCHEDULE:
            await cmd_schedule_channel_update(update, context)
        elif msg == CMD_ADMIN_STOP_SCHEDULE:
            await cmd_stop_schedule(update, context)
        elif msg == CMD_ADMIN_STATISTICS:
            await cmd_report_statistics(update, context)
        else:
            # check account state first, to see if he/she is in input state
            account = Account.Get(update.effective_chat.id)
            if account.state == Account.STATE_SEND_POST and account.authorization(context.args):
                # admin is trying to send post
                for chat_id in Account.Everybody():
                    try:
                        if chat_id != account.chat_id:
                            await update.message.copy(chat_id)
                    except:
                        pass  # maybe remove the account from database>?
                await update.message.reply_text('پیام شما با موفقیت برای کاربران بات ارسال شد!', reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
                account.state = None
            else:
                await update.message.reply_text("متوجه نشدم! دوباره تلاش کن...", reply_markup=ReplyKeyboardMarkup(menu_main if not account.is_admin else admin_keyboard, resize_keyboard=True))


async def handle_inline_keyboard_callbacks(update: Update, context: CallbackContext):
    query = update.callback_query
    account = Account.Get(update.effective_chat.id)
    data = json.loads(query.data)
    if data['type'] == "coins":
            if not data['value'] in account.desired_coins:
                if len(account.desired_coins) + len(account.desired_currencies) < Account.MaxSelectionInDesiredOnes:
                    account.desired_coins.append(data['value'])
                else:
                    await query.answer(text='مجموع موارد انتخابی شما به تعداد ۲۰ رسیده است.', show_alert=True)
                    return
            else:
                account.desired_coins.remove(data['value'])
            await query.message.edit_reply_markup(reply_markup=new_inline_keyboard("coins", cryptoManager.dict_persian_names, account.desired_coins))

    elif data['type'] == "currencies" or data['type'] == "golds":
            if not data['value'] in account.desired_currencies:
                if len(account.desired_coins) + len(account.desired_currencies) < Account.MaxSelectionInDesiredOnes:
                    account.desired_currencies.append(data['value'])
                else:
                    await query.answer(text='مجموع موارد انتخابی شما به تعداد ۲۰ رسیده است.', show_alert=True)
                    return
            else:
                account.desired_currencies.remove(data['value'])

            await query.message.edit_reply_markup(reply_markup=new_inline_keyboard(
                    data['type'],
                    currencyManager.just_currency_names if data['type'] == "currencies" else currencyManager.just_gold_names,
                    account.desired_currencies, True)
            )
    account.save()


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("crypto", cmd_select_coins))
    app.add_handler(CommandHandler("currency", cmd_select_currencies))
    app.add_handler(CommandHandler("gold", cmd_select_currencies))

    # ADMIN SECTION
    app.add_handler(CommandHandler("god", cmd_admin_login))
    app.add_handler(CommandHandler("post", cmd_send_post))
    app.add_handler(CommandHandler("schedule", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("stop", cmd_stop_schedule))
    app.add_handler(CommandHandler("stats", cmd_report_statistics))
    app.add_handler(CommandHandler("gecko", cmd_change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", cmd_change_source_to_coinmarketcap))
    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    app.add_handler(CallbackQueryHandler(handle_inline_keyboard_callbacks))

    print("Server is up and running...")
    # print(WEBHOOK_URL, WEBHOOK_PORT)
    app.run_polling(poll_interval=1, timeout=50)
    # app.run_webhook(listen="0.0.0.0", port=WEBHOOK_PORT, webhook_url=f"{WEBHOOK_URL}", stop_signals=None)


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        print(ex)
        tools.log("Server crashed because: ", ex)
