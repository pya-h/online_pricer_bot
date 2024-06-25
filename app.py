from telegram.ext import CallbackContext, filters, CommandHandler, ApplicationBuilder as BotApplicationBuilder, \
    MessageHandler, CallbackQueryHandler
from telegram import Update, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from models.account import Account
import json
from tools.manuwriter import log
from tools.mathematix import cut_and_separate, persianify
from bot.manager import BotMan
from bot.types import MarketOptions, SelectionListTypes
from api.crypto_service import CoinGeckoService, CoinMarketCapService
from models.alarms import PriceAlarm


botman = BotMan()


async def show_market_types(update: Update, context: CallbackContext, next_state: Account.States):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    account.change_state(next_state)
    await update.message.reply_text(botman.text('which_market', account.language),
                                    reply_markup=botman.markets_menu(account.language))


async def prepare_market_selection_menu(update: Update, context: CallbackContext, market: MarketOptions):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    list_type = account.match_state_with_selection_type()

    await update.message.reply_text(botman.text('select_your_set', account.language),
                                    reply_markup=botman.inline_keyboard(list_type, market,
                                                                        botman.crypto_serv.CoinsInPersian if market == MarketOptions.CRYPTO else (
                                                                            botman.currency_serv.NationalCurrenciesInPersian if market == MarketOptions.CURRENCY
                                                                            else botman.currency_serv.GoldsInPersian
                                                                        ), account.handle_market_selection(list_type,
                                                                                                           market),
                                                                        full_names=market != MarketOptions.CRYPTO,
                                                                        close_button=True))


async def select_coin_menu(update: Update, context: CallbackContext):
    await prepare_market_selection_menu(update, context, MarketOptions.CRYPTO)


async def select_currency_menu(update: Update, context: CallbackContext):
    await prepare_market_selection_menu(update, context, MarketOptions.CURRENCY)


async def select_gold_menu(update: Update, context: CallbackContext):
    await prepare_market_selection_menu(update, context, MarketOptions.GOLD)


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
    await update.message.reply_text(botman.text('welcome_choose_language', acc.language) % (update.message.chat.first_name,),
                                    reply_markup=botman.action_inline_keyboard(BotMan.QueryActions.CHOOSE_LANGUAGE, {'fa': 'language_persian', 'en': 'language_english'}, language=acc.language))


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
                                    botman.text('calculator_hint_footer', account.language),
                                    reply_markup=botman.cancel_menu(account.language))


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
        await update.message.reply_text()
        return

    botman.is_main_plan_on = True
    context.job_queue.run_repeating(update_markets, interval=botman.main_plan_interval * 60, first=1,
                                    name=botman.main_queue_id)
    await update.message.reply_text(botman.text('channel_planning_started', account.language) % (botman.main_plan_interval, ))


