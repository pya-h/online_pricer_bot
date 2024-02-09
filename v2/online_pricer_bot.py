from telegram.ext import *
from telegram import *
from api.currency import SourceArena
from db.account import UserStates, Account
from api.crypto import CoinMarketCap, CoinGecko
from decouple import config
from db.account import Account
import json
from tools import manuwriter, mathematix

# constants such as keyboard button texts
COMMANDS = (CMD_GET, CMD_SELECT_COINS, CMD_SELECT_CURRENCIES, CMD_SELECT_GOLDS, CMD_EQUALIZER, CMD_CANCEL) = (
    'مشاهده لیست قیمت من', 'ارز دیجیتال', "ارز", "طلا", "تبدیل گر", "لغو")
ADMIN_COMMANDS = (CMD_ADMIN_POST, CMD_ADMIN_START_SCHEDULE, CMD_ADMIN_STOP_SCHEDULE, CMD_ADMIN_STATISTICS) \
    = ('اطلاع رسانی', 'زمانبندی کانال', 'توقف زمانبندی', 'آمار')

# environment values
BOT_TOKEN = config('API_TOKEN')
CHANNEL_ID = config('CHANNEL_ID')
SCHEDULE_JOB_NAME = config('SCHEDULE_JOB_NAME')
CMC_API_KEY = config('COINMARKETCAP_API_KEY')
CURRENCY_TOKEN = config('CURRENCY_TOKEN')
SECOND_CHANNEL_ID = config('SECOND_CHANNEL_ID')
ABAN_TETHER_TOKEN = config('ABAN_TETHER_TOKEN')

schedule_interval = 5

# main keyboard (soft keyboard of course)
menu_main = [
    [KeyboardButton(CMD_EQUALIZER), KeyboardButton(CMD_GET)],
    [KeyboardButton(CMD_SELECT_COINS), KeyboardButton(CMD_SELECT_CURRENCIES), KeyboardButton(CMD_SELECT_GOLDS)],
]

admin_keyboard = [
    *menu_main,
    [KeyboardButton(CMD_ADMIN_POST), KeyboardButton(CMD_ADMIN_STATISTICS)],
    [KeyboardButton(CMD_ADMIN_START_SCHEDULE), KeyboardButton(CMD_ADMIN_STOP_SCHEDULE)],

]

cancel_menu = [
    [KeyboardButton(CMD_CANCEL)],
]


def get_propper_keyboard(is_admin: bool) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(menu_main if not is_admin else admin_keyboard, resize_keyboard=True)

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
currencyManager = SourceArena(CURRENCY_TOKEN, ABAN_TETHER_TOKEN)
is_channel_updates_started = False


def signed_message(message: str, for_channel: bool=True) -> str:
    timestamp = mathematix.timestamp()
    interval_fa = mathematix.persianify(schedule_interval.__str__())
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
        manuwriter.log("Cannot obtain Currencies! ", ex, currencyManager.Source)
        currencies = currencyManager.get_latest(desired_currencies, short_text=short_text)
    try:
        if desired_coins or (not desired_coins and not desired_currencies):
            # this condition is for preventing default values, when user has selected just currencies
            cryptos = cryptoManager.get(desired_coins, short_text=short_text) if exactly_right_now else \
                cryptoManager.get_latest(desired_coins, short_text)
    except Exception as ex:
        manuwriter.log("Cannot obtain Cryptos! ", ex, cryptoManager.Source)
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
                                        desired_currencies=account.desired_currencies, for_channel=False,
                                        exactly_right_now=not is_latest_data_valid)

        await update.message.reply_text(message, reply_markup=get_propper_keyboard(account.is_admin))
    else:
        await ask2join(update)


