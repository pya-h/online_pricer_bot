from flask import request, jsonify
import logging
from payagraph.bot import *
from payagraph.containers import *
from payagraph.keyboards import *
from plus.bot import *

from decouple import config
from plus.gateway.order import Order
from plus.gateway.nowpayments import NowpaymentsGateway

from plus.models.account import AccountPlus, UserStates
from plus.models.channel import Channel
from plus.models.payment import Payment

from tools import manuwriter
from typing import Union
from tools.exceptions import *
from plus.services.post import PostServicePlus
from tools.mathematix import persianify

### TODO: GOLBAL TODOS
### **** TODO: CREATE JOBS FOR GARBAGE COLLECTION OF MODELS **** ###
### **** TODO: ON BOT STARTED PREVIOUS POST JOBS MUST START **** ###
### **** TODO: ON ENGLISH LANGUAGE< CONFIG CURRENCY SHOWS GOLDS TOO **** ###



# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# read .env configs
COINMARKETCAP_API_KEY = config('COINMARKETCAP_API_KEY')
CURRENCY_SOURCEARENA_TOKEN = config('CURRENCY_TOKEN')
ABAN_TETHER_TOKEN = config('ABAN_TETHER_TOKEN')
# You bot data
VIP_BOT_TOKEN = config('VIP_BOT_TOKEN')
HOST_URL = config('HOST_URL')
BOT_USERNAME = config('VIP_BOT_USERNAME')
ONLINE_PRICE_DEFAULT_INTERVAL = float(config('MAIN_SCHEDULER_DEFAULT_INTERVAL', 10))

channel_post_service = PostServicePlus(source_arena_api_key=CURRENCY_SOURCEARENA_TOKEN, coinmarketcap_api_key=COINMARKETCAP_API_KEY, aban_tether_api_key=ABAN_TETHER_TOKEN, bot_username=BOT_USERNAME)

# Read the text resource containing the multilanguage data for the bot texts, messages, commands and etc.
# Also you can write your texts by hard coding but it will be hard implementing multilanguage texts that way,
text_resources = manuwriter.load_json('plus_texts', 'plus/resources')

def get_language_select_menu(bot: TelegramBotPlus, account: AccountPlus) -> Union[GenericMessage, InlineKeyboard]:
    return GenericMessage.Text(account.chat_id, bot.text("welcome", account.language) % (account.firstname, )), bot.language_glass_buttons(account.language)

def start_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    # DO smething such as showing tutorial
    message.by.change_state(UserStates.SELECT_LANGUAGE)
    return get_language_select_menu(bot, message.by)

def planning_section_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request showing user planning panel'''
    user = message.by
    keyboard = bot.keyboard_with_back_key(user.language, [bot.keyword("stop_planning", user.language), bot.keyword("new_planning", user.language)])
    return GenericMessage.Text(target_chat_id=user.chat_id, text=bot.text("planning_section", user.language)), keyboard


def config_selections_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request on entering to Price list configuration'''
    user = message.by
    moneys = bot.keyword('moneys')
    keyboard = bot.keyboard_with_back_key(user.language, [moneys['crypto'][user.language], moneys['currency'][user.language], moneys['gold'][user.language]])
    return GenericMessage.Text(target_chat_id=user.chat_id, text=bot.text("config_selections_section", user.language)), keyboard


def select_channel_for_new_planning_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request on adding a new channel and plan.'''
    user = message.by

    if len(user.my_channel_plans()) < user.max_channel_plans():
        user.change_state(UserStates.SELECT_CHANNEL)
        return GenericMessage.Text(target_chat_id=user.chat_id, text=bot.text("just_forward_channel_message", user.language)), None
    return GenericMessage.Text(target_chat_id=user.chat_id, text=bot.text("max_channel_plans_reached", user.language) % (user.max_channel_plans(), )), None

def list_channels_for_stop_plan_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request on adding a new channel and plan.'''
    user = message.by
    user_channels: list[Channel] = list(filter(lambda channel: channel.owner_id == user.chat_id, Channel.Instances.values()))
    keyboard = None
    if user_channels:
        call_data = lambda value: {"a": "dl-chnpl", "v": value}
        keyboard_rows = [GlassButton(f"{channel.title} - @{channel.name if channel.name else ''}", callback_data=call_data(channel.id)) for channel in user_channels]
        keyboard = InlineKeyboard(*keyboard_rows)
        response = GenericMessage.Text(target_chat_id=user.chat_id, text=bot.text("click_channel_to_delete", user.language))
    else:
        response = GenericMessage.Text(target_chat_id=user.chat_id, text=bot.text("no_channels_to_disable", user.language))
    return response, keyboard



