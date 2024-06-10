from telegram.ext import CallbackContext, filters, CommandHandler, ApplicationBuilder as BotApplicationBuilder, \
    MessageHandler, CallbackQueryHandler
from telegram import Update
from telegram.error import BadRequest
from models.account import Account
import json
from tools.manuwriter import log
from bot.manager import BotMan
from bot.types import MarketOptions, SelectionListTypes
from api.crypto_service import CoinGeckoService, CoinMarketCapService

botman = BotMan()


async def show_market_types(update: Update, context: CallbackContext, next_state: Account.States):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    account.change_state(next_state)
    await update.message.reply_text(botman.text('config_which_market', account.language),
                                    reply_markup=botman.markets_menu(account.language))


async def prepare_market_selection_menu(update: Update, context: CallbackContext, market: MarketOptions):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        raise LookupError('User not a member')
    list_type = account.match_state_with_selection_type()
    selection_list = account.handle_market_selection(list_type, market)
    return list_type, selection_list


async def select_coin_menu(update: Update, context: CallbackContext):
    try:
        list_type, selection_list = await prepare_market_selection_menu(update, context, MarketOptions.CRYPTO)
        await update.message.reply_text(botman.text('select_your_set', Account.Get(update.effective_chat.id).language),
                                        reply_markup=botman.inline_keyboard(list_type, MarketOptions.CRYPTO, botman.crypto_serv.CoinsInPersian,
                                                                            selection_list, close_button=True))
    except LookupError:
        pass


async def select_currency_menu(update: Update, context: CallbackContext):
    try:
        list_type, selection_list = await prepare_market_selection_menu(update, context, MarketOptions.CURRENCY)
        await update.message.reply_text(botman.text('select_your_set', Account.Get(update.effective_chat.id).language),
                                        reply_markup=botman.inline_keyboard(list_type, MarketOptions.CURRENCY,
                                                                            botman.currency_serv.NationalCurrenciesInPersian,
                                                                            selection_list, full_names=True,
                                                                            close_button=True))
    except LookupError:
        pass


async def select_gold_menu(update: Update, context: CallbackContext):
    try:
        list_type, selection_list = await prepare_market_selection_menu(update, context, MarketOptions.CURRENCY)
        await update.message.reply_text(botman.text('select_your_set', Account.Get(update.effective_chat.id).language),
                                        reply_markup=botman.inline_keyboard(list_type, MarketOptions.GOLD,
                                                                            botman.currency_serv.GoldsInPersian,
                                                                            selection_list, full_names=True,
                                                                            close_button=True))
    except LookupError:
        pass


async def say_youre_not_allowed(reply, language: str = 'fa'):
    await reply(botman.error('not_allowed', language), reply_markup=botman.menu_main(language))
    return None


async def notify_source_change(context: CallbackContext):
    await context.bot.send_message(chat_id=botman.channels[0]['id'],
                                   text=f"منبع قیمت ها به {botman.crypto_serv.Source} تغییر یافت.")


async def update_markets(context: CallbackContext):
    res = await botman.next_post()
    await botman.handle_possible_alarms(context.bot.send_message)
    await context.bot.send_message(chat_id=botman.channels[0]['id'], text=res)


async def cmd_welcome(update: Update, context: CallbackContext):
    acc = Account.Get(update.effective_chat.id)
    # get old or create new account => automatically will be added to Account.Instances
    if not await botman.has_subscribed_us(acc.chat_id, context):
        return await botman.ask_for_subscription(update, acc.language)

    await update.message.reply_text(f'''کاربر {update.message.chat.first_name}\nبه [ ربات قیمت لحظه ای] خوش آمدید🌷🙏

اگر برای اولین بار است که میخواهید از این ربات استفاده کنید توصیه میکنیم از طریق لینک زیر آموزش ویدیوئی ربات را مشاهده کنید:
🎥 https://t.me/Online_pricer/3443''', disable_web_page_preview=True,
                                    reply_markup=botman.mainkeyboard(acc))


