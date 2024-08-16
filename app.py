from telegram.ext import CallbackContext, filters, CommandHandler, ApplicationBuilder as BotApplicationBuilder, \
    MessageHandler, CallbackQueryHandler
from telegram.constants import ChatType
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
from typing import List
from tools.exceptions import NoLatestDataException, InvalidInputException, MaxAddedCommunityException, NoSuchThingException
from models.group import Group
from models.channel import Channel, PostInterval



botman = BotMan()

async def show_market_types(update: Update, context: CallbackContext, next_state: Account.States):
    account = Account.Get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    account.change_state(next_state)
    await update.message.reply_text(botman.text('which_market', account.language),
                                    reply_markup=botman.markets_menu(account.language))


async def prepare_market_selection_menu(update: Update, context: CallbackContext, market: MarketOptions):
    account = Account.Get(update.message.chat)
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
    acc = Account.Get(update.message.chat)
    # get old or create new account => automatically will be added to Account.Instances
    if not await botman.has_subscribed_us(acc.chat_id, context):
        return await botman.ask_for_subscription(update, acc.language)
    await update.message.reply_text((botman.text('welcome_user', acc.language) % (update.message.chat.first_name,)) + "\n\n" + botman.text('select_bot_language', acc.language),
                                    reply_markup=botman.action_inline_keyboard(BotMan.QueryActions.CHOOSE_LANGUAGE, {'fa': 'language_persian', 'en': 'language_english'}, language=acc.language))