def config_gold_list_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request selecting desired golds'''
    user = message.by
    caption = bot.text("list_types")["gold"][user.language] + "\n\n" + bot.text("selection_hint", user.language)
    keyboard = InlineKeyboard.CreateDynamicList("cg-gold", bot.post_service.currency_service.GoldsInPersian,
                                                                   user.desired_currencies, user.language=='fa')
    return GenericMessage.Text(target_chat_id=user.chat_id, text=caption), keyboard

def config_currency_list_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request selecting desired currencies'''
    user = message.by
    caption = bot.text("list_types")["currency"][user.language] + "\n\n" + bot.text("selection_hint", user.language)
    keyboard = InlineKeyboard.CreateDynamicList("cg-curr", bot.post_service.currency_service.NationalCurrenciesInPersian,
                                                                         user.desired_currencies, user.language=='fa')
    return GenericMessage.Text(target_chat_id=user.chat_id, text=caption), keyboard


def config_crypto_list_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request selecting desired cryptocurrencies'''
    user = message.by
    caption = bot.text("list_types")["crypto"][user.language] + "\n\n" + bot.text("selection_hint", user.language)
    keyboard = InlineKeyboard.CreateDynamicList("cg-cryp", bot.post_service.crypto_service.CoinsInPersian,
                                                                         user.desired_coins)
    return GenericMessage.Text(target_chat_id=user.chat_id, text=caption), keyboard


def select_channel_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''When bot asks for channel message forward, and user performs an action, this function will handle the action and proceed to next step if data provided is correct.'''
    user = message.by
    response: GenericMessage = GenericMessage.Text(target_chat_id=user.chat_id)

    if message.forward_origin and message.forward_origin.type == ChatTypes.CHANNEL:
        user.change_state(UserStates.SELECT_INTERVAL, message.forward_origin)
        response.text = bot.text("select_interval", user.language)
        return response, InlineKeyboard.Arrange(Channel.SupportedIntervals, "int")

    response.text = bot.text("just_forward_channel_message", user.language)
    return response, None

def enable_channel_plan(bot: TelegramBotPlus, user: AccountPlus, channel: Channel):
    bot.send(GenericMessage.Text(user.chat_id, bot.text("add_bot_to_channel_as_admin", user.language)))
    bot.prepare_new_post_job(channel, short_text=True) # creates post job and starts it # Check short_text