async def cmd_get_prices(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        return await botman.ask_for_subscription(update, account.language)

    is_latest_data_valid = botman.currency_serv and botman.currency_serv.latest_data and botman.crypto_serv \
                           and botman.crypto_serv.latest_data and botman.is_main_plan_on
    message = await botman.postman.create_post(desired_coins=account.desired_cryptos,
                                               desired_currencies=account.desired_currencies, for_channel=False,
                                               exactly_right_now=not is_latest_data_valid)

    await update.message.reply_text(message)


async def cmd_equalizer(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        return await botman.ask_for_subscription(update, account.language)

    account.change_state(Account.States.INPUT_EQUALIZER_AMOUNT)
    hint_examples = '''1) 100 USD
2) 10 50 BTC TRX
3) 5 GOLD ETH EUR

'''
    await update.message.reply_text(botman.text('calculator_hint', account.language) + hint_examples + \
                                    botman.text('calculator_hint_footer', account.language), reply_markup=botman.cancel_menu(account.language))


async def cmd_schedule_channel_update(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    botman.main_plan_interval = 10
    try:
        if context.args:
            try:
                botman.main_plan_interval = int(context.args[-1])
            except ValueError:
                botman.main_plan_interval = float(context.args[-1])

    except Exception as e:
        log("Something went wrong while scheduling: ", e)

    if botman.is_main_plan_on:
        await update.message.reply_text("فرآیند به روزرسانی قبلا شروع شده است.")
        return

    botman.is_main_plan_on = True
    context.job_queue.run_repeating(update_markets, interval=botman.main_plan_interval * 60, first=1,
                                    name=botman.main_queue_id)
    await update.message.reply_text(f'زمان بندی {botman.main_plan_interval} دقیقه ای با موفقیت انجام شد.')


async def cmd_stop_schedule(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    current_jobs = context.job_queue.get_jobs_by_name(botman.main_queue_id)
    for job in current_jobs:
        job.schedule_removal()
    botman.is_main_plan_on = False
    botman.crypto_serv.latest_prices = ''
    await update.message.reply_text('به روزرسانی خودکار کانال متوقف شد.')


async def cmd_change_source_to_coingecko(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    botman.crypto_serv = CoinGeckoService()
    await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.')
    await notify_source_change(context)


async def cmd_change_source_to_coinmarketcap(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    botman.crypto_serv = CoinMarketCapService(botman.postman.coinmarketcap_api_key)
    await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.')
    await notify_source_change(context)


async def cmd_admin_login(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        return await botman.ask_for_subscription(update, account.language)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    await update.message.reply_text(
        'اکانت شما به عنوان ادمین تایید اعتبار شد و می توانید از امکانات ادمین استفاده کنید.',
        reply_markup=botman.admin_keyboard(account.language))


async def cmd_send_post(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    account.change_state(Account.States.SEND_POST)
    await update.message.reply_text('''🔹 پست خود را ارسال کنید:
(این پست برای تمامی کاربران ربات ارسال میشود و بعد از ۴۸ ساعت پاک خواهد شد)''', reply_markup=botman.cancel_menu[account.language])


async def cmd_report_statistics(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    stats = Account.Statistics()
    await update.message.reply_text(f'''🔷 تعداد کاربران فعال ربات:

🔹 امروز: {stats['daily']}
🔹 دیروز: {stats['yesterday']}
🔹 هفته اخیر: {stats['weekly']}
🔹 ماه اخیر: {stats['monthly']}
🔹 تعداد کل کاربران ربات: {stats['all']}''')


async def start_equalizing(func_send_message, account: Account, amounts: list, units: list):
    if not isinstance(botman.crypto_serv, CoinMarketCapService):
        await func_send_message(
            "در حال حاضر این گزینه فقط بری ارز دیجیتال و کوین مارکت کپ فعال است. بزودی این امکان گسترش می یابد...")
        return
    response: str
    for amount in amounts:
        for unit in units:
            if unit in botman.crypto_serv.CoinsInPersian:
                header, response, _, absoulte_irt = botman.crypto_serv.equalize(unit, amount, account.calc_cryptos)
                response = botman.currency_serv.irt_to_currencies(absoulte_irt, unit, account.calc_currencies) + "\n\n" + response
            else:
                header, response, absolute_usd, _  = botman.currency_serv.equalize(unit, amount, account.calc_currencies)
                response += "\n\n" + botman.crypto_serv.usd_to_cryptos(absolute_usd, unit, account.calc_cryptos)

            await func_send_message(header + response)


async def handle_messages(update: Update, context: CallbackContext):
    if not update or not update.message:
        return
    match update.message.text:
        case BotMan.Commands.GET_FA.value | BotMan.Commands.GET_EN.value:
            await cmd_get_prices(update, context)
        case BotMan.Commands.CONFIG_PRICE_LIST_FA.value | BotMan.Commands.CONFIG_PRICE_LIST_EN.value:
            await show_market_types(update, context, Account.States.CONFIG_MARKETS)
        case BotMan.Commands.CONFIG_CALCULATOR_FA.value | BotMan.Commands.CONFIG_CALCULATOR_EN.value:
            await show_market_types(update, context, Account.States.CONFIG_CALCULATOR_LIST)
        case BotMan.Commands.CRYPTOS_FA.value | BotMan.Commands.CRYPTOS_EN.value:
            await select_coin_menu(update, context)
        case BotMan.Commands.NATIONAL_CURRENCIES_FA.value | BotMan.Commands.NATIONAL_CURRENCIES_EN.value:
            await select_currency_menu(update, context)
        case BotMan.Commands.GOLDS_FA.value | BotMan.Commands.GOLDS_EN.value:
            await select_gold_menu(update, context)
        case BotMan.Commands.ADMIN_NOTICES_FA.value | BotMan.Commands.ADMIN_NOTICES_EN.value:
            await cmd_send_post(update, context)
        case BotMan.Commands.ADMIN_PLAN_CHANNEL_FA.value | BotMan.Commands.ADMIN_PLAN_CHANNEL_EN.value:
            await cmd_schedule_channel_update(update, context)
        case BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_FA.value | BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_EN.value:
            await cmd_stop_schedule(update, context)
        case BotMan.Commands.ADMIN_STATISTICS_FA.value | BotMan.Commands.ADMIN_STATISTICS_EN.value:
            await cmd_report_statistics(update, context)
        case BotMan.Commands.CALCULATOR_FA.value | BotMan.Commands.CALCULATOR_EN.value:
            await cmd_equalizer(update, context)
        case _:
            # check account state first, to see if he/she is in input state
            account = Account.Get(update.effective_chat.id)
            msg = update.message.text
            if msg == BotMan.Commands.CANCEL_FA.value or msg == BotMan.Commands.CANCEL_EN.value:
                account.change_state()  # reset .state and .state_data
                await update.message.reply_text('خب چه کاری میتونم برات انجام بدم؟',
                                                reply_markup=botman.mainkeyboard(account))
            else:
                match account.state:
                    case Account.States.INPUT_EQUALIZER_AMOUNT:
                        params = msg.split()
                        count_of_params = len(params)
                        # extract parameters and categorize them into units and amounts
                        amounts = []
                        units = [] if not account.cache else account.cache
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
                            await update.message.reply_text(
                                "مقدار وارد شده به عنوان مبلغ اشتباه است! لطفا یک عدد معتبر وارد کنید.",
                                reply_markup=botman.mainkeyboard(account))
                            return

                        # start extracting units
                        while index < count_of_params:
                            source_symbol = params[index].upper()
                            if source_symbol in botman.crypto_serv.CoinsInPersian or source_symbol in botman.currency_serv.CurrenciesInPersian:
                                units.append(source_symbol)
                            else:
                                invalid_units.append(source_symbol)

                            index += 1

                        if invalid_units:
                            await update.message.reply_text(
                                f'هشدار! واحد های زیر  جزء واحد های شناخته شده ربات نیستند: \n {", ".join(invalid_units)}',
                                reply_markup=botman.mainkeyboard(account),
                                reply_to_message_id=update.message.message_id)
                        if not units:
                            # Open select unit reply_markup list
                            account.state = Account.States.INPUT_EQUALIZER_UNIT
                            account.change_state(Account.States.INPUT_EQUALIZER_UNIT, amounts)
                            await update.message.reply_text(
                                f"حال واحد ارز مربوط به این {'مبالغ' if len(amounts) > 1 else 'مبلغ'} را انتخاب کنید:",
                                reply_markup=botman.inline_keyboard(account.match_state_with_selection_type(), MarketOptions.CRYPTO,
                                                                    botman.crypto_serv.CoinsInPersian,
                                                                    close_button=True))
                        else:
                            await start_equalizing(update.message.reply_text, account, amounts, units)
                            account.change_state()  # reset state

                    case Account.States.SEND_POST:
                        if not account.authorization(context.args):
                            await say_youre_not_allowed(update.message.reply_text, account.language)
                            return

                        # admin is trying to send post
                        all_accounts = Account.Everybody()
                        progress_text = "هم اکنون بات شروع به ارسال پست کرده است. این فرایند ممکن است دقایقی طول بکشد...\n\nپیشرفت: "
                        telegram_response = await update.message.reply_text(progress_text)
                        message_id = None

                        try:
                            message_id = int(str(telegram_response['message_id']))
                        except:
                            pass

                        number_of_accounts = len(all_accounts)
                        progress_update_trigger = number_of_accounts // 20 if number_of_accounts >= 100 else 5
                        for index, chat_id in enumerate(all_accounts):
                            try:
                                if message_id and index % progress_update_trigger == 0:
                                    progress = 100 * index / number_of_accounts
                                    await context.bot.edit_message_text(chat_id=account.chat_id,
                                                                        message_id=message_id,
                                                                        text=f'{progress_text}{progress:.2f} %')
                                if chat_id != account.chat_id:
                                    await update.message.copy(chat_id)
                            except:
                                pass  # maybe remove the account from database ?
                        if message_id:
                            await context.bot.delete_message(chat_id=account.chat_id, message_id=message_id)
                        await update.message.reply_text(
                            f'✅ پیام شما با موفقیت برای تمامی کاربران ربات ({len(all_accounts)} نفر) ارسال شد.',
                            reply_markup=botman.admin_keyboard(account.language))
                        account.change_state()  # reset .state and .state_data

                    case _:
                        await update.message.reply_text("متوجه نشدم! دوباره تلاش کن...",
                                                        reply_markup=botman.mainkeyboard(account))


async def handle_inline_keyboard_callbacks(update: Update, context: CallbackContext):
    # FIXME: clicking return on market selection page, will say 'did not understand'
    query = update.callback_query
    account: Account = Account.Get(update.effective_chat.id)
    data = json.loads(query.data)
    if not data:
        return

    market = MarketOptions.Which(data['bt'])
    list_type = SelectionListTypes.Which(data['lt'])
    page: int

    try:
        page = int(data['pg'])
        # if previous line passes ok, means the value is as #Num and indicates the page number and is sending prev/next page signal
    except:
        page = 0

    if page == -1 or data['pg'] is None:
        account.change_state()
        await query.message.edit_text(botman.text('list_updated', account.language))
        return

    # FIXME: Page index log is showing 0 only
    if data['v'] and data['v'][0] == '$':
        if data['v'][1] == '#':
            pages_count = int(data["v"][2:]) + 1
            await query.answer(text=botman.text('log_page_indices', account.language) % (page, pages_count,), show_alert=False)
        return

    if account.state == Account.States.INPUT_EQUALIZER_UNIT:
        if account.cache:
            unit_symbol = data['v'].upper()
            await query.message.edit_text(
                ' '.join([str(amount) for amount in account.cache]) + f" {unit_symbol}"
            )
            await start_equalizing(lambda text: context.bot.send_message(chat_id=account.chat_id, text=text),
                                   account, account.cache, [unit_symbol])
            account.change_state()  # reset state
        else:  # actually this segment occurrence probability is near zero, but i wrote it down anyway to handle any
            # condition possible(or not.!)
            await query.message.edit_text('حالا مبلغ مربوط به این واحد ارزی را وارد کنید:')
            account.change_state(Account.States.INPUT_EQUALIZER_AMOUNT, data['v'].upper())
        return

    try:
        selection_list = account.handle_market_selection(list_type, market, data['v'])

        await query.message.edit_reply_markup(
            reply_markup=botman.inline_keyboard(
                list_type, market,
                (botman.crypto_serv.CoinsInPersian,
                    botman.currency_serv.NationalCurrenciesInPersian,
                    botman.currency_serv.GoldsInPersian,
                )[market.value - 1], selection_list, page=page, language=account.language,
                full_names=market != MarketOptions.CRYPTO, close_button=True
            )
        )

    except ValueError as reached_max_ex:
        max_selection = int(reached_max_ex.__str__())
        if not account.is_premium_member():
            link = f"https://t.me/{Account.GetHardcodeAdmin()['username']}"
            await query.message.reply_text(
                text=botman.error('max_selection', account.language) % (max_selection,) + botman.error('get_premium', account.language),
                reply_markup=botman.inline_url([{'text_key': "premium", 'url': link}])
            )
        else:
            await query.message.reply_text(text=botman.error('max_selection', account.language) % (max_selection,))
    except IndexError as ie:
        log('Invalid market selection procedure', ie, 'general')
        account.change_state()
        await query.message.edit_text(text=botman.error('invalid_market_selection', account.language))
    except BadRequest:
        # when the message content is exactly the same
        pass
    except Exception as selection_ex:
        log('User could\'t select coins', selection_ex, 'general')
        account.change_state()
        await query.message.edit_text(text=botman.error('unknown', account.language))

async def cmd_switch_language(update: Update, context: CallbackContext):
    acc = Account.Get(update.effective_chat.id)
    acc.language = "en" if acc.language.lower() == 'fa' else 'fa'
    await update.message.reply_text(botman.text('language_switched', acc.language))
    acc.save()


def main():
    app = BotApplicationBuilder().token(botman.token).build()

    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("crypto", select_coin_menu))
    app.add_handler(CommandHandler("currency", select_currency_menu))
    app.add_handler(CommandHandler("gold", select_gold_menu))
    app.add_handler(CommandHandler("equalizer", cmd_equalizer))

    # ADMIN SECTION
    app.add_handler(CommandHandler("god", cmd_admin_login))
    app.add_handler(CommandHandler("post", cmd_send_post))
    app.add_handler(CommandHandler("schedule", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("stop", cmd_stop_schedule))
    app.add_handler(CommandHandler("stats", cmd_report_statistics))
    app.add_handler(CommandHandler("gecko", cmd_change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", cmd_change_source_to_coinmarketcap))
    app.add_handler(CommandHandler("lang", cmd_switch_language))

    app.add_handler(MessageHandler(filters.ALL, handle_messages))
    app.add_handler(CallbackQueryHandler(handle_inline_keyboard_callbacks))

    print("Server is up and running...")
    app.run_polling(poll_interval=0.25, timeout=10)
    # app.run_webhook(listen='https://494d-188-165-0-66.ngrok-free.app/', port=4040)


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        print(ex)
        log("Server crashed because: ", ex, 'FATALITY')
