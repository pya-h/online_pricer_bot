from telegram.ext import CallbackContext, Application as TelegramApplication

from telegram import (
    Update,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Chat,
    ReplyKeyboardRemove,
    ChatMemberMember,
)
from telegram.error import BadRequest, Forbidden
from models.account import Account
import json
from tools.manuwriter import log
from tools.mathematix import (
    cut_and_separate,
    persianify,
    n_days_later_timestamp,
    seconds_to_next_period,
    now_in_minute,
)
from bot.manager import BotMan
from bot.types import MarketOptions, SelectionListTypes
from api.crypto_service import CoinMarketCapService
from models.alarms import PriceAlarm
from typing import List
from tools.exceptions import (
    NoLatestDataException,
    InvalidInputException,
    MaxAddedCommunityException,
    NoSuchThingException,
)
from models.group import Group
from models.channel import Channel, PostInterval
from bot.post import PostMan
from bot.settings import BotSettings
import asyncio


botman = BotMan()


async def show_market_types(update: Update, context: CallbackContext, next_state: Account.States):
    account = Account.get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    account.change_state(next_state)
    await update.message.reply_text(
        botman.text("which_market", account.language),
        reply_markup=botman.markets_menu(account.language),
    )


async def prepare_market_selection_menu(update: Update, context: CallbackContext, market: MarketOptions):
    account = Account.get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    list_type: SelectionListTypes | None = account.match_state_with_selection_type()

    await update.message.reply_text(
        botman.text("select_your_set", account.language),
        reply_markup=botman.create_tokens_menu(
            list_type,
            market,
            (
                botman.crypto_serv.coinsInPersian
                if market == MarketOptions.CRYPTO
                else (
                    botman.currency_serv.nationalCurrenciesInPersian
                    if market == MarketOptions.CURRENCY
                    else botman.currency_serv.goldsInPersian
                )
            ),
            BotMan.handleMarketSelection(account, list_type, market),
            close_button=True,
            language=account.language,
            choices_start_offset=int(list_type.should_show_irt(market)),
        ),
    )


async def select_coin_menu(update: Update, context: CallbackContext):
    await prepare_market_selection_menu(update, context, MarketOptions.CRYPTO)


async def select_currency_menu(update: Update, context: CallbackContext):
    await prepare_market_selection_menu(update, context, MarketOptions.CURRENCY)


async def select_gold_menu(update: Update, context: CallbackContext):
    await prepare_market_selection_menu(update, context, MarketOptions.GOLD)


async def say_youre_not_allowed(reply, account: Account):
    await reply(
        botman.error("not_allowed", account.language),
        reply_markup=botman.get_normal_primary_keyboard(account),
    )


async def notify_source_change(context: CallbackContext):
    await context.bot.send_message(
        chat_id=botman.channels[0]["id"],
        text=botman.text("price_source_is_cmc"),  # for now only coin market cap is used as crypto source.
    )


async def update_markets(context: CallbackContext):
    # res = await botman.next_post()
    await botman.update_markets()
    await botman.handle_possible_alarms(context)


async def cmd_welcome(update: Update | CallbackQuery, context: CallbackContext):
    acc = Account.get(update.message.chat)
    # get old or create new account => automatically will be added to Account.Instances
    if not await botman.has_subscribed_us(acc.chat_id, context):
        return await botman.ask_for_subscription(update, acc.language)
    await update.message.reply_text(
        (botman.text("welcome_user", acc.language) % (update.message.chat.first_name,))
        + "\n\n"
        + botman.text("select_bot_language", acc.language),
        reply_markup=botman.action_inline_keyboard(
            BotMan.QueryActions.CHOOSE_LANGUAGE,
            {"fa": "language_persian", "EN-FA": "language_english"},
            language=acc.language,
        ),
    )