async def cmd_get_prices(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        return await botman.ask_for_subscription(update, account.language)

    is_latest_data_valid = botman.currency_serv and botman.currency_serv.latest_data and botman.crypto_serv \
                           and botman.crypto_serv.latest_data and botman.is_main_plan_on
    message = await botman.postman.create_post(desired_coins=account.desired_cryptos,
                                               desired_currencies=account.desired_currencies, for_channel=False,
                                               exactly_right_now=not is_latest_data_valid)

    await update.message.reply_text(message)


async def cmd_equalizer(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
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
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

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


async def cmd_premium_plan(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

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
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    current_jobs = context.job_queue.get_jobs_by_name(botman.main_queue_id)
    for job in current_jobs:
        job.schedule_removal()
    botman.is_main_plan_on = False
    botman.crypto_serv.latest_prices = ''
    await update.message.reply_text(botman.text('channel_planning_stopped', account.language))


async def cmd_change_source_to_coingecko(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    botman.crypto_serv = CoinGeckoService()
    await update.message.reply_text('منبع قیمت ها به کوین گکو نغییر یافت.')
    await notify_source_change(context)


async def cmd_change_source_to_coinmarketcap(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    botman.crypto_serv = CoinMarketCapService(botman.postman.coinmarketcap_api_key)
    await update.message.reply_text('منبع قیمت ها به کوین مارکت کپ نغییر یافت.')
    await notify_source_change(context)


async def cmd_admin_login(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    await update.message.reply_text(
        'اکانت شما به عنوان ادمین تایید اعتبار شد و می توانید از امکانات ادمین استفاده کنید.',
        reply_markup=botman.get_admin_keyboard(account.language))

async def cmd_upgrade_user(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)
    account.change_state(Account.States.UPGRADE_USER, clear_cache=True)
    await update.message.reply_text(botman.text("specify_user", account.language),
        reply_markup=botman.get_admin_keyboard(account.language))


async def cmd_list_users_to_downgrade(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    account.change_state(Account.States.DOWNGRADE_USER)
    await update.message.reply_text(botman.text('specify_user', account.language) + "\n" + botman.text('downgrade_by_premiums_list', account.language), reply_markup=botman.cancel_menu(account.language))
    await botman.list_premiums(update, BotMan.QueryActions.ADMIN_DOWNGRADE_USER)

async def cmd_send_post(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not account.authorization(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account.language)

    account.change_state(Account.States.SEND_POST)
    await update.message.reply_text('''🔹 پست خود را ارسال کنید:
(این پست برای تمامی کاربران ربات ارسال میشود و بعد از ۴۸ ساعت پاک خواهد شد)''',
                                    reply_markup=botman.cancel_menu[account.language])


async def cmd_report_statistics(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
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
            try:
                if unit in botman.crypto_serv.CoinsInPersian:
                    response = botman.create_crypto_equalize_message(unit, amount, 
                                                        account.calc_cryptos, account.calc_currencies, account.language)
                else:
                    response = botman.create_currency_equalize_message(unit, amount, 
                                                account.calc_cryptos, account.calc_currencies, account.language)
                await func_send_message(response)
            except ValueError as ex:
                log('Error while equalizing', ex, category_name='Calculator')
                await func_send_message(botman.error('price_not_available', account.language) % (unit, ))
            except NoLatestDataException:
                await func_send_message(botman.error('api_not_available', account.language))
            except InvalidInputException:
                await func_send_message(botman.error('invalid_symbol', account.language) % (unit, ))

    account.change_state(Account.States.INPUT_EQUALIZER_AMOUNT, clear_cache=True)  # prepare for next input
    await func_send_message(botman.text('continues_calculator_hint', account.language), reply_markup=botman.cancel_menu(account.language))

async def list_user_alarms(update: Update | CallbackQuery, context: CallbackContext):
    account = Account.Get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    my_alarms = PriceAlarm.get_alarms(account.chat_id)
    alarms_count = len(my_alarms)
    descriptions: List[str | None] = [None] * alarms_count
    buttons: List[InlineKeyboardButton | None] = [None] * alarms_count

    for i, alarm in enumerate(my_alarms):
        index = i+1
        try:
            curreny_title = alarm.currency.upper()
            price = cut_and_separate(alarm.target_price)

            if account.language == 'fa':
                index = persianify(index)
                price = persianify(price)
                curreny_title = botman.crypto_serv.CoinsInPersian[curreny_title] if curreny_title in botman.crypto_serv.CoinsInPersian else botman.currency_serv.CurrenciesInPersian[curreny_title]
                unit = botman.text(f'price_unit_{alarm.target_unit.lower()}', account.language)
            descriptions[i] = f"{index}) {curreny_title}: {price} {unit}"
        except:
            descriptions[i] = f"{index}) " + botman.error('invalid_alarm_data', account.language)
        buttons[i] = InlineKeyboardButton(descriptions[i], callback_data=botman.action_callback_data(BotMan.QueryActions.DISABLE_ALARM, alarm.id))

    if account.language == 'fa':
        alarms_count = persianify(alarms_count)
    message_text = botman.text('u_have_n_alarms', account.language) % (str(alarms_count), ) \
        + ((":\n\n" + "\n".join(descriptions) + "\n\n" + botman.text('click_alarm_to_disable', account.language)) if my_alarms else ".")
    
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(message_text, reply_markup=InlineKeyboardMarkup([[col] for col in buttons]))
        return
    await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup([[col] for col in buttons]))


async def send_r_u_sure_to_downgrade_message(context: CallbackContext, admin_user: Account, target_user: Account):
    await context.bot.send_message(chat_id=admin_user.chat_id, 
                        text=target_user.user_detail + "\n\n" + botman.text('r_u_sure_to_downgrade', admin_user.language), 
                        reply_markup=botman.action_inline_keyboard(BotMan.QueryActions.ADMIN_DOWNGRADE_USER, {
                            f"{target_user.chat_id}{botman.CALLBACK_DATA_JOINER}y": "yes",
                            f"{target_user.chat_id}{botman.CALLBACK_DATA_JOINER}n": "no"
                        }
    ))

async def handle_action_queries(query: CallbackQuery, context: CallbackContext, account: Account, callback_data: dict | None = None):
    action = None
    value = None

    if callback_data:
        callback_data = json.loads(str(query.data))
        action = callback_data['act'] 
        value = callback_data['v']

    if callback_data and isinstance(value, str) and value and value[0] == '!':
        params = value.split()
        message_id: int | None = None
        try:
            message_id = int(params[-1])
        except:
            pass
        if query.message:
            await query.message.delete()

        return await context.bot.delete_message(chat_id=account.chat_id, message_id=message_id) if message_id else None

    match action:
        case BotMan.QueryActions.CHOOSE_LANGUAGE.value:
            if not value:
                await query.delete_message()
                return
            lang = value
            if lang != 'fa' and lang != 'en':
                await query.answer(text=botman.error('invalid_language', account.language), show_alert=True)
                return
            account.language = lang
            account.save()
            await context.bot.send_message(text=botman.text('language_switched', account.language), chat_id=account.chat_id, reply_markup=botman.mainkeyboard(account))
        case BotMan.QueryActions.SELECT_PRICE_UNIT.value:
            if value:
                value = value.split(botman.CALLBACK_DATA_JOINER)
                market = MarketOptions.Which(int(value[0]))
                symbol = value[1]
                target_price = float(value[2])
                price_unit = value[3]
                current_price: float | None = None
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

                if current_price is not None:
                    if account.can_create_new_alarm:
                        alarm = PriceAlarm(account.chat_id, symbol, target_price=target_price, target_unit=price_unit, current_price=current_price)
                        alarm.set()
                        price_unit_str = botman.text(f'price_unit_{price_unit.lower()}', language=account.language)
                        current_price = cut_and_separate(target_price)
                        lang = account.language
                        if lang == 'fa':
                            current_price = persianify(current_price)
                        await query.message.edit_text(text=botman.text('alarm_set', lang) % (currency_name if lang == 'fa' else symbol, target_price, price_unit_str))
                    else:
                        await botman.show_reached_max_error(query, account, account.max_alarms_count)

        case BotMan.QueryActions.DISABLE_ALARM.value:
            alarm_id: int | None = None
            try:
                alarm_id = int(value)
                PriceAlarm.DisableById(alarm_id)
                await list_user_alarms(query, context)
            except Exception as ex:
                await context.bot.send_message(chat_id=account.chat_id, text=botman.error('error_while_disabling_alarm', account.language))
                log(f'Cannot disable the alarm with id={alarm_id}', ex, "Alarms")
        case BotMan.QueryActions.FACTORY_RESET.value:
            try:
                if value is not None and value.lower() == 'y':
                    account.factory_reset()
                    await query.message.delete()
                    await context.bot.send_message(chat_id=account.chat_id, text=botman.text('factory_reset_successful', account.language), reply_markup=botman.mainkeyboard(account))
            except Exception as ex:
                await query.message.edit_text(text=botman.error('factory_reset_incomplete', account.language))
                log(f'User {account.chat_id} factory reset failed!', ex, 'FactoryReset')
        case BotMan.QueryActions.SELECT_TUTORIAL.value:
            import resources.longtext as long_texts
            await query.message.edit_text(text=long_texts.TUTORIALS_TEXT[value][account.language])
            return
        case BotMan.QueryActions.SELECT_POST_INTERVAL.value: 
            await botman.handle_interval_input(query, context, value)
            await query.message.delete()
            account.change_state(clear_cache=True)
            return

        case BotMan.QueryActions.START_CHANNEL_POSTING.value:
            channel = Channel.Get(value)
            if not channel:
                await query.message.reply_text(botman.error('error_while_planning_channel', account.language), reply_markup=botman.mainkeyboard(account))  
                await query.message.delete()
                return
            channel.plan()  # TODO: check this again
            await query.message.reply_text(botman.text('channel_posting_started', account.language), reply_markup=botman.mainkeyboard(account))
            await query.message.delete()
            # TODO: Write the post job part.
        case _:
            if not account.authorization(context.args):
                await query.message.edit_text(botman.error('what_the_fuck', account.language))
                await context.bot.send_message(chat_id=account.chat_id, text=botman.text('what_can_i_do', account.language),
                                                reply_markup=botman.mainkeyboard(account))  # to hide admin keyboard if it's shown by mistake
                return
            
            # if admin:
            match action:
                case BotMan.QueryActions.ADMIN_DOWNGRADE_USER.value:
                    if 'v' not in callback_data or not value:
                        page: int

                        try:
                            page = int(callback_data['pg'])
                            # if previous line passes ok, means the value is as #Num and indicates the page number and is sending prev/next page signal
                            if page == -1 or callback_data['pg'] is None:
                                account.change_state(clear_cache=True)
                                await query.message.edit_text(botman.text('list_updated', account.language))
                                await context.bot.send_message(chat_id=account.chat_id, text=botman.text('what_can_i_do', account.language), reply_markup=botman.mainkeyboard(account))
                                return
                            menu = botman.users_list_menu(Account.GetPremiumUsers(), BotMan.QueryActions.ADMIN_DOWNGRADE_USER, columns_in_a_row=3, page=page, language=account.language)
                            await query.message.edit_reply_markup(reply_markup=menu)
                        except:
                            page = 0

                        return

                    chat_id: int | None = None
                    values = str(value).split(botman.CALLBACK_DATA_JOINER)
                    try:
                        chat_id = int(values[0])
                    except:
                        pass
                    if not chat_id:
                        await query.message.edit_text(botman.error('invalid_user_specification', account.language))
                        return
                    target_user = Account.GetById(chat_id)
                    if len(values) > 1:
                        if values[1] == 'y':
                            if target_user.is_premium:
                                target_user.downgrade()
                                await query.message.edit_text(botman.text('account_downgraded', account.language))
                                return
                            await query.message.edit_text(botman.text('not_a_premium', account.language))
                        else:
                            await query.message.edit_text(botman.text('operation_canceled', account.language))
                        # downgrade user
                    else:
                        await send_r_u_sure_to_downgrade_message(context, account, target_user)

    await query.answer()

async def handle_inline_keyboard_callbacks(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query.data:
        return

    data = json.loads(query.data)
    account: Account = Account.Get(query.message.chat)
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
                await start_equalizing(query.message.reply_text,
                                       account, input_amounts, [unit_symbol])
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
            
            if current_price_description:
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
        await botman.show_reached_max_error(query, account, max_selection)

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
    acc = Account.Get(update.message.chat)
    acc.language = "en" if acc.language == 'fa' else 'fa'
    await update.message.reply_text(botman.text('language_switched', acc.language))
    acc.save()

async def list_type_is_selected(update: Update):
    account = Account.Get(update.message.chat)
    if account.state not in [Account.States.CONFIG_CALCULATOR_LIST, Account.States.INPUT_EQUALIZER_UNIT, Account.States.CONFIG_MARKETS, Account.States.CREATE_ALARM]:
        await update.message.reply_text(botman.error('list_type_not_specified', account.language), reply_markup=botman.mainkeyboard(account))
        return False
    return True


# premiums:
async def cmd_start_using_in_channel(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    account.change_state(Account.States.ADD_BOT_AS_ADMIN, clear_cache=True)
    await update.message.reply_text(botman.text('add_bot_as_channel_admin', account.language), reply_markup=botman.cancel_menu(account.language))

async def unknown_command_handler(update: Update, context: CallbackContext):
    account = Account.Get(update.message.chat)
    await update.message.reply_text(botman.error('what_the_fuck', account.language),
                                               reply_markup=botman.mainkeyboard(account))

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
        case BotMan.Commands.CALCULATOR_FA.value | BotMan.Commands.CALCULATOR_EN.value:
            await cmd_equalizer(update, context)
        case BotMan.Commands.MY_CHANNELS_FA.value | BotMan.Commands.MY_CHANNELS_EN.value:
            account = Account.Get(update.message.chat)
            if not account.has_channels:
                await cmd_start_using_in_channel(update, context)
                return
            account.add_cache('community_type', botman.ChatType.CHANNEL)
            await update.message.reply_text(botman.resourceman.keyboard('my_channels', account.language) if account.is_premium else botman.text("go_premium_to_activate_feature", account.language),
                                            reply_markup=botman.get_community_config_keyboard(botman.ChatType.CHANNEL, account.language))
        case BotMan.Commands.MY_GROUPS_FA.value | BotMan.Commands.MY_GROUPS_EN.value:
            account = Account.Get(update.message.chat)
            if not account.has_groups:
                await update.message.reply_text(botman.text('add_bot_as_group_admin', Account.Get(update.message.chat).language))
                return
            account.add_cache('community_type', botman.ChatType.GROUP)
            await update.message.reply_text(botman.resourceman.keyboard('my_groups', account.language) if account.is_premium else botman.text("go_premium_to_activate_feature", account.language),
                                            reply_markup=botman.get_community_config_keyboard(botman.ChatType.GROUP, account.language))
        case BotMan.Commands.SETTINGS_FA.value | BotMan.Commands.SETTINGS_EN.value:
            await update.message.delete()
            await botman.show_settings_menu(update)


        # Select market sub menu
        case BotMan.Commands.CRYPTOS_FA.value | BotMan.Commands.CRYPTOS_EN.value:
            if await list_type_is_selected(update):
                await select_coin_menu(update, context)
        case BotMan.Commands.NATIONAL_CURRENCIES_FA.value | BotMan.Commands.NATIONAL_CURRENCIES_EN.value:
            if await list_type_is_selected(update):
                await select_currency_menu(update, context)
        case BotMan.Commands.GOLDS_FA.value | BotMan.Commands.GOLDS_EN.value:
            if await list_type_is_selected(update):
                await select_gold_menu(update, context)

        # community sub menu:
        case BotMan.Commands.CHANNELS_CHANGE_INTERVAL_FA.value | BotMan.Commands.CHANNELS_CHANGE_INTERVAL_EN.value:
            account = Account.Get(update.message.chat)
            channel = Channel.GetByOwner(account.chat_id)
            if not channel:
                await update.message.reply_text(botman.error('no_channels', account.language), reply_markup=botman.mainkeyboard(account))
                return
            await botman.select_post_interval_menu(update, account, channel.id, Account.States.CHANGE_POST_INTERVAL)
        # settings sub menu:
        case BotMan.Commands.SET_BOT_LANGUAGE_FA.value | BotMan.Commands.SET_BOT_LANGUAGE_EN.value:
                account = Account.Get(update.message.chat)
                if not await botman.has_subscribed_us(account.chat_id, context):
                    await botman.ask_for_subscription(update, account.language)
                    return
                await update.message.reply_text(botman.text('select_bot_language', account.language),
                                                reply_markup=botman.action_inline_keyboard(BotMan.QueryActions.CHOOSE_LANGUAGE, 
                                                    {'fa': 'language_persian', 'en': 'language_english', 0: 'close'}, language=account.language))
        case BotMan.Commands.FACTORY_RESET_FA.value | BotMan.Commands.FACTORY_RESET_EN.value:
            account = Account.Get(update.message.chat)
            await update.message.reply_text(botman.text('factory_reset_confirmation', account.language),
                                reply_markup=botman.action_inline_keyboard(BotMan.QueryActions.FACTORY_RESET, 
                                    {'y': 'factory_reset'}, language=account.language))
            
        case BotMan.Commands.SUPPORT_FA.value | BotMan.Commands.SUPPORT_EN.value:
            await update.message.reply_text(botman.text('contact_support_hint') % (Account.GetHardcodeAdmin()['username']))
        case BotMan.Commands.OUR_OTHERS_FA.value | BotMan.Commands.OUR_OTHERS_EN.value:
            await update.message.reply_text(botman.text('check_our_other_collections'))
        case BotMan.Commands.TUTORIALS_FA.value | BotMan.Commands.TUTORIALS_EN.value:
            account = Account.Get(update.message.chat)
            await update.message.reply_text(botman.text('click_tutorial_u_need', account.language),
                                            reply_markup=botman.action_inline_keyboard(botman.QueryActions.SELECT_TUTORIAL, {
                                                'config_lists': 'config_lists',
                                                'get_prices': "get_prices",
                                                'config_calculator': 'config_calculator',
                                                'calculator': 'calculator',
                                                'list_alarms': 'list_alarms',
                                                'create_alarm': 'create_alarm',
                                                'use_in_channel': 'use_in_channel',
                                                'use_in_group': 'use_in_group',
                                                f'! {update.message.message_id}': 'close'
                                            }, language=account.language, in_main_keyboard=True))

        # cancel/return options
        case BotMan.Commands.CANCEL_FA.value | BotMan.Commands.CANCEL_EN.value:
            account = Account.Get(update.message.chat)
            account.change_state(clear_cache=True)  # reset .state and .state_data
            await update.message.reply_text(botman.text('operation_canceled', account.language),
                                            reply_markup=botman.mainkeyboard(account))
        case BotMan.Commands.RETURN_FA.value | BotMan.Commands.RETURN_EN.value:
            account = Account.Get(update.message.chat)
            account.change_state(clear_cache=True)
            await update.message.reply_text(botman.text('what_can_i_do', account.language), reply_markup=botman.mainkeyboard(account))
        
        # special states
        case _:
            # check account state first, to see if he/she is in input state
            account = Account.Get(update.message.chat)
            msg = update.message.text

            if account.is_admin:
                # admin options:
                match msg:
                    case BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_FA.value | BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_EN.value:
                        await cmd_upgrade_user(update, context)
                        return
                    case BotMan.Commands.ADMIN_DOWNGRADE_USER_FA.value | BotMan.Commands.ADMIN_DOWNGRADE_USER_EN.value:
                        await cmd_list_users_to_downgrade(update, context)
                        return
                    case BotMan.Commands.ADMIN_NOTICES_FA.value | BotMan.Commands.ADMIN_NOTICES_EN.value:
                        await cmd_send_post(update, context)
                        return
                    case BotMan.Commands.ADMIN_PLAN_CHANNEL_FA.value | BotMan.Commands.ADMIN_PLAN_CHANNEL_EN.value:
                        await cmd_schedule_channel_update(update, context)
                        return
                    case BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_FA.value | BotMan.Commands.ADMIN_STOP_CHANNEL_PLAN_EN.value:
                        await cmd_stop_schedule(update, context)
                        return
                    case BotMan.Commands.ADMIN_STATISTICS_FA.value | BotMan.Commands.ADMIN_STATISTICS_EN.value:
                        await cmd_report_statistics(update, context)
                        return

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
                        account.change_state(Account.States.INPUT_EQUALIZER_UNIT, 'input_amounts', amounts)
                        await show_market_types(update, context, Account.States.INPUT_EQUALIZER_UNIT)
                    else:
                        await start_equalizing(update.message.reply_text, account, amounts, units)
                        
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

                case Account.States.ADD_BOT_AS_ADMIN:  # TODO: Add code to automatically add channel, just like groups
                    channel_chat_id: int | None = None
                    if update.message.forward_from_chat:
                        channel_chat_id = update.message.forward_from_chat.id
                    else:
                        try:
                            channel_chat_id = int(msg)
                        except:
                            pass

                    if not channel_chat_id:
                        # send a message to the channel or group and retrieve chat_id
                        try:
                            response = await context.bot.send_message(chat_id=msg, text='Test')
                            channel_chat_id = response.chat.id

                            await context.bot.delete_message(chat_id=channel_chat_id, message_id=response.message_id)
                        except:
                            await update.message.reply_text(botman.error('bot_seems_not_admin', account.language), reply_markup=botman.action_inline_keyboard(botman.QueryActions.VERIFY_BOT_IS_ADMIN, {
                                msg: 'verify'
                            }, in_main_keyboard=False))

                    if channel_chat_id:
                        await botman.select_post_interval_menu(update, account, channel_chat_id, Account.States.SELECT_POST_INTERVAL)
                case Account.States.SELECT_POST_INTERVAL | Account.States.CHANGE_POST_INTERVAL:
                    interval: int = 0
                    try:
                        interval = PostInterval.TimestampToMinutes(msg)
                    except:
                        await update.message.reply_text(botman.error('unsupported_input_format', account.language))
                        return
                    await botman.handle_interval_input(update, context, interval)
                    try:
                        await context.bot.delete_message(chat_id=account.chat_id, message_id=int(account.get_cache('interval_menu_msg_id')))
                    except:
                        pass
                    account.change_state(clear_cache=True)
                case _:
                    if not account.authorization(context.args):
                        await update.message.reply_text(botman.error('what_the_fuck', account.language),
                                                    reply_markup=botman.mainkeyboard(account))
                        return

                    # Admin states
                    match account.state:
                        case Account.States.UPGRADE_USER:
                            upgrading_chat_id = account.get_cache('upgrading')
                            text = update.message.text
                            user: Account | None = None
                            if not upgrading_chat_id:
                                user = botman.identify_user(update)

                                if not user:
                                    await update.message.reply_text(botman.error('invalid_user_specification', account.language))
                                    return
                                account.add_cache('upgrading', user.chat_id)

                                await update.message.reply_text(user.user_detail)
                                await update.message.reply_text(botman.text('enter_upgrade_premium_duration', account.language))
                            else:
                                months: int | None = None
                                try:
                                    months = int(text)
                                except:
                                    months = None
                                if not months or (months < 0):
                                    await update.message.reply_text(botman.error('invalid_months_count', account.language))
                                    return
                                target = Account.GetById(upgrading_chat_id)
                                target.upgrade(months)
                                
                                await context.bot.send_message(chat_id=target.chat_id, text=botman.text('youre_upgraded_premium', target.language), reply_markup=botman.mainkeyboard(target))

                                await update.message.reply_text(botman.text('user_upgraded_premium', account.language), reply_markup=botman.mainkeyboard(account))
                                account.change_state(clear_cache=True)
                        case Account.States.DOWNGRADE_USER:
                            user = botman.identify_user(update)

                            if not user:
                                await update.message.reply_text(botman.error('invalid_user_specification', account.language))
                                return
                            await send_r_u_sure_to_downgrade_message(context, account, user)
                        case Account.States.SEND_POST:
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
                                reply_markup=botman.get_admin_keyboard(account.language))
                            account.change_state(clear_cache=True)  # reset .state and .state_data


async def handle_new_group_members(update: Update, context: CallbackContext):
    my_id = context.bot.id
    for member in update.message.new_chat_members:
        if member.id == my_id:
            owner = Account.GetById(group.owner_id)  # TODO: Use Join query if account is not in cache mem
            try:
                group = Group.Register(update.message.chat, update.message.from_user.id)

                if group.is_active:
                    await context.bot.send_message(chat_id=owner.chat_id, text=botman.text('group_is_active', owner.language) % (group.title,))
                else:
                    await context.bot.send_message(chat_id=owner.chat_id, text=botman.text('go_premium_for_group_activation', owner.language) % (group.title))
            except MaxAddedCommunityException:
                await context.bot.send_message(chat_id=owner.chat_id, text=botman.error('max_groups_reached', owner.language))
            return

async def handle_group_messages(update: Update, context: CallbackContext):
    crypto_amounts, currency_amounts = botman.extract_symbols_and_amounts(update.message.text)
    group: Group = Group.Get(update.message.chat.id)
    to_user: Account = Account.GetById(update.message.from_user.id)
    
    if not group.is_active:
        return
    
    for input_list in [(crypto_amounts, botman.create_crypto_equalize_message), (currency_amounts, botman.create_currency_equalize_message)]:
        inputs, equalizer_func = input_list
        for coef_n_unit in inputs:
            coef, unit = coef_n_unit.split()
            coef = botman.extract_coef(coef)
            message = equalizer_func(unit, coef, group.selected_coins, group.selected_currencies, to_user.language)
            await update.message.reply_text(message)


def main():
    app = BotApplicationBuilder().token(botman.token).build()

    app.add_handler(CommandHandler("start", cmd_welcome))
    app.add_handler(CommandHandler("get", cmd_get_prices))
    app.add_handler(CommandHandler("crypto", select_coin_menu))
    app.add_handler(CommandHandler("currency", select_currency_menu))
    app.add_handler(CommandHandler("gold", select_gold_menu))
    app.add_handler(CommandHandler("equalizer", cmd_equalizer))
    app.add_handler(CommandHandler("lang", cmd_switch_language))
    app.add_handler(CommandHandler("useinchannel", cmd_start_using_in_channel))

    # ADMIN SECTION
    app.add_handler(CommandHandler("god", cmd_admin_login))
    app.add_handler(CommandHandler("up", cmd_upgrade_user))
    app.add_handler(CommandHandler("down", cmd_list_users_to_downgrade))
    app.add_handler(CommandHandler("post", cmd_send_post))
    app.add_handler(CommandHandler("schedule", cmd_schedule_channel_update))
    app.add_handler(CommandHandler("stop", cmd_stop_schedule))
    app.add_handler(CommandHandler("stats", cmd_report_statistics))
    app.add_handler(CommandHandler("gecko", cmd_change_source_to_coingecko))
    app.add_handler(CommandHandler("marketcap", cmd_change_source_to_coinmarketcap))

    app.add_handler(CallbackQueryHandler(handle_inline_keyboard_callbacks))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_group_members))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND, handle_group_messages))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_messages))  # TODO: Is private filter required?
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command_handler))
    # app.add_error_handler() # TODO:Check this out

    print("Server is up and running...")
    app.run_polling(poll_interval=0.25, timeout=10)

    # Run as webhook
    # app.run_webhook(
    #     listen='127.0.0.1', 
    #     port=8000, 
    #     webhook_url='https://7490-2a05-f480-1c00-69d-5400-5ff-fe05-46a8.ngrok-free.app'
    # )


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        print(ex)
        log("Server crashed because: ", ex, 'FATALITY')