async def cmd_select_coins(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if await is_a_member(account, context):
        await update.message.reply_text('''📌 #لیست_بازار_ارز_دیجیتال

👈 با فعال کردن تیک (✅) گزینه های مد نظرتان، آنها را در لیست خود قرار دهید.
👈 با دوباره کلیک کردن، تیک () برداشته شده و آن گزینه از لیستتان حذف می شود.
👈 شما میتوانید نهایت ۲۰ گزینه را در لیست خود قرار دهید.''',
                                        reply_markup=new_inline_keyboard("coins", cryptoManager.CoinsInPersian,
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
                                        reply_markup=new_inline_keyboard("currencies", currencyManager.NationalCurrenciesInPersian,
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
                                        reply_markup=new_inline_keyboard("golds", currencyManager.GoldsInPersian,
                                                                         account.desired_currencies, True))
    else:
        await ask2join(update)


async def cmd_equalizer(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if await is_a_member(account, context):
        account.change_state(UserStates.INPUT_EQUALIZER_AMOUNT)
        await update.message.reply_text('''♻️💱 تبدیل‌گر، 💱☯
در این بخش می‌توانید با مشخص کردن مبلغ مشخص تحت یک ارز مشخص، مبلغ معادل آن در ارزهای دیجیتال دیگر را مشاهده کنید. فرایند معادل‌سازی، بصورت پیش‌فرض، بر اساس لیست ارز دیجیتال تنظیم شده‌ی شما در ربات انجام می‌گردد.

👁‍🗨 راهنما 👁‍🗨
پس از انتخاب گزینه‌ی <تبدیل‌گر> دو روش پیش‌ رو خواهید داشت:
1⃣ مبلغ را وارد کنید، سپس یک لیست طولانی ارز دیجیتال (همانند لیست قسمت تنظیم ارز دیجیتال) مشاهده می‌کنید، با انتخاب ارز دلخواه، ربات فرایند معادل‌سازی را انجام داده و بلافاصله پیام‌بعدی لیست معاد‌ل‌ها را دریافت خواهید کرد.

2⃣ مبلغ را وارد کرده و یک فاصله قرار داده و نماد ارز دیجیتال را در جلوی مبلغ بنویسید. ربات بصورت خودکار ارز دیجیتال موردنظر شما را شناسایی گرده و فرایند را تکمیل می‌کند.''',
                                        reply_markup=get_propper_keyboard(account.is_admin))
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
            manuwriter.log("Something went wrong while scheduling: ", e)
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
        account.change_state(UserStates.SEND_POST)
        await update.message.reply_text('''🔹 پست خود را ارسال کنید:
(این پست برای تمامی کاربران ربات ارسال میشود و بعد از ۴۸ ساعت پاک خواهد شد)''', reply_markup=ReplyKeyboardMarkup(cancel_menu, resize_keyboard=True))
    else:
        await update.message.reply_text('شما اجازه چنین کاری را ندارید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def cmd_report_statistics(update: Update, context: CallbackContext):
    if Account.Get(update.effective_chat.id).authorization(context.args):
        stats = Account.Statistics()
        await update.message.reply_text(f'''🔷 تعداد کاربران فعال ربات:

🔹 امروز: {stats['daily']}
🔹 دیروز: {stats['yesterday']}
🔹 هفته اخیر: {stats['weekly']}
🔹 ماه اخیر: {stats['monthly']}
🔹 تعداد کل کاربران ربات: {stats['all']}''', reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
    else:
        await update.message.reply_text('شما اجازه چنین کاری را ندارید!', reply_markup=ReplyKeyboardMarkup(menu_main, resize_keyboard=True))

async def start_equalizing(func_send_message, account: Account, amounts: list, units: list):
    if isinstance(cryptoManager, CoinMarketCap):
        for amount in amounts:
            for unit in units:
                response = cryptoManager.equalize(unit, amount, account.desired_coins)
                await func_send_message(response)
    else:
        await func_send_message("در حال حاضر این گزینه فقط بری ارز دیجیتال و کوین مارکت کپ فعال است. بزودی این امکان گسترش می یابد...")
        
        
async def handle_messages(update: Update, context: CallbackContext):
    if update and update.message:
        msg = update.message.text
        # TODO: Use match-case here
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
        elif msg == CMD_EQUALIZER:
            await cmd_equalizer(update, context)
        else:
            # check account state first, to see if he/she is in input state
            account = Account.Get(update.effective_chat.id)
            if msg == CMD_CANCEL:
                account.change_state()  # reset .state and .state_data
                await update.message.reply_text('خب چه کاری میتونم برات انجام بدم؟',
                                                reply_markup=get_propper_keyboard(account.is_admin))

            elif account.state == UserStates.SEND_POST and account.authorization(context.args):
                # admin is trying to send post
                all_accounts = Account.Everybody()
                progress_text = "هم اکنون بات شروع به ارسال پست کرده است. این فرایند ممکن است دقایقی طول بکشد...\n\nپیشرفت: "
                telegram_response = await update.message.reply_text(progress_text)
                message_id = None
                try:
                    message_id = telegram_response['message_id']
                except:
                    message_id = None
                number_of_accounts = len(all_accounts)
                progress_update_trigger = number_of_accounts // 20 if number_of_accounts >= 100 else 5
                for index, chat_id in enumerate(all_accounts):
                    try:
                        if message_id and index % progress_update_trigger == 0:
                            progress = 100 * index / number_of_accounts
                            await context.bot.edit_message_text(chat_id=account.chat_id, message_id=message_id, text=f'{progress_text}{progress:.2f} %')
                        if chat_id != account.chat_id:
                            await update.message.copy(chat_id)
                    except:
                        pass  # maybe remove the account from database ?
                if message_id:
                    await context.bot.delete_message(chat_id=account.chat_id, message_id=message_id)
                await update.message.reply_text(f'✅ پیام شما با موفقیت برای تمامی کاربران ربات ({len(all_accounts)} نفر) ارسال شد.',
                                                reply_markup=ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True))
                account.change_state()  # reset .state and .state_data
            elif account.state == UserStates.INPUT_EQUALIZER_AMOUNT:
                params = msg.split()
                count_of_params = len(params)
                # extract parameters and categorize themn into units and amounts
                amounts = []
                units = [] if not account.state_data else account.state_data
                invalid_units = []
                index = 0
                # extract amounts from params
                try:
                    while index < count_of_params:
                        amount = float(params[index])
                        amounts.append(amount)
                        index += 1
                except:
                    pass
                
                if not amounts:
                    await update.message.reply_text("مقدار وارد شده به عنوان مبلغ اشتباه است! لطفا یک عدد معتبر وارد کنید.",
                            reply_markup=get_propper_keyboard(account.is_admin))
                    return
                
                # start extracting units
                while index < count_of_params:
                    source_symbol = params[index].upper()
                    if source_symbol in cryptoManager.CoinsInPersian:
                        units.append(source_symbol)
                    else: # invalud units
                        invalid_units.append(source_symbol)
                        
                    index += 1
                # if there was some units that are invalid are not supported
                if invalid_units:
                    await update.message.reply_text(f'هشدار! واحد های زیر  جزء واحد های شناخته شده ربات نیستند: \n {", ".join(invalid_units)}',
                                                    reply_markup=get_propper_keyboard(account.is_admin), reply_to_message_id=update.message.message_id)    
                if not units:
                    # Open select unit reply_markup list
                    account.state = UserStates.INPUT_EQUALIZER_UNIT
                    account.change_state(UserStates.INPUT_EQUALIZER_UNIT, amounts)
                    await update.message.reply_text(f"حال واحد ارز مربوط به این {'مبالغ' if len(amounts) > 1 else 'مبلغ'} را انتخاب کنید:",
                                                    reply_markup=new_inline_keyboard("coins", cryptoManager.CoinsInPersian, account.desired_coins))
                else:
                    await start_equalizing(update.message.reply_text, account, amounts, units)
                    account.change_state()  # reset state
            else:
                await update.message.reply_text("متوجه نشدم! دوباره تلاش کن...",
                                                reply_markup=get_propper_keyboard(account.is_admin))


async def handle_inline_keyboard_callbacks(update: Update, context: CallbackContext):
    query = update.callback_query
    account = Account.Get(update.effective_chat.id)
    data = json.loads(query.data)
    if data['type'] == "coins":
        if account.state == UserStates.INPUT_EQUALIZER_UNIT:
            if account.state_data:
                await start_equalizing(lambda text: context.bot.send_message(chat_id=account.chat_id, text=text), 
                                    account, account.state_data, [data['value'].upper()])
                account.change_state()  # reset state
            else:  # actually this segment occurance probability is near zero, but i wrote it down anyway to handle any condition possible(or not.!)
                await query.message.edit_text('حالا مبلغ مربوط به این واحد ارزی را وارد کنید:', reply_markup=get_propper_keyboard(account.is_admin))
                account.change_state(UserStates.INPUT_EQUALIZER_AMOUNT, data['value'].upper())
            return
        if not data['value'] in account.desired_coins:
            if len(account.desired_coins) + len(account.desired_currencies) < Account.MaxSelectionInDesiredOnes:
                account.desired_coins.append(data['value'])
            else:
                await query.answer(text='مجموع موارد انتخابی شما به تعداد ۲۰ رسیده است.', show_alert=True)
                return
        else:
            account.desired_coins.remove(data['value'])
        await query.message.edit_reply_markup(reply_markup=new_inline_keyboard("coins", cryptoManager.CoinsInPersian, account.desired_coins))
    
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
                currencyManager.NationalCurrenciesInPersian if data['type'] == "currencies" else currencyManager.GoldsInPersian,
                account.desired_currencies, True)
        )
    account.save()


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("crypto", cmd_select_coins))
    app.add_handler(CommandHandler("currency", cmd_select_currencies))
    app.add_handler(CommandHandler("gold", cmd_select_golds))
    app.add_handler(CommandHandler("equalizer", cmd_equalizer))

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
    app.run_polling(poll_interval=1.5, timeout=50)


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        print(ex)
        manuwriter.log("Server crashed because: ", ex, 'FATALITY')