async def cmd_stop_schedule(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    current_jobs = context.job_queue.get_jobs_by_name(botman.main_queue_id)
    for job in current_jobs:
        job.schedule_removal()
    botman.is_main_plan_on = False
    botman.crypto_serv.latest_prices = ''
    await update.message.reply_text(botman.text('channel_planning_stopped', account.language))


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
(این پست برای تمامی کاربران ربات ارسال میشود و بعد از ۴۸ ساعت پاک خواهد شد)''',
                                    reply_markup=botman.cancel_menu[account.language])


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
                header, response, _, absolute_irt = botman.crypto_serv.equalize(unit, amount, account.calc_cryptos)
                response = botman.currency_serv.irt_to_currencies(absolute_irt, unit,
                                                                  account.calc_currencies) + "\n\n" + response
            else:
                header, response, absolute_usd, _ = botman.currency_serv.equalize(unit, amount, account.calc_currencies)
                response += "\n\n" + botman.crypto_serv.usd_to_cryptos(absolute_usd, unit, account.calc_cryptos)

            await func_send_message(header + response)


async def list_user_alarms(update: Update, context: CallbackContext):
    account = Account.Get(update.effective_chat.id)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    my_alarms = account.get_alarms()
    return InlineKeyboardMarkup(list(map(lambda alarm: [InlineKeyboardButton(None, callback_data=None)], my_alarms)))

async def handle_action_queries(query: CallbackQuery, context: CallbackContext, account: Account, callback_data: dict | None = None):

    if callback_data:
        callback_data = json.loads(query.data)
    match callback_data['act']:
        case BotMan.QueryActions.CHOOSE_LANGUAGE.value:
            lang = callback_data['v'].lower()
            if lang != 'fa' and lang != 'en':
                await query.answer(text=botman.error('invalid_language', account.language), show_alert=True)
                return
            account.language = lang
            account.save()
            await context.bot.send_message(text=botman.text('language_switched', account.language), chat_id=account.chat_id, reply_markup=botman.mainkeyboard(account))
            await query.answer()
        case BotMan.QueryActions.SELECT_PRICE_UNIT.value:
            data: str = callback_data['v']
            if data:
                data = data.split(botman.CALLBACK_DATA_JOINER)
                market = MarketOptions.Which(int(data[0]))
                symbol = data[1]
                target_price = float(data[2])
                price_unit = data[3]
                current_price: float | None = None  # FIXME: handle golds in EntitiesInDollors, deviding by usd price again
                currency_name: str = None
                try:
                    match market:
                        case MarketOptions.CRYPTO:
                            current_price = botman.crypto_serv.get_single_price(symbol, price_unit)
                            currency_name = botman.crypto_serv.CoinsInPersian[symbol]
                        case MarketOptions.GOLD | MarketOptions.CURRENCY:
                            current_price = botman.currency_serv.get_single_price(symbol, price_unit)
                            currency_name = botman.currency_serv.CurrenciesInPersian[symbol]
                        case _:
                            if symbol in botman.crypto_serv.CoinsInPersian:
                                current_price = botman.crypto_serv.get_single_price(symbol, price_unit)
                                currency_name = botman.crypto_serv.CoinsInPersian[symbol]
                            elif symbol in botman.currency_serv.CurrenciesInPersian:
                                current_price = botman.currency_serv.get_single_price(symbol, price_unit)
                                currency_name = botman.currency_serv.CurrenciesInPersian[symbol]
                            else:
                                raise ValueError("Unknown symbol and market")
                except Exception as ex:
                    log(f'Cannot create the alarm for user {account.chat_id}', ex)
                print(currency_name, current_price)
                if current_price is not None:
                    if not account.can_create_new_alarm:
                        botman.show_reached_max_error(query, account, account.max_alarms_count)
                    alarm = PriceAlarm(account.chat_id, symbol, target_price=target_price, target_unit=price_unit, current_price=current_price)
                    alarm.set()
                    price_unit_str = botman.text(f'price_unit_{price_unit.lower()}', language=account.language)
                    current_price = cut_and_separate(target_price)
                    lang = account.language.lower()
                    if lang == 'fa':
                        current_price = persianify(current_price)
                    await query.message.edit_text(text=botman.text('alarm_set', lang) % (currency_name if lang == 'fa' else symbol, target_price, price_unit_str))
            await query.answer()

async def handle_inline_keyboard_callbacks(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query.data:
        return

    data = json.loads(query.data)
    account: Account = Account.Get(update.effective_chat.id)
    # first check query type
    if 'act' in data:
        # action queries are handled here
        await handle_action_queries(query, context, account, data)
        return

    # list queries are handled below

    # check if user is changing list page:
    page: int

    try:
        page = int(data['pg'])
        # if previous line passes ok, means the value is as #Num and indicates the page number and is sending prev/next page signal
    except:
        page = 0

    if page == -1 or data['pg'] is None:
        account.change_state(clear_cache=True)
        await query.message.edit_text(botman.text('list_updated', account.language))
        return

    # FIXME: Page index log is showing 0 only
    if data['v'] and data['v'][0] == '$':
        if data['v'][1] == '#':
            pages_count = int(data["v"][2:]) + 1
            await query.answer(text=botman.text('log_page_indices', account.language) % (page, pages_count,),
                               show_alert=False)
        return

    market = MarketOptions.Which(data['bt'])
    list_type = SelectionListTypes.Which(data['lt'])

    match list_type:
        case SelectionListTypes.EQUALIZER_UNIT:
            input_amounts = account.get_cache('input_amounts')
            if input_amounts:
                unit_symbol = data['v'].upper()
                await query.message.edit_text(
                    ' '.join([str(amount) for amount in input_amounts]) + f" {unit_symbol}"
                )
                await start_equalizing(lambda text: context.bot.send_message(chat_id=account.chat_id, text=text),
                                       account, input_amounts, [unit_symbol])
                account.change_state(clear_cache=True)  # reset state
            else:  # actually this segment occurrence probability is near zero, but i wrote it down anyway to handle any
                # condition possible(or not.!)
                await query.message.edit_text(botman.text("enter_desired_price", account.language))
                account.change_state(Account.States.INPUT_EQUALIZER_AMOUNT, 'input_symbols', data['v'].upper())
            return
        case SelectionListTypes.ALARM:
            symbol = data['v'].upper()
            account.change_state(Account.States.CREATE_ALARM, 'create_alarm_props',  {'symbol': symbol, 'market': market.value})
            
            message_text = botman.text("enter_desired_price", account.language)
            current_price_description = botman.crypto_serv.get_price_description_row(symbol) if market == MarketOptions.CRYPTO \
                else botman.currency_serv.get_price_description_row(symbol)
            
            if current_price_description:  # TODO: update this when english language is fully implemented
                message_text += f"\n\n{current_price_description}"
            await query.message.edit_text(text=message_text)
            return

    # if the user is configuring a list:

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
        botman.show_reached_max_error(query, account, max_selection)

    except IndexError as ie:
        log('Invalid market selection procedure', ie, 'general')
        account.change_state(clear_cache=True)
        await query.message.edit_text(text=botman.error('invalid_market_selection', account.language))
    except BadRequest:
        # when the message content is exactly the same
        pass
    except Exception as selection_ex:
        log('User could\'t select coins', selection_ex, 'general')
        account.change_state(clear_cache=True)
        await query.message.edit_text(text=botman.error('unknown', account.language))


async def cmd_switch_language(update: Update, context: CallbackContext):
    acc = Account.Get(update.effective_chat.id)
    acc.language = "en" if acc.language.lower() == 'fa' else 'fa'
    await update.message.reply_text(botman.text('language_switched', acc.language))
    acc.save()


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
        case BotMan.Commands.CREATE_ALARM_FA.value | BotMan.Commands.CREATE_ALARM_EN.value:
            await show_market_types(update, context, Account.States.CREATE_ALARM)
        case BotMan.Commands.LIST_ALARMS_FA.value | BotMan.Commands.LIST_ALARMS_EN.value:
            await list_user_alarms(update, context)
        case BotMan.Commands.CRYPTOS_FA.value | BotMan.Commands.CRYPTOS_EN.value:
            await select_coin_menu(update, context)
        case BotMan.Commands.NATIONAL_CURRENCIES_FA.value | BotMan.Commands.NATIONAL_CURRENCIES_EN.value:
            await select_currency_menu(update, context)
        case BotMan.Commands.GOLDS_FA.value | BotMan.Commands.GOLDS_EN.value:
            await select_gold_menu(update, context)
        case BotMan.Commands.CALCULATOR_FA.value | BotMan.Commands.CALCULATOR_EN.value:
            await cmd_equalizer(update, context)
        case BotMan.Commands.ADMIN_NOTICES_FA.value | BotMan.Commands.ADMIN_NOTICES_EN.value:
            await cmd_send_post(update, context)
        case BotMan.Commands.ADMIN_PLAN_CHANNEL_FA.value | BotMan.Commands.ADMIN_PLAN_CHANNEL_EN.value:
            await cmd_schedule_channel_update(update, context)
        case BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_FA.value | BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_EN.value:
            await cmd_stop_schedule(update, context)
        case BotMan.Commands.ADMIN_STATISTICS_FA.value | BotMan.Commands.ADMIN_STATISTICS_EN.value:
            await cmd_report_statistics(update, context)
        case BotMan.Commands.CANCEL_FA.value | BotMan.Commands.CANCEL_EN.value:
            account = Account.Get(update.effective_chat.id)
            account.change_state(clear_cache=True)  # reset .state and .state_data
            await update.message.reply_text(botman.text('operation_canceled', account.language),
                                            reply_markup=botman.mainkeyboard(account))
        case BotMan.Commands.RETURN_FA.value | BotMan.Commands.RETURN_EN.value:
            account = Account.Get(update.effective_chat.id)
            account.change_state(clear_cache=True)  # TODO: For now it clears; if in future there was some place that just needs turning back one step, this will ne updated.
            await update.message.reply_text(botman.text('what_can_i_do', account.language), reply_markup=botman.mainkeyboard(account))
        case _:
            # check account state first, to see if he/she is in input state
            account = Account.Get(update.effective_chat.id)
            msg = update.message.text

            match account.state:
                case Account.States.INPUT_EQUALIZER_AMOUNT:
                    params = msg.split()
                    count_of_params = len(params)
                    # todo: for now input must be first price and then symbols => you could make the order dynamic
                    # extract parameters and categorize them into units and amounts
                    amounts = []
                    units = account.get_cache('input_symbols') or []
                    if not isinstance(units, list):
                        units = [units]
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
                            botman.error('invalid_amount', account.language),
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
                            botman.error('unrecognized_currency_symbols', account.language) + ", ".join(
                                invalid_units),
                            reply_markup=botman.mainkeyboard(account),
                            reply_to_message_id=update.message.message_id)
                    if not units:
                        # Open select unit reply_markup list
                        account.change_state(Account.States.INPUT_EQUALIZER_UNIT, 'input_amounts', amounts)
                        await update.message.reply_text(
                            botman.text("select_price_currency_unit", account.language),
                            reply_markup=botman.inline_keyboard(account.match_state_with_selection_type(),
                                                                MarketOptions.CRYPTO,
                                                                botman.crypto_serv.CoinsInPersian,
                                                                close_button=True))
                    else:
                        await start_equalizing(update.message.reply_text, account, amounts, units)
                        account.change_state(clear_cache=True)  # reset state
                        
                case Account.States.CREATE_ALARM:
                    props = account.get_cache('create_alarm_props')
                    try:
                        price = float(msg)
                    except:
                        await update.message.reply_text(botman.error('invalid_price', account.language), reply_markup=botman.cancel_menu(account.language))
                        return
                    
                    symbol = props['symbol']
                    market = props['market']
                    data_prefix = f'{market}{botman.CALLBACK_DATA_JOINER}{symbol}{botman.CALLBACK_DATA_JOINER}{price}'
                    await update.message.reply_text(botman.text('whats_price_unit', account.language), 
                                                    reply_markup=botman.action_inline_keyboard(BotMan.QueryActions.SELECT_PRICE_UNIT,
                                                                    {f'{data_prefix}{botman.CALLBACK_DATA_JOINER}irt': 'price_unit_irt', 
                                                                     f'{data_prefix}{botman.CALLBACK_DATA_JOINER}usd': 'price_unit_usd'}))
                    account.delete_specific_cache('create_alarm_props')

                case Account.States.SEND_POST:
                    if not account.authorization(context.args):
                        await say_youre_not_allowed(update.message.reply_text, account.language)
                        return

                    # admin is trying to send post
                    all_accounts = Account.Everybody()
                    progress_text = botman.text('sending_your_post', account.language)
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
                        botman.text("post_successfully_sent", account.language) % (len(all_accounts),),
                        reply_markup=botman.admin_keyboard(account.language))
                    account.change_state(clear_cache=True)  # reset .state and .state_data
                case _:
                    await update.message.reply_text(botman.error('what_the_fuck', account.language),
                                                    reply_markup=botman.mainkeyboard(account))


def main():
    app = BotApplicationBuilder().token(botman.token).build()

    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("crypto", select_coin_menu))
    app.add_handler(CommandHandler("currency", select_currency_menu))
    app.add_handler(CommandHandler("gold", select_gold_menu))
    app.add_handler(CommandHandler("equalizer", cmd_equalizer))
    # app.add_handler(CommandHandler("new_alarm", cmd_create_alarm))

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