async def cmd_get_prices(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        return await botman.ask_for_subscription(update, account.language)
    is_latest_data_valid = (
        botman.currency_serv
        and botman.currency_serv.latest_data
        and botman.crypto_serv
        and botman.crypto_serv.latest_data
        and botman.is_main_plan_on
    )
    message = await botman.postman.create_post(
        desired_coins=account.desired_cryptos,
        desired_currencies=account.desired_currencies,
        get_most_recent_price=not is_latest_data_valid,
        language=account.language,
    )

    await update.message.reply_text(message, reply_markup=botman.mainkeyboard(account))


async def cmd_equalizer(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        return await botman.ask_for_subscription(update, account.language)

    account.change_state(Account.States.INPUT_EQUALIZER_AMOUNT)
    hint_examples = """1) 100 USD
2) 10 50 BTC TRX
3) 5 GOLD ETH EUR

"""
    await update.message.reply_text(
        botman.text("calculator_hint", account.language)
        + hint_examples
        + botman.text("calculator_hint_footnote", account.language),
        reply_markup=botman.return_menu(account.language),
    )


def plan_market_updates(context: CallbackContext | TelegramApplication, interval: float | int = 10):
    if botman.is_main_plan_on:
        raise InvalidInputException("Command; Channel already planned!")

    botman.is_main_plan_on = True
    # if (first_run_offset := seconds_to_next_period(interval) - 1) > 60 and (
    #     not botman.currency_serv.latest_data or not botman.crypto_serv.latest_data
    # ):
    #     asyncio.run(botman.next_post()) # FIXME: Fix this later its causing crash
    context.job_queue.run_repeating(
        update_markets,
        interval=interval * 60,
        first=seconds_to_next_period(interval) - 1,
        name=botman.main_queue_id,
    )


async def cmd_schedule_channel_update(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)

    try:
        if context.args:
            try:
                botman.main_plan_interval = int(context.args[-1])
            except ValueError:
                botman.main_plan_interval = float(context.args[-1])

    except Exception as e:
        log("Something went wrong while scheduling: ", e)

    try:
        plan_market_updates(context, botman.main_plan_interval)
        await update.message.reply_text(
            botman.text("channel_planning_started", account.language) % (botman.main_plan_interval,)
        )
    except InvalidInputException:
        await update.message.reply_text(botman.text("channel_already_planned", account.language))
    except Exception as x:
        await unhandled_error_happened(update, context)


async def cmd_stop_schedule(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)

    current_jobs = context.job_queue.get_jobs_by_name(botman.main_queue_id)
    for job in current_jobs:
        job.schedule_removal()
    botman.is_main_plan_on = False
    botman.crypto_serv.latest_prices = ""
    await update.message.reply_text(botman.text("channel_planning_stopped", account.language))


async def cmd_admin_login(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)

    await update.message.reply_text(
        botman.text("congrats_admin", account.language),
        reply_markup=botman.get_admin_primary_keyboard(account),
    )


async def cmd_upgrade_user(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_admin and not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    account.change_state(Account.States.UPGRADE_USER)
    account.delete_specific_cache("upgrading")
    await update.message.reply_text(
        botman.text("specify_user", account.language),
        reply_markup=botman.cancel_menu(account.language),
    )


async def cmd_add_admin(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    account.change_state(Account.States.ADD_ADMIN)

    await update.message.reply_text(
        botman.text("specify_user", account.language),
        reply_markup=botman.cancel_menu(account.language),
    )


async def cmd_remove_admin(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    admins = Account.getStaffAdmins()
    await update.message.reply_text(
        botman.text("remove_by_admin_list", account.language),
        reply_markup=botman.users_list_menu(
            admins,
            BotMan.QueryActions.REMOVE_ADMIN,
            columns_in_a_row=3,
            page=0,
            language=account.language,
        ),
    )


async def cmd_list_users_to_downgrade(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_admin and not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)

    await update.message.reply_text(
        botman.text("specify_user", account.language)
        + "\n"
        + botman.text("downgrade_by_premiums_list", account.language),
        reply_markup=botman.cancel_menu(account.language),
    )
    if await botman.list_premiums(update, BotMan.QueryActions.ADMIN_DOWNGRADE_PREMIUM_USER):
        account.change_state(Account.States.DOWNGRADE_USER)


async def cmd_send_post(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)

    account.change_state(Account.States.SEND_POST)
    await update.message.reply_text(
        botman.text("enter_remove_interval_in_days", account.language),
        reply_markup=botman.cancel_menu(account.language),
    )


async def cmd_report_statistics(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)

    reports = BotMan.collectBotStats(account.language)
    for report in reports:
        await update.message.reply_text(report, reply_markup=botman.get_admin_primary_keyboard(account))

    await update.message.reply_text(
        botman.text("u_can_list_entities", account.language),
        reply_markup=botman.action_inline_keyboard(
            BotMan.QueryActions.LIST_ENTITY,
            {
                f"{BotMan.CommunityType.GROUP.value}{BotMan.CALLBACK_DATA_DELIMITER}0": "groups_list",
                f"{BotMan.CommunityType.CHANNEL.value}{BotMan.CALLBACK_DATA_DELIMITER}0": "channels_list",
                f"{BotMan.CommunityType.NONE.value}{BotMan.CALLBACK_DATA_DELIMITER}0": "premiums_list",
            },
            account.language,
        ),
    )


async def cmd_send_plans_post(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    account.change_state(Account.States.CHANGE_PREMIUM_PLANS)
    await update.message.reply_text(
        botman.text("send_premium_plans_post", account.language),
        reply_markup=botman.cancel_menu(account.language),
    )


async def start_equalizing(func_send_message, account: Account, amounts: list, units: list):
    if not isinstance(botman.crypto_serv, CoinMarketCapService):
        await func_send_message(botman.error("only_available_on_cmc", account.language))
        return
    response: str
    tasks: List[Message] = []
    for amount in amounts:
        for unit in units:
            try:
                if unit in botman.crypto_serv.coinsInPersian:
                    response = botman.create_crypto_equalize_message(
                        unit,
                        amount,
                        account.calc_cryptos,
                        account.calc_currencies,
                        account.language,
                    )
                else:
                    response = botman.create_currency_equalize_message(
                        unit,
                        amount,
                        account.calc_cryptos,
                        account.calc_currencies,
                        account.language,
                    )
                tasks.append(func_send_message(response))
            except ValueError as value_x:
                log("Error while equalizing", value_x, category_name="Equalizer")
                tasks.append(func_send_message(botman.error("price_not_available", account.language) % (unit,)))
            except NoLatestDataException:
                tasks.append(func_send_message(botman.error("api_not_available", account.language)))
            except InvalidInputException:
                tasks.append(func_send_message(botman.error("invalid_symbol", account.language) % (unit,)))
            except Exception as x:
                log("Error while equalizing", x, category_name="Equalizer")
                tasks.append(func_send_message(botman.error("unknown", account.language)))
                account.change_state()
    await asyncio.gather(*tasks, return_exceptions=True)
    account.change_state(Account.States.INPUT_EQUALIZER_AMOUNT)
    account.delete_specific_cache("input_amounts", "input_symbols")
    await func_send_message(
        botman.text("continues_calculator_hint", account.language),
        reply_markup=botman.return_menu(account.language),
    )


async def list_user_alarms(update: Update | CallbackQuery, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not await botman.has_subscribed_us(account.chat_id, context):
        await botman.ask_for_subscription(update, account.language)
        return
    my_alarms: List[PriceAlarm] = PriceAlarm.getUserAlarms(account.chat_id)
    alarms_count = len(my_alarms)
    descriptions: List[str | None] = [None] * alarms_count
    buttons: List[InlineKeyboardButton | None] = [None] * alarms_count
    next_alarm_text: str = ""
    for i, alarm in enumerate(my_alarms):
        index = i + 1
        try:
            currency_title = alarm.token.upper()
            price = cut_and_separate(alarm.target_price)

            if account.language == "fa":
                index = persianify(index)
                price = persianify(price)
                currency_title = (
                    botman.crypto_serv.coinsInPersian[currency_title]
                    if alarm.market == MarketOptions.CRYPTO
                    else botman.currency_serv.currenciesInPersian[currency_title]
                )
            unit = botman.text(
                f"price_unit_{alarm.target_unit}",
                "fa" if account.language == "fa" else "en",
            )
            next_alarm_text = f"{index}) {currency_title}: {price} {unit}"
            descriptions[i] = f"🚨 {next_alarm_text}"
        except:
            next_alarm_text = f"{index}) " + botman.error("invalid_alarm_data", account.language)
            descriptions[i] = f"❗️ {next_alarm_text}"
        buttons[i] = InlineKeyboardButton(
            f"❌ {next_alarm_text}",
            callback_data=botman.actionCallbackData(BotMan.QueryActions.DISABLE_ALARM, alarm.id),
        )

    if account.language == "fa":
        alarms_count = persianify(alarms_count)
    message_text = (
        (
            botman.text("u_have_n_alarms", account.language) % (str(alarms_count),)
            + (
                (":\n\n" + "\n".join(descriptions) + "\n\n" + botman.text("click_alarm_to_disable", account.language))
                if my_alarms
                else "."
            )
        )
        if alarms_count
        else botman.text("u_have_no_alarms", account.language)
    )

    if isinstance(update, CallbackQuery):
        await update.message.edit_text(message_text, reply_markup=InlineKeyboardMarkup([[col] for col in buttons]))
        return
    await update.message.reply_text(message_text, reply_markup=InlineKeyboardMarkup([[col] for col in buttons]))


async def send_r_u_sure_to_downgrade_message(context: CallbackContext, admin_user: Account, target_user: Account):
    await context.bot.send_message(
        chat_id=admin_user.chat_id,
        text=target_user.user_detail + "\n\n" + botman.text("r_u_sure_to_downgrade", admin_user.language),
        reply_markup=botman.action_inline_keyboard(
            BotMan.QueryActions.ADMIN_DOWNGRADE_PREMIUM_USER,
            {
                f"{target_user.chat_id}{BotMan.CALLBACK_DATA_DELIMITER}y": "yes",
                f"{target_user.chat_id}{BotMan.CALLBACK_DATA_DELIMITER}n": "no",
            },
        ),
    )


async def handle_action_queries(
    query: CallbackQuery,
    context: CallbackContext,
    account: Account,
    callback_data: dict | None = None,
):
    action = None
    value = None

    if callback_data:
        callback_data = json.loads(str(query.data))
        action = callback_data["act"]
        value = callback_data["v"]

    if callback_data and isinstance(value, str) and value and value[0] == "!":
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

            if value == "EN-FA":
                await query.message.edit_text(
                    text=botman.text("which_english_language_state_u_prefer", account.language),
                    reply_markup=botman.action_inline_keyboard(
                        BotMan.QueryActions.CHOOSE_LANGUAGE,
                        {"FA": "just_english_tokens", "en": "whole_bot"},
                        language=account.language,
                    ),
                )
                return
            if value.lower() != "fa" and value != "en":
                await query.answer(
                    text=botman.error("invalid_language", account.language),
                    show_alert=True,
                )
                return

            BotMan.updateUserLanguage(account, value)
            await context.bot.send_message(
                text=botman.resourceman.text_for_case_sensitive_key("language_switched", account.language),
                chat_id=account.chat_id,
                reply_markup=botman.mainkeyboard(account),
            )

        case BotMan.QueryActions.SELECT_PRICE_UNIT.value:
            if value:
                value = value.split(BotMan.CALLBACK_DATA_DELIMITER)
                market = MarketOptions.which(int(value[0]))
                symbol = value[1]
                target_price = float(value[2])
                price_unit = value[3]
                current_price: float | None = None
                currency_name: str | None = None
                try:
                    currency_name, current_price = botman.get_token_state(market, symbol, price_unit)
                except Exception as alarm_ex:
                    log(f"Cannot create the alarm for user {account.chat_id}", alarm_ex)

                if current_price is not None:
                    if account.can_create_new_alarm:
                        alarm = PriceAlarm(
                            account.chat_id,
                            symbol,
                            target_price=target_price,
                            target_unit=price_unit,
                            current_price=current_price,
                            market=market,
                        )

                        alarm.set()
                        price_unit_str = botman.text(
                            f"price_unit_{price_unit.lower()}",
                            language=account.language,
                        )
                        target_price = cut_and_separate(target_price)

                        if account.language == "fa":
                            target_price = persianify(target_price)
                        else:
                            currency_name = symbol
                        await query.message.edit_text(
                            text=botman.text("alarm_set", account.language)
                            % (
                                currency_name,
                                target_price,
                                price_unit_str,
                            )
                        )
                    else:
                        await botman.show_reached_max_error(query, account, account.max_alarms_count, "alarms")

                await query.message.reply_text(
                    botman.text("what_can_i_do", account.language),
                    reply_markup=botman.mainkeyboard(account),
                )

        case BotMan.QueryActions.DISABLE_ALARM.value:
            alarm_id: int | None = None
            try:
                alarm_id = int(value)
                PriceAlarm.disableById(alarm_id)
                await list_user_alarms(query, context)
            except Exception as alarm_ex:
                await context.bot.send_message(
                    chat_id=account.chat_id,
                    text=botman.error("error_while_disabling_alarm", account.language),
                )
                log(f"Cannot disable the alarm with id={alarm_id}", alarm_ex, "Alarms")
        case BotMan.QueryActions.FACTORY_RESET.value:
            try:
                if value is not None and value.lower() == "y":
                    BotMan.factoryResetAccount(account)
                    await asyncio.gather(
                        query.message.delete(),
                        context.bot.send_message(
                            chat_id=account.chat_id,
                            text=botman.text("factory_reset_successful", account.language),
                            reply_markup=botman.mainkeyboard(account),
                        ),
                        return_exceptions=True,
                    )
            except Exception as alarm_ex:
                await query.message.edit_text(text=botman.error("factory_reset_incomplete", account.language))
                log(
                    f"User {account.chat_id} factory reset failed!",
                    alarm_ex,
                    "FactoryReset",
                )
        case BotMan.QueryActions.SELECT_TUTORIAL.value:
            await query.message.edit_text(text=BotMan.getLongText(value, account.language))
            return
        case BotMan.QueryActions.SELECT_POST_INTERVAL.value:
            if await botman.handle_set_interval_outcome(query, context, value):
                account.change_state(clear_cache=True)
                await query.message.delete()
            return

        case BotMan.QueryActions.START_CHANNEL_POSTING.value:
            try:
                channel = Channel.get(value)
                if not channel:
                    raise Exception()
                if not account.is_premium:
                    await botman.send_message_with_premium_button(
                        query,
                        botman.text("go_premium_to_activate_feature", account.language),
                        language=account.language,
                    )
                    await query.answer()
                    return
                channel.plan()  # TODO: check this again
                await asyncio.gather(
                    query.message.reply_text(
                        botman.text("channel_posting_started", account.language),
                        reply_markup=botman.mainkeyboard(account),
                    ),
                    query.message.delete(),
                    return_exceptions=True,
                )
            except:
                await asyncio.gather(
                    query.message.reply_text(
                        botman.error("error_while_planning_channel", account.language),
                        reply_markup=botman.mainkeyboard(account),
                    ),
                    query.message.delete(),
                    return_exceptions=True,
                )

        case BotMan.QueryActions.TRIGGER_DATE_TAG.value | BotMan.QueryActions.TRIGGER_MARKET_TAGS.value:
            try:
                community_type, enable = value.split(BotMan.CALLBACK_DATA_DELIMITER)
                if not community_type or not enable:
                    raise InvalidInputException("Invalid callback data.")
                community_type, enable = int(community_type), int(enable)
                community = BotMan.getCommunity(community_type, account.chat_id)
                if not community:
                    raise NoSuchThingException(-1, BotMan.CommunityType.toString(community_type))
                if action == BotMan.QueryActions.TRIGGER_DATE_TAG.value:
                    community.message_show_date_tag = bool(enable)
                else:
                    community.message_show_market_tags = bool(enable)
                community.save()
                await query.message.edit_text(botman.text("update_successful", account.language))
            except NoSuchThingException as x:
                await query.message.edit_text(
                    botman.error(f"no_{x.thing}s", account.language),
                )
                account.delete_specific_cache("community")
            except:
                await query.message.edit_text(botman.error("unexpected_error", account.language))
        case BotMan.QueryActions.UPDATE_MESSAGE_SECTIONS.value | BotMan.QueryActions.DISCONNECT_COMMUNITY.value:
            if not value:
                await query.message.edit_text(botman.text("operation_canceled", account.language))
                account.change_state()
                return
            params = value.split(BotMan.CALLBACK_DATA_DELIMITER)
            community_type = BotMan.CommunityType.which(int(params[0]))
            if not community_type:
                await query.message.edit_text(botman.text("data_invalid", account.language))
                account.delete_specific_cache("community", "msg2delete")
                return

            if not (community := community_type.to_class().getByOwner(account.chat_id)):
                await asyncio.gather(
                    query.message.reply_text(
                        botman.error(f"no_{community.__str__()}", account.language),
                        reply_markup=botman.mainkeyboard(account),
                    ),
                    query.message.delete(),
                    return_exceptions=True,
                )
                account.delete_specific_cache("community", "msg2delete")
                return
            if action == BotMan.QueryActions.UPDATE_MESSAGE_SECTIONS.value:
                if (section := params[1].lower()) != "footer" and section != "header":
                    await query.message.edit_text(botman.error("data_invalid", account.language))
                    return

                if section != "footer":
                    community.message_header = None
                else:
                    community.message_footnote = None
                community.save()
                account.change_state()
                await query.message.edit_text(botman.text("update_successful", account.language))
            else:
                try:
                    community_id = int(params[1])
                    if community_id != community.id:
                        await query.message.edit_text(
                            botman.error(
                                f"{community.__str__()}_not_yours_anymore",
                                account.language,
                            )
                        )
                        return
                    community.throw_in_trashcan()
                    if community.delete():
                        await query.message.edit_text(
                            botman.text("successfully_disconnected", account.language),
                            reply_markup=botman.action_inline_keyboard(
                                BotMan.QueryActions.REQUEST_RECONNECT_COMMUNITY,
                                {value: "reconnect"},
                                account.language,
                                columns_in_a_row=1,
                            ),
                        )
                        return
                except Exception as x:
                    log(
                        f"Disconnecting {community.__str__()} failed, callback_data={value}",
                        x,
                        category_name="Community",
                    )
                await query.message.edit_text(botman.error("data_invalid", account.language))
        case BotMan.QueryActions.REQUEST_RECONNECT_COMMUNITY.value | BotMan.QueryActions.RECONNECT_COMMUNITY.value:
            if not value and (action == BotMan.QueryActions.RECONNECT_COMMUNITY.value):
                await query.message.edit_text(botman.text("operation_canceled", account.language))
                return
            params = value.split(BotMan.CALLBACK_DATA_DELIMITER)
            if (
                not params
                or (len(params) < 2)
                or (not (community_type := BotMan.CommunityType.which(int(params[0]))).value)
            ):
                await query.message.edit_text(botman.error("data_invalid", account.language))
                return

            if action == BotMan.QueryActions.REQUEST_RECONNECT_COMMUNITY.value:
                await query.message.edit_text(
                    botman.text(
                        f"rusure_to_reconnect_{community_type.__str__()}",
                        account.language,
                    ),
                    reply_markup=botman.action_inline_keyboard(
                        BotMan.QueryActions.RECONNECT_COMMUNITY,
                        {None: "cancel", value: "reconnect"},
                        account.language,
                    ),
                )
            else:
                # If user has verified the reconnection request:
                community_id = int(params[1])
                current_community: Group | Channel | None = BotMan.getCommunity(community_type, account.chat_id)
                if current_community:
                    trash_data = community_type.to_class().getTrashedCustomization(community_id)
                    current_community.use_trash_data(trash_data)
                    current_community.save()
                    await query.message.edit_text(
                        botman.text(
                            f"trash_replaced_{community_type.__str__()}_data",
                            account.language,
                        )
                    )
                    return
                if community_type.to_class().restoreTrash(community_id):
                    await query.message.edit_text(botman.text("trash_restored", account.language))
                else:
                    await query.message.edit_text(botman.error("unexpected_error", account.language))
        case BotMan.QueryActions.IVE_SUBSCRIBED.value:
            if value:
                await asyncio.gather(
                    cmd_welcome(query, context),
                    query.message.delete(),
                    return_exceptions=True,
                )
                return
        case BotMan.QueryActions.SHOW_PREMIUM_PLANS.value:
            await handle_cmd_show_premium_plans(query, context)
        case _:
            if action == BotMan.QueryActions.ADMIN_DOWNGRADE_PREMIUM_USER.value and account.is_admin:
                if "v" not in callback_data or not value:
                    await botman.handle_users_menu_page_change(
                        account,
                        query,
                        callback_data,
                        Account.getPremiumUsers,
                        BotMan.QueryActions.ADMIN_DOWNGRADE_PREMIUM_USER,
                    )
                    return

                chat_id: int | None = None
                values = str(value).split(BotMan.CALLBACK_DATA_DELIMITER)
                try:
                    chat_id = int(values[0])
                except:
                    pass
                if not chat_id:
                    await query.message.edit_text(botman.error("invalid_user_specification", account.language))
                    return
                target_user = Account.getById(chat_id)
                if len(values) > 1:
                    if values[1] == "y":
                        if target_user.is_premium:
                            await asyncio.gather(
                                botman.downgrade_user(target_user, context=context),
                                query.message.edit_text(botman.text("account_downgraded", account.language)),
                            )
                            msg_to_edit = account.get_cache("msg2edit")
                            if msg_to_edit:
                                premiums = await botman.list_premiums(
                                    update=query,
                                    list_type=BotMan.QueryActions.ADMIN_DOWNGRADE_PREMIUM_USER,
                                    only_menu=True,
                                )
                                await context.bot.edit_message_reply_markup(
                                    chat_id=account.chat_id,
                                    message_id=int(msg_to_edit),
                                    reply_markup=premiums,
                                )
                                account.delete_specific_cache("msg2edit")
                            return
                        await query.message.edit_text(botman.text("not_a_premium", account.language))
                    else:
                        await query.message.edit_text(botman.text("operation_canceled", account.language))
                    account.delete_specific_cache("msg2edit")
                    # downgrade user
                else:
                    account.add_cache("msg2edit", query.message.message_id)
                    await send_r_u_sure_to_downgrade_message(context, account, target_user)
            elif action == BotMan.QueryActions.LIST_ENTITY.value and account.is_god:
                post_body: str = ""
                limit: int = 10
                community, page = (int(x) for x in value.split(BotMan.CALLBACK_DATA_DELIMITER))
                communities: List[Channel | Group] | None = None
                total: int
                match (community := BotMan.CommunityType.which(community)):
                    case BotMan.CommunityType.GROUP:
                        communities = Group.selectGroups(take=limit, page=page)
                        total = Group.getAllGroupsCount()
                    case BotMan.CommunityType.CHANNEL:
                        communities = Channel.selectActiveChannels(take=limit, page=page)
                        total = Channel.getActiveChannelsCount()
                    case _:
                        limit *= 2
                        accounts = Account.selectAccounts(take=limit, page=page, only_premiums=True)
                        total = Account.getPremiumUsersCount()
                        for i, user in enumerate(accounts):
                            post_body += f"{page * limit + i + 1}. {user.description}\n"
                if communities:
                    template = botman.text(
                        f"{community.__str__()}_description_template",
                        account.language,
                    )
                    number = page * limit + 1

                    for comm in communities:
                        premium_days = comm.owner.premium_days_remaining
                        premium_days, str_number = (
                            (persianify(premium_days), persianify(number))
                            if account.language == "fa"
                            else (str(premium_days), str(number))
                        )
                        post_body += template % (
                            str_number,
                            comm.name,
                            comm.title,
                            str(comm.owner),
                            comm.owner.firstname,
                            premium_days,
                        )
                        number += 1
                buttons: dict = dict()
                if page:
                    buttons[f"{community.value}{BotMan.CALLBACK_DATA_DELIMITER}{page - 1}"] = "prev_page"
                if (page + 1) * limit < total:
                    buttons[f"{community.value}{BotMan.CALLBACK_DATA_DELIMITER}{page + 1}"] = "next_page"
                await query.message.edit_text(
                    post_body or "Nothing!",
                    reply_markup=botman.action_inline_keyboard(
                        BotMan.QueryActions.LIST_ENTITY, buttons, account.language
                    ),
                )
            elif action == BotMan.QueryActions.REMOVE_ADMIN.value and account.is_god:
                if "v" not in callback_data or not value:
                    await botman.handle_users_menu_page_change(
                        account,
                        query,
                        callback_data,
                        Account.getStaffAdmins,
                        BotMan.QueryActions.REMOVE_ADMIN,
                    )
                    return
                target: Account | None = None
                try:
                    target = Account.getById(int(value))
                    if not target.is_admin:
                        await query.message.reply_text(botman.text("not_an_admin", account.language))
                        return
                    if target.is_god:
                        await query.message.reply_text(botman.error("not_allowed", account.language))
                        return
                    account.downgrade_to_normal(target)
                    try:
                        page: int = int(callback_data["pg"])
                    except:
                        page = 0
                    await asyncio.gather(
                        query.message.reply_text(
                            botman.text("admin_downgraded_to_normal", account.language) % (target.__str__(),)
                        ),
                        context.bot.send_message(
                            chat_id=target.chat_id,
                            text=botman.text("what_can_i_do", target.language),
                            reply_markup=botman.mainkeyboard(target),
                        ),
                        query.message.edit_reply_markup(
                            reply_markup=botman.users_list_menu(
                                Account.getStaffAdmins(),
                                BotMan.QueryActions.REMOVE_ADMIN,
                                page=page,
                                language=account.language,
                            )
                        ),
                    )
                except Exception as ex:
                    await query.message.reply_text(botman.error("unknown", account.language))
                    log(
                        f"Failed downgrading a user: {target or value}",
                        ex,
                        category_name="ADMIN",
                    )

            else:
                await asyncio.gather(
                    query.message.edit_text(botman.error("what_the_fuck", account.language)),
                    context.bot.send_message(
                        chat_id=account.chat_id,
                        text=botman.text("what_can_i_do", account.language),
                        reply_markup=botman.mainkeyboard(account),
                    ),
                    return_exceptions=True,
                )
    await query.answer()


async def handle_inline_keyboard_callbacks(update: Update, context: CallbackContext):
    query = update.callback_query
    if not query.data:
        return

    data = json.loads(query.data)
    account: Account = Account.get(query.message.chat)
    # first check query type
    if "act" in data:
        # action queries are handled here
        await handle_action_queries(query, context, account, data)
        return

    page: int
    try:
        page = int(data["pg"])
        # if previous line passes ok, means the value is as #Num and indicates the page number and is sending prev/next page signal
    except:
        page = 0

    if page == -1 or data["pg"] is None:
        # account.change_state()
        # account.delete_specific_cache("input_amounts", "input_symbols") #TODO: remove if after testing we made sure these two lines weren't required at first.
        if SelectionListTypes.which(data["lt"]) in [
            SelectionListTypes.EQUALIZER_UNIT,
            SelectionListTypes.ALARM,
        ]:
            await query.message.delete()
        else:
            await query.message.edit_text(botman.text("list_updated", account.language))
        return

    if data["v"] and data["v"][0] == "$":
        if data["v"][1] == "#":
            idx_first, idx_last = (int(x) for x in (data["v"][2:]).split(":"))
            hint = botman.text("log_page_indices", account.language) % (
                idx_first + 1,
                idx_last,
                page + 1,
            )
            await query.answer(
                text=hint if account.language != "fa" else persianify(hint),
                show_alert=True,
            )
        return

    market = MarketOptions.which(data["bt"])
    list_type = SelectionListTypes.which(data["lt"])
    match list_type:
        case SelectionListTypes.EQUALIZER_UNIT:
            input_amounts = account.get_cache("input_amounts")
            if input_amounts:
                unit_symbol = data["v"].upper()
                await asyncio.gather(
                    query.message.edit_text(" ".join([str(amount) for amount in input_amounts]) + f" {unit_symbol}"),
                    start_equalizing(query.message.reply_text, account, input_amounts, [unit_symbol]),
                    return_exceptions=True,
                )
            else:  # actually this segment occurrence probability is near zero, but I wrote it down anyway to handle any
                # condition possible or not!
                await query.message.edit_text(botman.text("enter_desired_price", account.language))
                account.change_state(
                    Account.States.INPUT_EQUALIZER_AMOUNT,
                    "input_symbols",
                    data["v"].upper(),
                )
            return
        case SelectionListTypes.ALARM:
            if "v" not in data or not data["v"]:
                await query.message.edit_reply_markup(
                    reply_markup=botman.create_tokens_menu(
                        list_type,
                        market,
                        (
                            botman.crypto_serv.coinsInPersian,
                            botman.currency_serv.nationalCurrenciesInPersian,
                            botman.currency_serv.goldsInPersian,
                        )[market.value - 1],
                        page=page,
                        language=account.language,
                        close_button=True,
                        choices_start_offset=int(market == MarketOptions.CURRENCY),
                    )
                )
                return
            symbol = data["v"].upper()
            account.change_state(
                Account.States.CREATE_ALARM,
                "create_alarm_props",
                {"symbol": symbol, "market": market.value},
            )

            message_text = botman.text("enter_desired_price", account.language)
            current_price_description = (
                botman.crypto_serv.get_price_description_row(symbol, account.language)
                if market == MarketOptions.CRYPTO
                else botman.currency_serv.get_price_description_row(symbol, account.language)
            )

            if current_price_description:
                message_text += f"\n\n{current_price_description}"
            await asyncio.gather(
                query.message.reply_text(message_text, reply_markup=botman.cancel_menu(account.language)),
                query.message.delete(),
                return_exceptions=True,
            )
            return

    # if the user is configuring a list:
    try:
        selection_list = BotMan.handleMarketSelection(account, list_type, market, data["v"])

        await query.message.edit_reply_markup(
            reply_markup=botman.create_tokens_menu(
                list_type,
                market,
                (
                    botman.crypto_serv.coinsInPersian,
                    botman.currency_serv.nationalCurrenciesInPersian,
                    botman.currency_serv.goldsInPersian,
                )[market.value - 1],
                selection_list,
                page=page,
                language=account.language,
                close_button=True,
                choices_start_offset=int(list_type.should_show_irt(market)),
            )
        )

    except ValueError as reached_max_ex:
        max_selection = int(reached_max_ex.__str__())
        await botman.show_reached_max_error(query, account, max_selection)

    except IndexError as ie:
        log("Invalid market selection procedure", ie, "general")
        account.change_state()
        await query.message.edit_text(text=botman.error("invalid_market_selection", account.language))
    except BadRequest:
        # when the message content is exactly the same
        pass
    except Exception as selection_ex:
        log("User couldn't select coins", selection_ex, "general")
        account.change_state()
        await query.message.edit_text(text=botman.error("unknown", account.language))


async def cmd_switch_language(update: Update, _: CallbackContext):
    acc = Account.get(update.message.chat)
    BotMan.updateUserLanguage(acc, "en" if acc.language != "en" else "fa")
    await update.message.reply_text(
        botman.resourceman.text_for_case_sensitive_key("language_switched", acc.language),
        reply_markup=botman.mainkeyboard(acc),
    )


async def list_type_is_selected(update: Update):
    account = Account.get(update.message.chat)
    if account.state not in [
        Account.States.CONFIG_CALCULATOR_LIST,
        Account.States.INPUT_EQUALIZER_UNIT,
        Account.States.CONFIG_MARKETS,
        Account.States.CREATE_ALARM,
        Account.States.CONFIG_GROUP_MARKETS,
        Account.States.CONFIG_CHANNEL_MARKETS,
    ]:
        await update.message.reply_text(
            botman.error("list_type_not_specified", account.language),
            reply_markup=botman.mainkeyboard(account),
        )
        return False
    return True


# premiums:
async def cmd_start_using_in_channel(update: Update, _: CallbackContext):
    account = Account.get(update.message.chat)
    account.change_state(Account.States.ADD_BOT_AS_ADMIN)
    account.delete_specific_cache("channel_chat_id", "community")
    await update.message.reply_text(
        botman.text("add_bot_as_channel_admin", account.language),
        reply_markup=botman.cancel_menu(account.language),
    )


async def handle_cmd_show_my_plan_status(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    days_remaining = account.premium_days_remaining
    if days_remaining < 0:
        await botman.send_message_with_premium_button(
            update,
            botman.text("ur_using_free_plan", account.language),
            language=account.language,
        )
        if account.plus_end_date is not None:
            await botman.downgrade_user(account)
        return
    str_days_remaining = str(days_remaining) if account.language != "fa" else persianify(days_remaining)
    if days_remaining <= 7:
        await context.bot.send_message(
            chat_id=account.chat_id,
            text=botman.text("premium_expiry_is_close", account.language) % (str_days_remaining,),
        )
        return
    await update.message.reply_text(
        botman.text("ur_plan_duration", account.language) % (str_days_remaining,),
        reply_markup=botman.mainkeyboard(account),
    )


async def admin_renew_plans(update: Update, context: CallbackContext, account: Account | None = None):
    if not account:
        account = Account.get(update.message.chat)
    if account.is_authorized(context.args):
        if account.state == Account.States.CHANGE_PREMIUM_PLANS:
            post: str | None = None
            photo_file_id: str | None = None
            if update.message.photo:
                photo_file_id = update.message.photo[-1].file_id
                post = update.message.caption or ""
            elif update.message.text:
                post = update.message.text

            if post:
                language = BotSettings.Language.FA
                for ch in post:
                    if ch.isalnum():
                        ch = ch.lower()
                        if ("a" <= ch <= "z") or ("0" <= ch <= "9"):
                            language = BotSettings.Language.EN
                        break

                BotSettings().get().update_premium_plans_post(post, photo_file_id, language)
                await update.message.reply_text(
                    botman.text("update_successful", account.language),
                    reply_markup=botman.get_admin_primary_keyboard(account),
                )

                return True
        return False


async def unknown_command_handler(update: Update, _: CallbackContext = None):
    account = Account.get(update.message.chat)
    await update.message.reply_text(
        botman.error("what_the_fuck", account.language),
        reply_markup=(
            botman.mainkeyboard(account) if update.message.chat.type.lower() == "private" else ReplyKeyboardRemove()
        ),
    )


async def go_to_community_panel(update: Update, account: Account, community_type: BotMan.CommunityType):
    account.add_cache("community", community_type.value)
    if not account.is_premium:
        await update.message.reply_text(
            botman.text("go_premium_to_activate_feature", account.language),
            reply_markup=botman.get_community_config_keyboard(community_type, account.language),
        )
        return

    if not (community := community_type.to_class().getByOwner(account.chat_id, take=1)):
        await unknown_command_handler(update)
        return

    await update.message.reply_text(
        botman.text(f"{community_type.__str__()}_x_panel", account.language) % (community.title,),
        reply_markup=botman.get_community_config_keyboard(community_type, account.language),
    )


async def handle_cmd_channels(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    channel = Channel.getByOwner(account.chat_id, take=1)
    if not channel:
        await cmd_start_using_in_channel(update, context)
        return
    tasks = []
    if not channel.is_active and account.is_premium:
        tasks.append(
            update.message.reply_text(
                text=botman.text("channel_not_active", account.language),
                reply_markup=botman.action_inline_keyboard(
                    BotMan.QueryActions.START_CHANNEL_POSTING,
                    {channel.id: "start"},
                    account.language,
                    columns_in_a_row=1,
                ),
            )
        )
    tasks.append(go_to_community_panel(update, account, BotMan.CommunityType.CHANNEL))
    await asyncio.gather(*tasks)


async def handle_cmd_groups(update: Update, _: CallbackContext):
    account = Account.get(update.message.chat)
    if not Group.userHasAnyGroups(account.chat_id):
        if account.is_premium:
            await update.message.reply_text(botman.text("add_bot_as_group_admin", account.language))
        else:
            await botman.send_message_with_premium_button(
                update,
                botman.text("add_bot_as_group_admin_n_go_premium", account.language),
                language=account.language,
            )
        return
    await go_to_community_panel(update, account, BotMan.CommunityType.GROUP)


async def handle_cmd_show_premium_plans(update: Update | CallbackQuery, _: CallbackContext):
    account = Account.get(update.message.chat)
    post_text, post_photo = BotSettings.get().PREMIUM_PLANS_POST(account.language)
    if post_photo:
        await update.message.reply_photo(
            photo=post_photo,
            caption=post_text,
            reply_markup=botman.mainkeyboard(account),
        )
        return
    await update.message.reply_text(post_text, reply_markup=botman.mainkeyboard(account))


async def handle_messages(update: Update, context: CallbackContext):
    if not update or not update.message:
        return
    message_text = update.message.text

    match message_text:
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
            await handle_cmd_channels(update, context)
        case BotMan.Commands.MY_GROUPS_FA.value | BotMan.Commands.MY_GROUPS_EN.value:
            await handle_cmd_groups(update, context)
        case BotMan.Commands.SETTINGS_FA.value | BotMan.Commands.SETTINGS_EN.value:
            await botman.show_settings_menu(update)
        case BotMan.Commands.GO_PREMIUM_FA.value | BotMan.Commands.GO_PREMIUM_EN.value:
            await handle_cmd_show_premium_plans(update, context)
        case BotMan.Commands.MY_PREMIUM_PLAN_DURATION_FA.value | BotMan.Commands.MY_PREMIUM_PLAN_DURATION_EN.value:
            await handle_cmd_show_my_plan_status(update, context)
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
            account = Account.get(update.message.chat)
            channel = Channel.getByOwner(account.chat_id)
            if not channel:
                account.delete_specific_cache("community")
                await update.message.reply_text(
                    botman.error("no_channels", account.language),
                    reply_markup=botman.mainkeyboard(account),
                )
                return
            await botman.prepare_set_interval_interface(
                update, account, channel.id, Account.States.CHANGE_POST_INTERVAL
            )

        case (
            BotMan.Commands.COMMUNITY_CONFIG_PRICE_LIST_FA.value | BotMan.Commands.COMMUNITY_CONFIG_PRICE_LIST_EN.value
        ):
            account = Account.get(update.message.chat)
            community_type = BotMan.CommunityType.which(account.get_cache("community"))
            if not community_type:
                await unknown_command_handler(update, context)
                return
            account.add_cache("back", BotMan.MenuSections.COMMUNITY_PANEL.value)
            await show_market_types(
                update,
                context,
                (
                    Account.States.CONFIG_GROUP_MARKETS
                    if community_type == BotMan.CommunityType.GROUP
                    else Account.States.CONFIG_CHANNEL_MARKETS
                ),
            )
        case BotMan.Commands.COMMUNITY_TRIGGER_DATE_TAG_FA.value | BotMan.Commands.COMMUNITY_TRIGGER_DATE_TAG_EN.value:
            account = Account.get(update.message.chat)
            community_type = account.get_cache("community")
            if not BotMan.CommunityType.which(community_type):
                await unknown_command_handler(update, context)
                return
            await update.message.reply_text(
                botman.text("trigger_date_tag", account.language),
                reply_markup=botman.action_inline_keyboard(
                    BotMan.QueryActions.TRIGGER_DATE_TAG,
                    {
                        f"{community_type}{BotMan.CALLBACK_DATA_DELIMITER}0": "no_hide_tag",
                        f"{community_type}{BotMan.CALLBACK_DATA_DELIMITER}1": "yes_show_tag",
                    },
                    account.language,
                ),
            )
        case (
            BotMan.Commands.COMMUNITY_TRIGGER_MARKET_TAGS_FA.value
            | BotMan.Commands.COMMUNITY_TRIGGER_MARKET_TAGS_EN.value
        ):
            account = Account.get(update.message.chat)
            community_type = account.get_cache("community")
            if not BotMan.CommunityType.which(community_type):
                await unknown_command_handler(update, context)
                return
            await update.message.reply_text(
                botman.text("trigger_market_tags", account.language),
                reply_markup=botman.action_inline_keyboard(
                    BotMan.QueryActions.TRIGGER_MARKET_TAGS,
                    {
                        f"{community_type}{BotMan.CALLBACK_DATA_DELIMITER}0": "no_hide_tag",
                        f"{community_type}{BotMan.CALLBACK_DATA_DELIMITER}1": "yes_show_tag",
                    },
                    account.language,
                ),
            )
        case (
            BotMan.Commands.COMMUNITY_SET_MESSAGE_HEADER_FA.value
            | BotMan.Commands.COMMUNITY_SET_MESSAGE_HEADER_EN.value
            | BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_FA.value
            | BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_EN.value
        ):
            (section, state) = (
                ("header", Account.States.SET_MESSAGE_HEADER)
                if message_text != BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_FA.value
                and message_text != BotMan.Commands.COMMUNITY_SET_MESSAGE_FOOTNOTE_EN.value
                else ("footer", Account.States.SET_MESSAGE_FOOTNOTE)
            )
            account = Account.get(update.message.chat)
            community_type = account.get_cache("community")
            if not BotMan.CommunityType.which(community_type):
                await unknown_command_handler(update, context)
                return
            telegram_res: Message = await update.message.reply_text(
                botman.text(f"write_msg_{section}", account.language),
                reply_markup=botman.action_inline_keyboard(
                    BotMan.QueryActions.UPDATE_MESSAGE_SECTIONS,
                    {
                        None: "cancel",
                        f"{community_type}{BotMan.CALLBACK_DATA_DELIMITER}{section}": "remove",
                    },
                    account.language,
                ),
            )
            account.change_state(state, "msg2delete", telegram_res.message_id)
        case BotMan.Commands.GROUP_CHANGE_FA.value | BotMan.Commands.GROUP_CHANGE_EN.value:
            account = Account.get(update.message.chat)
            group = Group.getByOwner(account.chat_id)
            if not group:
                account.delete_specific_cache("community")
                await update.message.reply_text(
                    botman.error("no_groups", account.language),
                    reply_markup=botman.mainkeyboard(account),
                )
                return
            account.change_state(Account.States.CHANGE_GROUP, "changing_id", group.id)
            account.add_cache("back", BotMan.MenuSections.COMMUNITY_PANEL.value)
            await update.message.reply_text(
                botman.text("add_bot_to_new_group", account.language),
                reply_markup=botman.cancel_menu(account.language),
            )
        case BotMan.Commands.CHANNEL_CHANGE_FA.value | BotMan.Commands.CHANNEL_CHANGE_EN.value:
            account = Account.get(update.message.chat)
            if not Channel.getByOwner(account.chat_id):
                account.delete_specific_cache("community")
                await update.message.reply_text(
                    botman.error("no_channels", account.language),
                    reply_markup=botman.mainkeyboard(account),
                )
                return
            account.change_state(
                Account.States.ADD_BOT_AS_ADMIN,
                "community",
                BotMan.CommunityType.CHANNEL.value,
            )
            account.add_cache("back", BotMan.MenuSections.COMMUNITY_PANEL.value)
            await update.message.reply_text(
                botman.text("add_bot_as_channel_admin", account.language),
                reply_markup=botman.cancel_menu(account.language),
            )
        case BotMan.Commands.COMMUNITY_DISCONNECT_FA.value | BotMan.Commands.COMMUNITY_DISCONNECT_EN.value:
            account = Account.get(update.message.chat)
            if not (
                community := BotMan.getCommunity(
                    (community_type := BotMan.CommunityType.which(account.get_cache("community"))),
                    account.chat_id,
                )
            ):
                account.delete_specific_cache("community")
                await update.message.reply_text(
                    botman.error(f"no_{community_type.__str__()}", account.language),
                    reply_markup=botman.mainkeyboard(account),
                )
                return

            await update.message.reply_text(
                botman.text(f"rusure_to_disconnect_{community_type.__str__()}", account.language),
                reply_markup=botman.action_inline_keyboard(
                    BotMan.QueryActions.DISCONNECT_COMMUNITY,
                    {
                        None: "cancel",
                        f"{community_type.value}{BotMan.CALLBACK_DATA_DELIMITER}{community.id}": "community_disconnect",
                    },
                    language=account.language,
                ),
            )
        # settings sub menu:
        case BotMan.Commands.SET_BOT_LANGUAGE_FA.value | BotMan.Commands.SET_BOT_LANGUAGE_EN.value:
            account = Account.get(update.message.chat)
            if not await botman.has_subscribed_us(account.chat_id, context):
                await botman.ask_for_subscription(update, account.language)
                return
            await update.message.reply_text(
                botman.text("select_bot_language", account.language),
                reply_markup=botman.action_inline_keyboard(
                    BotMan.QueryActions.CHOOSE_LANGUAGE,
                    {"fa": "language_persian", "EN-FA": "language_english", 0: "close"},
                    language=account.language,
                ),
            )
        case BotMan.Commands.FACTORY_RESET_FA.value | BotMan.Commands.FACTORY_RESET_EN.value:
            account = Account.get(update.message.chat)
            await update.message.reply_text(
                botman.text("factory_reset_confirmation", account.language),
                reply_markup=botman.action_inline_keyboard(
                    BotMan.QueryActions.FACTORY_RESET,
                    {"y": "factory_reset"},
                    language=account.language,
                ),
            )

        case BotMan.Commands.SUPPORT_FA.value | BotMan.Commands.SUPPORT_EN.value:
            await update.message.reply_text(
                botman.text("contact_support_hint") % (Account.getHardcodeAdmin()["username"])
            )
        case BotMan.Commands.OUR_OTHERS_FA.value | BotMan.Commands.OUR_OTHERS_EN.value:
            await context.bot.send_message(
                chat_id=update.message.chat_id,
                text=botman.text(
                    "check_our_other_collections",
                    Account.get(update.message.chat).language,
                ),
                disable_web_page_preview=True,
            )
        case BotMan.Commands.TUTORIALS_FA.value | BotMan.Commands.TUTORIALS_EN.value:
            account = Account.get(update.message.chat)
            await update.message.reply_text(
                botman.text("click_tutorial_u_need", account.language),
                reply_markup=botman.action_inline_keyboard(
                    botman.QueryActions.SELECT_TUTORIAL,
                    {
                        "config_lists": "config_lists",
                        "get_prices": "get_prices",
                        "config_calculator": "config_calculator",
                        "calculator": "calculator",
                        "list_alarms": "list_alarms",
                        "create_alarm": "create_alarm",
                        "my_groups": "my_groups",
                        "my_channels": "my_channels",
                        f"! {update.message.message_id}": "close",
                    },
                    language=account.language,
                    in_main_keyboard=True,
                ),
            )

        # cancel/return options
        case (
            BotMan.Commands.CANCEL_FA.value
            | BotMan.Commands.CANCEL_EN.value
            | BotMan.Commands.RETURN_FA.value
            | BotMan.Commands.RETURN_EN.value
        ):
            account = Account.get(update.message.chat)
            prev_menu = account.get_cache("back")
            if prev_menu:
                match prev_menu:
                    case BotMan.MenuSections.COMMUNITY_PANEL.value:
                        community = BotMan.CommunityType.which(account.get_cache("community"))
                        if not community:
                            await unknown_command_handler(update, context)
                            return
                        await go_to_community_panel(update, account, community)
                        account.delete_specific_cache("back")
                        return
            await botman.deleteRedundantMessage(account, context, delete_cache=False)
            account.change_state(
                clear_cache=message_text == BotMan.Commands.RETURN_FA.value
                or message_text == BotMan.Commands.RETURN_EN.value
            )
            await update.message.reply_text(
                botman.text(
                    (
                        "operation_canceled"
                        if message_text != BotMan.Commands.RETURN_FA.value
                        and message_text != BotMan.Commands.RETURN_EN.value
                        else "what_can_i_do"
                    ),
                    account.language,
                ),
                reply_markup=botman.mainkeyboard(account),
            )

        # special states
        case _:
            # check account state first, to see if he/she is in input state
            account = Account.get(update.message.chat)
            if account.is_admin:
                match message_text:
                    case (
                        BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_FA.value
                        | BotMan.Commands.ADMIN_UPGRADE_TO_PREMIUM_EN.value
                    ):
                        await cmd_upgrade_user(update, context)
                        return
                    case BotMan.Commands.ADMIN_DOWNGRADE_USER_FA.value | BotMan.Commands.ADMIN_DOWNGRADE_USER_EN.value:
                        await cmd_list_users_to_downgrade(update, context)
                        return

                if account.is_god:
                    # admin options:
                    match message_text:
                        case BotMan.Commands.GOD_NOTICES_FA.value | BotMan.Commands.GOD_NOTICES_EN.value:
                            await cmd_send_post(update, context)
                            return
                        case BotMan.Commands.GOD_STATISTICS_FA.value | BotMan.Commands.GOD_STATISTICS_EN.value:
                            await cmd_report_statistics(update, context)
                            return
                        case (
                            BotMan.Commands.GOD_CHANGE_PREMIUM_PLANS_FA.value
                            | BotMan.Commands.GOD_CHANGE_PREMIUM_PLANS_EN.value
                        ):
                            await cmd_send_plans_post(update, context)
                            return
                        case BotMan.Commands.GOD_ADD_ADMIN_FA.value | BotMan.Commands.GOD_ADD_ADMIN_EN.value:
                            await cmd_add_admin(update, context)
                            return
                        case BotMan.Commands.GOD_REMOVE_ADMIN_FA.value | BotMan.Commands.GOD_REMOVE_ADMIN_EN.value:
                            await cmd_remove_admin(update, context)
                            return
            match account.state:
                case Account.States.INPUT_EQUALIZER_AMOUNT:
                    params = message_text.split()
                    count_of_params = len(params)

                    # extract parameters and categorize them into units and amounts
                    amounts = []
                    units = account.get_cache("input_symbols") or []
                    if not isinstance(units, list):
                        units = [units]
                    invalid_units = []
                    index = 0
                    # extract amounts from params
                    try:
                        while index < count_of_params:
                            amount = BotMan.stringToNumber(params[index])
                            amounts.append(amount)
                            index += 1
                    except:
                        pass
                    if not amounts:
                        await update.message.reply_text(
                            botman.error("invalid_amount", account.language),
                            reply_markup=botman.mainkeyboard(account),
                        )
                        return

                    # start extracting units
                    while index < count_of_params:
                        source_symbol = params[index].upper()
                        if (
                            source_symbol in botman.crypto_serv.coinsInPersian
                            or source_symbol in botman.currency_serv.currenciesInPersian
                        ):
                            units.append(source_symbol)
                        else:
                            invalid_units.append(source_symbol)

                        index += 1

                    if invalid_units:
                        await update.message.reply_text(
                            botman.error("unrecognized_currency_symbols", account.language) + ", ".join(invalid_units),
                            reply_markup=botman.mainkeyboard(account),
                            reply_to_message_id=update.message.message_id,
                        )
                    if not units:
                        account.change_state(
                            Account.States.INPUT_EQUALIZER_UNIT,
                            "input_amounts",
                            amounts,
                        )
                        await show_market_types(update, context, Account.States.INPUT_EQUALIZER_UNIT)
                    else:
                        await start_equalizing(update.message.reply_text, account, amounts, units)

                case Account.States.CREATE_ALARM:
                    props = account.get_cache("create_alarm_props")
                    try:
                        price = float(message_text)
                    except:
                        await update.message.reply_text(
                            botman.error("invalid_price", account.language),
                            reply_markup=botman.cancel_menu(account.language),
                        )
                        return

                    symbol = props["symbol"]
                    market = props["market"]
                    data_prefix = (
                        f"{market}{BotMan.CALLBACK_DATA_DELIMITER}{symbol}{BotMan.CALLBACK_DATA_DELIMITER}{price}"
                    )
                    await update.message.reply_text(
                        botman.text("whats_price_unit", account.language),
                        reply_markup=botman.action_inline_keyboard(
                            BotMan.QueryActions.SELECT_PRICE_UNIT,
                            {
                                f"{data_prefix}{BotMan.CALLBACK_DATA_DELIMITER}irt": "price_unit_irt",
                                f"{data_prefix}{BotMan.CALLBACK_DATA_DELIMITER}usd": "price_unit_usd",
                            },
                            account.language,
                        ),
                    )
                    account.delete_specific_cache("create_alarm_props")

                case Account.States.ADD_BOT_AS_ADMIN:
                    channel_chat: Chat | None = None
                    if update.message.forward_from_chat:
                        channel_chat = update.message.forward_from_chat

                    if not channel_chat:
                        # send a message to the channel or group and retrieve chat_id
                        try:
                            if "https://t.me/" in message_text:
                                message_text = message_text.replace("https://t.me/", "@")
                            response: Message = await context.bot.send_message(chat_id=message_text, text="Test")
                            channel_chat = response.chat
                            await context.bot.delete_message(chat_id=channel_chat.id, message_id=response.message_id)
                        except Exception as x:
                            await update.message.reply_text(
                                botman.error(
                                    "bot_seems_not_admin_or_url_invalid",
                                    account.language,
                                ),
                                reply_markup=botman.action_inline_keyboard(
                                    botman.QueryActions.VERIFY_BOT_IS_ADMIN,
                                    {message_text: "verify_admin"},
                                    in_main_keyboard=False,
                                ),
                            )
                            log(
                                "Something fucked while identifying the channel",
                                x,
                                category_name="Channel",
                            )
                    if channel_chat:
                        await botman.use_input_channel_chat_info(
                            update,
                            context,
                            account,
                            channel_chat,
                            Account.States.SELECT_POST_INTERVAL,
                        )
                case Account.States.SELECT_POST_INTERVAL | Account.States.CHANGE_POST_INTERVAL:
                    interval: int
                    try:
                        interval = PostInterval.TimestampToMinutes(message_text)
                    except:
                        await update.message.reply_text(botman.error("unsupported_input_format", account.language))
                        return
                    await botman.handle_set_interval_outcome(update, context, interval)
                    try:
                        await context.bot.delete_message(
                            chat_id=account.chat_id,
                            message_id=int(account.get_cache("interval_menu_msg_id")),
                        )
                    except:
                        pass
                    account.change_state()
                    account.delete_specific_cache("interval_menu_msg_id")
                case Account.States.SET_MESSAGE_FOOTNOTE | Account.States.SET_MESSAGE_HEADER:
                    community_type = BotMan.CommunityType.which(account.get_cache("community"))
                    if not community_type or community_type == BotMan.CommunityType.NONE:
                        await unknown_command_handler(update, context)
                        return
                    community = community_type.to_class().getByOwner(account.chat_id)
                    await botman.deleteRedundantMessage(account, context)
                    if not community:
                        await update.message.reply_text(
                            botman.error(f"no_{community_type}s", account.language),
                            reply_markup=botman.mainkeyboard(account),
                        )
                        account.delete_specific_cache("community")
                        return
                    if account.state == Account.States.SET_MESSAGE_HEADER:
                        community.message_header = message_text
                    else:
                        community.message_footnote = message_text
                    community.save()
                    await update.message.reply_text(
                        botman.text("update_successful", account.language),
                        reply_markup=botman.get_community_config_keyboard(community_type, account.language),
                    )
                    account.change_state()
                case _:
                    if not account.is_admin:
                        await update.message.reply_text(
                            botman.error("what_the_fuck", account.language),
                            reply_markup=botman.mainkeyboard(account),
                        )
                        return

                    match account.state:
                        case Account.States.UPGRADE_USER:
                            upgrading_chat_id = account.get_cache("upgrading")

                            if not upgrading_chat_id:
                                user = BotMan.identifyUser(update)

                                if not user:
                                    await update.message.reply_text(
                                        botman.error(
                                            "invalid_user_specification",
                                            account.language,
                                        )
                                    )
                                    return
                                account.add_cache("upgrading", user.chat_id)

                                await update.message.reply_text(user.user_detail)
                                await update.message.reply_text(
                                    botman.text(
                                        "enter_upgrade_premium_duration",
                                        account.language,
                                    ),
                                    reply_markup=botman.cancel_menu(account.language),
                                )
                            else:
                                days: int | None = None
                                try:
                                    days = int(message_text)
                                except:
                                    pass
                                if not days or (days < 0):
                                    await update.message.reply_text(
                                        botman.error("invalid_days_count", account.language),
                                        reply_markup=botman.cancel_menu(account.language),
                                    )
                                    return
                                target = Account.getById(upgrading_chat_id)
                                target.upgrade(days)
                                days_remaining = (
                                    persianify(target.premium_days_remaining)
                                    if target.language == "fa"
                                    else str(target.premium_days_remaining)
                                )
                                await context.bot.send_message(
                                    chat_id=target.chat_id,
                                    text=botman.text("youre_upgraded_premium", target.language) % (days_remaining,),
                                    reply_markup=botman.mainkeyboard(target),
                                )

                                await update.message.reply_text(
                                    botman.text("user_upgraded_premium", account.language),
                                    reply_markup=botman.mainkeyboard(account),
                                )
                                account.change_state()
                            return
                        case Account.States.DOWNGRADE_USER:
                            user = BotMan.identifyUser(update)

                            if not user:
                                await update.message.reply_text(
                                    botman.error("invalid_user_specification", account.language)
                                )
                                return
                            await send_r_u_sure_to_downgrade_message(context, account, user)
                            return

                    if not account.is_god:
                        await update.message.reply_text(
                            botman.error("what_the_fuck", account.language),
                            reply_markup=botman.mainkeyboard(account),
                        )
                        return

                    # God actions
                    match account.state:
                        case Account.States.SEND_POST:
                            # admin is trying to send post
                            if update.message.text.isnumeric():
                                try:
                                    days = int(update.message.text)
                                    account.add_cache("offset", days)
                                    str_days = str(days) if account.language != "fa" else persianify(days)
                                    suffix = botman.text(
                                        "this_message_will_be_removed_after",
                                        account.language,
                                    ) % (str_days,)
                                    await update.message.reply_text(
                                        botman.text("type_your_post_text", account.language) + suffix,
                                        reply_markup=botman.cancel_menu(account.language),
                                    )
                                    return
                                except:
                                    pass

                            all_accounts: List[int] = list(
                                filter(
                                    lambda chat_id: chat_id != account.chat_id,
                                    Account.everybody(),
                                )
                            )
                            telegram_response: Message = await update.message.reply_text(
                                botman.text("sending_your_post", account.language)
                            )

                            removal_time: int | None = None
                            try:
                                message_id = int(str(telegram_response.message_id))
                            except Exception as x:
                                log(
                                    "Failed getting admin post message id:",
                                    x,
                                    category_name="Admin",
                                )
                                await asyncio.gather(
                                    update.message.reply_text(
                                        botman.text(
                                            "failed_retrieving_post_message",
                                            account.language,
                                        )
                                    ),
                                    cmd_send_post(update, context),
                                )
                                return
                            try:
                                offset = int(account.pop_cache("offset"))
                                removal_time = n_days_later_timestamp(offset)
                            except Exception as x:
                                pass

                            post_tasks = await asyncio.gather(
                                *[update.message.copy(chat_id) for chat_id in all_accounts],
                                return_exceptions=True,
                            )

                            users_count, not_received = len(all_accounts), len(
                                list(
                                    filter(
                                        lambda t: isinstance(t, BaseException),
                                        post_tasks,
                                    )
                                )
                            )
                            await asyncio.gather(
                                context.bot.delete_message(chat_id=account.chat_id, message_id=message_id),
                                update.message.reply_text(
                                    botman.text("post_successfully_sent", account.language)
                                    % (users_count, users_count - not_received),
                                    reply_markup=botman.get_admin_primary_keyboard(account),
                                ),
                                return_exceptions=True,
                            )

                            account.change_state()
                            if removal_time:
                                trash_type = Account.database().TrashType.MESSAGE.value
                                try:
                                    Account.schedulePostsForRemoval(
                                        [
                                            (
                                                trash_type,
                                                all_accounts[i],
                                                task.message_id,
                                                removal_time,
                                            )
                                            for i, task in enumerate(post_tasks)
                                            if not isinstance(task, BaseException)
                                        ]
                                    )
                                    await update.message.reply_text(
                                        botman.text(
                                            "posts_scheduled_for_removal",
                                            account.language,
                                        ),
                                        reply_markup=botman.get_admin_primary_keyboard(account),
                                    )
                                except Exception as x:
                                    log(
                                        "Failed to schedule admin post for removal",
                                        x,
                                        category_name="Admin",
                                    )
                                    await update.message.reply_text(
                                        botman.text(
                                            "posts_sent_by_not_scheduled",
                                            account.language,
                                        ),
                                        reply_markup=botman.get_admin_primary_keyboard(account),
                                    )
                        case Account.States.CHANGE_PREMIUM_PLANS:
                            await admin_renew_plans(update, context, account)

                        case Account.States.ADD_ADMIN:
                            if not (user := BotMan.identifyUser(update)):
                                await update.message.reply_text(
                                    botman.error(
                                        "invalid_user_specification",
                                        account.language,
                                    )
                                )
                                return
                            try:
                                account.make_admin(user)
                                await asyncio.gather(
                                    update.message.reply_text(
                                        botman.text(
                                            "user_is_admin_now",
                                            account.language,
                                        )
                                        % user.user_detail,
                                        reply_markup=botman.mainkeyboard(account),
                                    ),
                                    context.bot.send_message(
                                        chat_id=user.chat_id,
                                        text=botman.text("youre_admin_now", user.language),
                                        reply_markup=botman.mainkeyboard(user),
                                    ),
                                )
                            except Forbidden:
                                log(
                                    f"User#{account.chat_id} tried to upgrade another user to admin level, with no God Access.\nUser Detail:{account.user_detail}",
                                    category_name="Admin",
                                )
                                await update.message.reply_text(
                                    botman.error(
                                        "not_allowed",
                                        account.language,
                                    ),
                                    reply_markup=botman.mainkeyboard(account),
                                )
                            except Exception as x:
                                await unhandled_error_happened(update)
                                log(
                                    "A god user tried to upgrade another user to admin but encountered unknown error:",
                                    x,
                                    category_name="Admin",
                                )
                            account.change_state()


async def handle_new_group_members(update: Update, context: CallbackContext):
    if not update.my_chat_member or not update.my_chat_member.new_chat_member:
        return

    if update.my_chat_member.chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        return  # Ignore channels and private chats; TODO: Modify this to also automatically handle channel joins in future.

    if update.my_chat_member.new_chat_member.user.id == context.bot.id:
        owner = Account.getById(update.my_chat_member.from_user.id)
        if update.my_chat_member.new_chat_member.status == ChatMemberMember.LEFT:
            await context.bot.send_message(
                chat_id=owner.chat_id,
                text=botman.text("seems_bot_was_removed_from_group", owner.language),
            )
            return
        elif (
            update.my_chat_member.old_chat_member
            and update.my_chat_member.old_chat_member.status == ChatMemberMember.ADMINISTRATOR
            and update.my_chat_member.new_chat_member.status != ChatMemberMember.ADMINISTRATOR
        ):
            # This is a downgrade event, not a new addition
            log(
                f"Bot was downgraded to normal member in group {update.my_chat_member.chat.id}",
                category_name="GroupEvents",
            )
            await context.bot.send_message(
                chat_id=owner.chat_id,
                text=botman.text("group_admin_downgraded_bot", owner.language),
            )
            return
        try:
            if owner.state == Account.States.CHANGE_GROUP:
                old_group_id = owner.get_cache("changing_id")
                old_group: Group
                if not old_group_id or not (old_group := Group.get(old_group_id)):
                    await context.bot.send_message(
                        chat_id=owner.chat_id,
                        text=botman.error("unexpected_error", owner.language),
                        reply_markup=botman.mainkeyboard(owner),
                    )
                    owner.change_state()
                    owner.delete_specific_cache("changing_id")
                    return
                try:
                    say_farewell_task = context.bot.send_message(
                        chat_id=old_group_id,
                        text=botman.text("farewell_my_friends", owner.language),
                    )
                    old_group.change(update.my_chat_member.chat)
                    await asyncio.gather(
                        say_farewell_task,
                        context.bot.send_message(
                            chat_id=owner.chat_id,
                            text=botman.text("group_changed", owner.language),
                            reply_markup=botman.get_community_config_keyboard(
                                BotMan.CommunityType.GROUP, owner.language
                            ),
                        ),
                        context.bot.leave_chat(old_group_id),
                        return_exceptions=True,
                    )
                    owner.delete_specific_cache("changing_id")
                    owner.change_state(
                        cache_key="community",
                        data=BotMan.CommunityType.GROUP.value,
                    )
                except InvalidInputException:
                    await context.bot.send_message(
                        chat_id=owner.chat_id,
                        text=botman.error("changed_group_is_the_same", owner.language),
                        reply_markup=botman.get_community_config_keyboard(BotMan.CommunityType.GROUP, owner.language),
                    )
                except:
                    pass
                return
            group = Group.register(update.my_chat_member.chat, owner.chat_id)
            if group.is_active:
                await context.bot.send_message(
                    chat_id=owner.chat_id,
                    text=botman.text("group_is_active", owner.language) % (group.title,),
                )
            else:
                await botman.send_message_with_premium_button_to(
                    context,
                    owner.chat_id,
                    botman.text("go_premium_for_group_activation", owner.language) % group.title,
                    language=owner.language,
                )
        except MaxAddedCommunityException:
            await context.bot.send_message(
                chat_id=owner.chat_id,
                text=botman.error("max_groups_reached", owner.language),
            )
        except ValueError:
            owner.change_state(clear_cache=True)
            context.bot.send_message(
                chat_id=owner.chat_id,
                text=botman.error("unhandled_error_happened", owner.language),
                reply_markup=botman.mainkeyboard(owner),
            )
        return


async def cmd_refresh(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    if not account.is_authorized(context.args):
        await update.message.reply_text(
            botman.error("what_the_fuck", account.language),
            reply_markup=botman.mainkeyboard(account),
        )
        return
    botman.refreshMemory()
    account = Account.get(update.message.chat)
    await update.message.reply_text(
        "Successfully refreshed.",
        reply_markup=botman.mainkeyboard(account),
    )


async def handle_group_messages(update: Update, _: CallbackContext):
    if not update.message or not update.message.text:
        return
    crypto_amounts, currency_amounts = botman.extract_symbols_and_amounts(update.message.text)
    group: Group = Group.get(update.message.chat.id)
    to_user: Account = Account.getById(update.message.from_user.id, should_create=False)

    if not group or not group.is_active:
        return

    tasks = []
    for input_list in [
        (crypto_amounts, botman.create_crypto_equalize_message),
        (currency_amounts, botman.create_currency_equalize_message),
    ]:
        inputs, equalizer_func = input_list
        for multiplier_and_unit in inputs:
            try:
                multiplier, unit = multiplier_and_unit.split()
                multiplier = BotMan.extractMultiplier(multiplier)
                message = equalizer_func(
                    unit,
                    multiplier,
                    group.selected_coins,
                    group.selected_currencies,
                    to_user.language,
                    group.message_show_market_tags,
                )

                tasks.append(
                    update.message.reply_text(
                        PostMan.customizePost(message, group, to_user.language),
                        reply_markup=ReplyKeyboardRemove(),
                    )
                )
            except Exception as x:
                pass
    await asyncio.gather(*tasks, return_exceptions=True)


async def unhandled_error_happened(update: Update, _: CallbackContext | None = None):
    try:
        if update and update.message and isinstance(update.message.chat, Chat):
            account = Account.getById(
                (update.message.chat_id if update.message.chat_id > 0 else update.message.from_user.id),
                should_create=False,
            )
            if account:
                account.change_state(clear_cache=True)
                await update.message.reply_text(
                    botman.error("unhandled_error_happened", account.language),
                    reply_markup=(
                        botman.mainkeyboard(account)
                        if update.message.chat.type.lower() == "private"
                        else ReplyKeyboardRemove()
                    ),
                )
    except Exception as x:
        log("Fucked up error", x, category_name="Unexpected")


async def handle_multimedia_messages(update: Update, context: CallbackContext):
    if await admin_renew_plans(update, context):
        return
    await unknown_command_handler(update, context)


async def handle_cmd_settings(update: Update, _: CallbackContext):
    await botman.show_settings_menu(update)


### Developer options:
async def cmd_add_cmc_api_key(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    args = account.extract_args_if_authorized(context.args)
    if not args:
        return await say_youre_not_allowed(update.message.reply_text, account)

    try:
        botman.crypto_serv.keyman.add(*args)
        await update.message.reply_text(
            f"Added!\n{botman.crypto_serv.keyman.report}",
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))


async def cmd_remove_cmc_api_key(update: Update, context: CallbackContext):
    account = Account.get(update.message.chat)
    args = account.extract_args_if_authorized(context.args)
    if not args:
        return await say_youre_not_allowed(update.message.reply_text, account)
    try:
        botman.crypto_serv.keyman.discard(*args)
        await update.message.reply_text(
            f"Removed!\n{botman.crypto_serv.keyman.report}",
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))


async def cmd_list_cmc_api_key(update: Update, context: CallbackContext):
    if not (account := Account.get(update.message.chat)).is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    try:
        await update.message.reply_text(
            botman.crypto_serv.keyman.state,
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))

async def cmd_switch_usdt_source(update: Update, context: CallbackContext):
    if not (account := Account.get(update.message.chat)).is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    try:
        args = account.extract_args_if_authorized(context.args)
        botman.currency_serv.switch_tether_toman_source(args[0])
        await update.message.reply_text(
            "Successfully switched tether price source.",
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))

async def cmd_set_manual_tether_price(update: Update, context: CallbackContext):
    if not (account := Account.get(update.message.chat)).is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    try:
        args = account.extract_args_if_authorized(context.args)
        botman.currency_serv.set_manual_tether_price(float(args[0]))
        await update.message.reply_text(
            "Successfully set tether price.",
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))

async def cmd_unset_manual_tether_price(update: Update, context: CallbackContext):
    if not (account := Account.get(update.message.chat)).is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    try:
        botman.currency_serv.set_manual_tether_price()
        await update.message.reply_text(
            "Tether price source returned to normal mode.",
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))

async def cmd_set_manual_usd_price(update: Update, context: CallbackContext):
    if not (account := Account.get(update.message.chat)).is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    try:
        args = account.extract_args_if_authorized(context.args)
        botman.currency_serv.set_manual_usd_price(float(args[0]))
        await update.message.reply_text(
            "Successfully set dollar price.",
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))

async def cmd_unset_manual_usd_price(update: Update, context: CallbackContext):
    if not (account := Account.get(update.message.chat)).is_authorized(context.args):
        return await say_youre_not_allowed(update.message.reply_text, account)
    try:
        botman.currency_serv.set_manual_usd_price()
        await update.message.reply_text(
            "Dollar price source returned to navasan.",
            reply_markup=botman.get_admin_primary_keyboard(account),
        )
    except Exception as x:
        await update.message.reply_text(x.__str__(), reply_markup=botman.get_admin_primary_keyboard(account))