def switch_langauge_query_handler(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[GenericMessage, Keyboard|InlineKeyboard]:
    # use prepare_membership_gateway
    user = callback_query.by
    lang = callback_query.value.lower() # language value
    keyboard = None
    if lang != "fa" and lang != "en":
        callback_query.text = bot.text("invalid_language", user.language)
        keyboard = bot.language_glass_buttons(user.language)
        callback_query.replace_on_previous = True
    else:
        callback_query.replace_on_previous = False
        user.language = lang
        user.change_state()
        try:
            user.save()
            callback_query.text = bot.text("switched_language", user.language)
        except:
            return GenericMessage.Text(user.chat_id, bot.text('cant_change_language', user.language)), None

    return callback_query, keyboard


def set_language_command_handler(bot: TelegramBotPlus, message: GenericMessage) -> Union[GenericMessage, Keyboard|InlineKeyboard]:
    user = message.by
    lang = message.text[1:3].lower()
    if lang != 'en' and lang != 'fa':  # its rare but its good to make sure
        return GenericMessage.Text(user.chat_id, bot.text("invalid_language", user.language)), None
    user.language = lang
    try:
        user.save()
    except:
        return GenericMessage.Text(user.chat_id, bot.text('cant_change_language', user.language)), None
    return GenericMessage.Text(user.chat_id, bot.text("what_todo", user.language)), None


def save_channel_plan(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''After user selects the channel and planning interval, this function will be called and will save and plan the result.'''
    user = callback_query.by
    if not isinstance(user.state_data, ForwardOrigin):
        return GenericMessage.Text(user.chat_id, bot.text("channel_data_lost", user.language)), None
    channel_data: ForwardOrigin = user.state_data
    keyboard = None
    # callback_query.text=f"{channel_data.__str__()}\nInterval: {callback_query.value} Minutes"
    try:
        channel = user.plan_new_channel(channel_id=channel_data.id, channel_name=channel_data.username, channel_title=channel_data.title, interval=callback_query.value)
        callback_query.text = bot.text('channel_planned_succesfully', user.language) % (channel.title, channel.interval, )
        if user.is_member_plus():
            enable_channel_plan(bot, user, channel)
        else:
            callback_query.text += "\n\n" + bot.text("not_plus", user.language)
            keyboard = bot.list_all_plans(user.language)
            if not keyboard:
                callback_query.text = bot.text("no_plans_available", user.language)
    except NotPlusException:
        callback_query.text = bot.text("not_plus", user.language)
    except Exception as ex:
        callback_query.text = ex.__str__()
    callback_query.replace_on_previous = True
    user.change_state()  # reset user state

    return callback_query, keyboard


def create_payment_link(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[GenericMessage, Keyboard|InlineKeyboard]:
    # use prepare_membership_gateway
    user = callback_query.by
    order = Order(buyer=user, plus_plan_id=int(callback_query.value))  # change this
    gateway = NowpaymentsGateway(order=order, callback_url=f'{bot.host_url}/verify', on_success_url=bot.get_telegram_link())
    payment_link_keyboard = InlineKeyboard(GlassButton(bot.text("pay", user.language), url=gateway.get_payment_link()))
    callback_query.text = order.plus_plan.fill_template_string(bot.text("payment_description", user.language), user.language)
    callback_query.replace_on_previous = True
    return callback_query, payment_link_keyboard

def update_desired_crypto_list(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Add/Remove a this coin item into user's desired list. So that the user see this item's price on next posts'''
    user = callback_query.by
    coin_symbol = callback_query.value
    if coin_symbol in user.desired_coins:
        user.desired_coins.remove(coin_symbol)
    else:
        user.desired_coins.append(coin_symbol)
    callback_query.replace_on_previous = True
    user.save()
    return callback_query, InlineKeyboard.CreateDynamicList("cg-cryp", bot.post_service.crypto_service.CoinsInPersian, user.desired_coins)

def update_desired_currency_list(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Add/Remove a currency item into user's desired list. So that the user see this item's price on next posts'''
    user = callback_query.by
    currency_symbol = callback_query.value
    if currency_symbol in user.desired_currencies:
        user.desired_currencies.remove(currency_symbol)
    else:
        user.desired_currencies.append(currency_symbol)
    callback_query.replace_on_previous = True
    user.save()
    return callback_query, InlineKeyboard.CreateDynamicList("cg-curr", bot.post_service.currency_service.CurrenciesInPersian, user.desired_currencies, user.language=='fa')

def update_desired_gold_list(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Add/Remove a gold item into user's desired list. So that the user see this item's price on next posts'''
    user = callback_query.by
    gold_symbol = callback_query.value
    if gold_symbol in user.desired_currencies:
        user.desired_currencies.remove(gold_symbol)
    else:
        user.desired_currencies.append(gold_symbol)
    callback_query.replace_on_previous = True
    user.save()
    return callback_query, InlineKeyboard.CreateDynamicList("cg-gold", bot.post_service.currency_service.GoldsInPersian, user.desired_currencies, user.language=='fa')


def delete_channel_plan_handler(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[GenericMessage, Keyboard|InlineKeyboard]:
    '''Stop the planning of the selected channel'''
    user = callback_query.by
    channel = None
    try:
        channel_id = int(callback_query.value)
        channel: Channel = Channel.Instances[channel_id]
    except:
        pass

    if channel:
        if channel.stop_plan():
            callback_query.text = bot.text("channel_plan_disabled")[user.language] % (channel.title, )
            bot.cancel_postjob(channel.id)
        else:
            callback_query.text = bot.text("channel_plan_cant_stop")[user.language]

    else:
        callback_query.text = bot.text("channel_not_found")[user.language]

    callback_query.replace_on_previous = True
    return callback_query, None

# Middlewares
def ask_language_first(bot: TelegramBotPlus, update: dict) -> bool:
    '''This middleware actual use is on first start, when the user skips selecting language, this will put the question in repeat until the user selects a language.'''
    account = GenericMessage.GetAccountDirectly(update)
    if not account or account.state != UserStates.SELECT_LANGUAGE:
        return True
    # if 'callback_query' in update:
    #     cq = TelegramCallbackQuery(update)
    #     if cq.action == 's-l':
    #         return True
    bot.send(*get_language_select_menu(bot, account))
    return False # prevent handler from going on, because user first must select the language


def check_channels_membership(bot: TelegramBotPlus, update: dict) -> bool:
    '''channels = array(FIRST_2_JOIN_CHANNEL_ID => array('name' => "Persian College", 'url' => FIRST_2_JOIN_CHANNEL_URL),
        PERSIAN_PROJECT_CHANNEL_ID => array('name' => "Persian Project", 'url' => PERSIAN_PROJECT_CHANNEL_URL));

    all_joined = true;
    user_id = isset(update[CALLBACK_QUERY]) ? update[CALLBACK_QUERY]['from']['id'] : update['message']['from']['id'];
    channel_list_menu = array(array());
    current_row = 0;
    foreach(channels as channel_id => params) {
        res = callMethod(
            METH_GET_CHAT_MEMBER,
            CHAT_ID, channel_id,
            'user_id', user_id
        );
        res = json_decode(res, true);
        all_joined = all_joined && (strtolower(res['result']['status'] ?? USER_NOT_A_MEMBER) != USER_NOT_A_MEMBER);
        channel_list_menu[current_row][] = array(TEXT_TAG => params['name'], INLINE_URL_TAG => params['url']);
        if(count(channel_list_menu[current_row]) >= 2) {
            channel_list_menu[] = array();
            current_row++;
        }
    }
    channel_list_menu[] = array(array(TEXT_TAG => 'بررسی عضویت', CALLBACK_DATA => wrapInlineButtonData(INLINE_ACTION_VERIFY_ACCOUNT)));
    if(all_joined) {
        if (isset(update['message']))
            handleCasualMessage(update);
        else if (isset(update[CALLBACK_QUERY]))
            handleCallbackQuery(update);
    } else {
        callMethod(METH_SEND_MESSAGE,
            CHAT_ID, user_id,
            TEXT_TAG, 'قبل از هر چیزی لازمه که در کانال های ما جوین شی',
            KEYBOARD, array('remove_keyboard' => true)
        );
        callMethod(METH_SEND_MESSAGE,
            CHAT_ID, user_id,
            TEXT_TAG, 'بعد از اینکه عضو کانال های زیر شدی، بررسی عضویت رو بزن:',
            KEYBOARD, array(INLINE_KEYBOARD => channel_list_menu)
        );
    }'''
    return True

def check_account_is_plus_member(bot: TelegramBotPlus, update: dict) -> bool:
    chat_id = GenericMessage.GetChatId(update)
    user = AccountPlus.Get(chat_id)

    if not user.is_member_plus():
        order = Order(buyer=user, months_counts=2)  # change this
        # gateway = NowpaymentsGateway(buyer_chat_id=chat_id, order=order, callback_url=f'{bot.host_url}/verify', on_success_url=bot.get_telegram_link())
        # FIXME: Send upgrade message
        # response = GenericMessage.Text(chat_id, text=gateway.get_payment_link())
        # bot.send(message=response)

        return False
    return True


main_keyboard = {
    'en': Keyboard([text_resources["keywords"]["planning_section"]["en"], text_resources["keywords"]["config_selections"]["en"]]),
    'fa': Keyboard([text_resources["keywords"]["planning_section"]["fa"], text_resources["keywords"]["config_selections"]["fa"]])
}

bot = TelegramBotPlus(token=VIP_BOT_TOKEN, username=BOT_USERNAME, host_url=HOST_URL, text_resources=text_resources, _main_keyboard=main_keyboard, post_service=channel_post_service)

bot.add_cancel_key(bot.keyword('main_menu'))
bot.add_cancel_key(bot.cmd('cancel'))

bot.add_middleware(check_channels_membership)
bot.add_middleware(ask_language_first)

bot.add_state_handler(state=UserStates.SELECT_CHANNEL, handler=select_channel_handler)
bot.add_message_handler(message=bot.keyword('planning_section'), handler=planning_section_handler)
bot.add_message_handler(message=bot.keyword('config_selections'), handler=config_selections_handler)

bot.add_message_handler(message=bot.keyword('new_planning'), handler=select_channel_for_new_planning_handler)
bot.add_message_handler(message=bot.keyword('stop_planning'), handler=list_channels_for_stop_plan_handler)

bot.add_message_handler(message=bot.keyword('moneys')['gold'], handler=config_gold_list_handler)
bot.add_message_handler(message=bot.keyword('moneys')['currency'], handler=config_currency_list_handler)
bot.add_message_handler(message=bot.keyword('moneys')['crypto'], handler=config_crypto_list_handler)

bot.add_callback_query_handler(action="s-l", handler=switch_langauge_query_handler)
bot.add_callback_query_handler(action="int", handler=save_channel_plan)
bot.add_callback_query_handler(action="cg-cryp", handler=update_desired_crypto_list)
bot.add_callback_query_handler(action="cg-gold", handler=update_desired_gold_list)
bot.add_callback_query_handler(action="cg-curr", handler=update_desired_currency_list)
bot.add_callback_query_handler(action="buy+plan", handler=create_payment_link)
bot.add_callback_query_handler(action="dl-chnpl", handler=delete_channel_plan_handler)

# TODO: Make this Admin command
bot.add_command_handler(command='uptime', handler=lambda bot, message: (GenericMessage.Text(message.chat_id, bot.get_uptime()), None))
bot.add_command_handler(command=bot.cmd('lang_en'), handler=set_language_command_handler)
bot.add_command_handler(command=bot.cmd('lang_fa'), handler=set_language_command_handler)
bot.add_command_handler(command=bot.cmd('start'), handler=start_handler)

bot.prepare_new_parallel_job(ONLINE_PRICE_DEFAULT_INTERVAL / 2, channel_post_service.update_latest_data)  # This will reload cached data for currency/crypto service
# Reading cache files everytime by everychannel is a performance risk, and also may fail (Assume two channels try reading cache in the same time.)
# So I designed a Job that will read cache file one time on a specific interval and other channels use the loaded data from memory
# Since the online_pricer_bot itself updates on 10(or whatever) minutes interval, cache files are updated on that interval too, and re-reading the same cache everytime is really a DUMB move,
bot.load_channels_and_plans()

bot.start_clock()

bot.config_webhook()

# @bot.app.route('/verify', methods=['POST'])
# def verify_payment():
#     manuwriter.log(request.json.__str__(), category_name="PaymentVerificationJSON")
#     # Extract necessary information from the payment notification
#     payment = Payment(request.json).save()
#     # Check if the payment was successful
#     if payment.status == 'finished':
#         try:
#             # Assume you have a mechanism to map order_id to user_id
#             account = AccountPlus.Get(payment.payer_chat_id)
#             account.updgrade(payment.plus_plan.id)

#             # Notify the user via Telegram bot about the status update
#             bot.send(GenericMessage.Text(payment.payer_chat_id, bot.text('plus_plan_activated_for_u', account.language) \
#                 % (payment.plus_plan.title if account.language.lower() == 'fa' \
#                     else payment.plus_plan.title_en, \
#                     persianify(account.plus_end_date.strftime("%Y-%M-%d")) if account.language == 'fa' \
#                     else account.plus_end_date.strftime("%Y-%M-%d") )))
#             for channel in account.my_channel_plans():
#                 ### TODO: Edit this for when We add garbage collect for channels
#                 bot.prepare_new_post_job(channel)
#             manuwriter.log(f"\npayer_chat_id:{payment.payer_chat_id}\n\tplan_id:{payment.plus_plan.id}\n\tplan_title:{payment.plus_plan.title_en}\n" +\
#                 f"\tpayment_id: {payment.id}\n\torder_id: {payment.order_id}", category_name='payments_success')
#         except Exception as ex:
#             manuwriter.log(f"Payment finished but encountered error while upgrading the user.\n\tpayer_chat_id:{payment.payer_chat_id}" +\
#                 f"\n\tplan_id:{payment.plus_plan.id}\n\tplan_title_fa:{payment.plus_plan.title}\n\tplan_title_en:{payment.plus_plan.title_en}\n\tpayment_id: {payment.id}\n\torder_id: {payment.order_id}", ex, 'payments_failed')
#             payment_info = f"Payment ID: {payment.id}\nOrder ID: {payment.order_id}\nChat ID: {payment.payer_chat_id}"
#             bot.send(GenericMessage.Text(account.chat_id, bot.text("payment_failure", account.language) + f"\n\n{payment_info}"))
#     return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    bot.go()  # Run the Flask app
