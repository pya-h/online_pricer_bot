from flask import request, jsonify
import logging
from payagraph.bot import *
from payagraph.containers import *
from payagraph.keyboards import *
from plus.botplus import *

from decouple import config
from plus.gateway.order import Order
from plus.gateway.nowpayments import NowpaymentsGateway

from plus.models.account import AccountPlus, UserStates
from plus.models.channel import Channel
from plus.models.payment import Payment

from tools import manuwriter
from typing import Union
from tools.exceptions import *
from api.post import PlusPostManager


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

channel_post_manager = PlusPostManager(source_arena_api_key=CURRENCY_SOURCEARENA_TOKEN, coinmarketcap_api_key=COINMARKETCAP_API_KEY, aban_tether_api_key=ABAN_TETHER_TOKEN, bot_username=BOT_USERNAME)

# Read the text resource containing the multilanguage data for the bot texts, messages, commands and etc.
# Also you can write your texts by hard coding but it will be hard implementing multilanguage texts that way,
text_resources = manuwriter.load_json('plus_texts', 'resources')

def start_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    # DO smething such as showing tutorial
    message.text = bot.text("what_todo", message.by.language)
    message.by.change_state()
    return message, None

def planning_section_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request showing user planning panel'''
    user = message.by
    keyboard = bot.keyboard_with_back_key(user.language, [bot.keyword("stop_planning", user.language), bot.keyword("new_planning", user.language)])
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("planning_section", user.language)), keyboard


def config_selections_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request on entering to Price list configuration'''
    user = message.by
    moneys = bot.keyword('moneys')
    keyboard = bot.keyboard_with_back_key(user.language, [moneys['crypto'][user.language], moneys['currency'][user.language], moneys['gold'][user.language]])
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("planning_section", user.language)), keyboard


def select_channel_for_new_planning_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request on adding a new channel and plan.'''
    user = message.by

    if len(user.my_channel_plans()) < user.max_channel_plans():
        user.change_state(UserStates.SELECT_CHANNEL)
        return TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("just_forward_channel_message", user.language)), None
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("max_channel_plans_reached", user.language) % (user.max_channel_plans(), )), None

def list_channels_for_stop_plan_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request on adding a new channel and plan.'''
    user = message.by
    user_channels: list[Channel] = list(filter(lambda channel: channel.owner_id == user.chat_id, Channel.Instances.values()))
    keyboard = None
    if user_channels:
        call_data = lambda value: {"a": "dlpl", "v": value}
        keyboard_rows = [InlineKey(f"{channel.title} - @{channel.name if channel.name else ''}", callback_data=call_data(channel.id)) for channel in user_channels]
        keyboard = InlineKeyboard(*keyboard_rows)
        response = TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("click_channel_to_delete", user.language))
    else:
        response = TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("no_channels_to_disable", user.language))
    return response, keyboard



def config_gold_list_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request selecting desired golds'''
    user = message.by
    caption = bot.text("list_types")["gold"][user.language] + "\n\n" + bot.text("selection_hint", user.language)
    keyboard = InlineKeyboard.CreateDynamicList("cg-gold", bot.post_manager.currencyManager.GoldsInPersian,
                                                                   user.desired_currencies, user.language=='fa')
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=caption), keyboard

def config_currency_list_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request selecting desired currencies'''
    user = message.by
    caption = bot.text("list_types")["currency"][user.language] + "\n\n" + bot.text("selection_hint", user.language)
    keyboard = InlineKeyboard.CreateDynamicList("cg-curr", bot.post_manager.currencyManager.CurrenciesInPersian,
                                                                         user.desired_currencies, user.language=='fa')
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=caption), keyboard


def config_crypto_list_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request selecting desired cryptocurrencies'''
    user = message.by
    caption = bot.text("list_types")["crypto"][user.language] + "\n\n" + bot.text("selection_hint", user.language)
    keyboard = InlineKeyboard.CreateDynamicList("cg-cryp", bot.post_manager.cryptoManager.CoinsInPersian,
                                                                         user.desired_coins)
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=caption), keyboard


def select_channel_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''When bot asks for channel message forward, and user performs an action, this function will handle the action and proceed to next step if data provided is correct.'''
    user = message.by
    response: TelegramMessage = TelegramMessage.Text(target_chat_id=user.chat_id)

    if message.forward_origin and message.forward_origin.type == ChatTypes.CHANNEL:
        user.change_state(UserStates.SELECT_INTERVAL, message.forward_origin)
        response.text = bot.text("select_interval", user.language)
        return response, InlineKeyboard.Arrange(Channel.SupportedIntervals, "int")

    response.text = bot.text("just_forward_channel_message", user.language)
    return response, None


def chnage_language_handler(bot: TelegramBotPlus, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    user = message.by
    lang = message.text[1:3].lower()
    if lang != 'en' and lang != 'fa':  # its rare but its good to make sure
        return TelegramMessage.Text(user.chat_id, "Unknown languege!"), None
    try:
        user.language = lang
        user.save()
    except:
        return TelegramMessage.Text(user.chat_id, bot.text('cant_change_language', user.language)), None
    return TelegramMessage.Text(user.chat_id, bot.text("what_todo", user.language)), None

def save_channel_plan(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''After user selects the channel and planning interval, this function will be called and will save and plan the result.'''
    user = callback_query.by
    if not isinstance(user.state_data, ForwardOrigin):
        return TelegramMessage.Text(user.chat_id, bot.text("channel_data_lost", user.language)), None
    channel_data: ForwardOrigin = user.state_data
    # callback_query.text=f"{channel_data.__str__()}\nInterval: {callback_query.value} Minutes"
    try:
        channel = user.plan_new_channel(channel_id=channel_data.id, channel_name=channel_data.username, channel_title=channel_data.title, interval=callback_query.value)
        callback_query.text = bot.text('channel_planned_succesfully', user.language) % (channel.title, channel.interval, )
        bot.send(TelegramMessage.Text(user.chat_id, bot.text("add_bot_to_channel_as_admin", user.language)))
        bot.prepare_new_post_job(channel, short_text=True) # creates post job and starts it # Check short_text
    except NotPlusException:
        callback_query.text = bot.text("not_plus", user.language)
    except Exception as ex:
        callback_query.text = ex.__str__()
    callback_query.replace_on_previous = True
    user.change_state()  # reset user state

    return callback_query, None


def update_desired_crypto_list(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Add/Remove a this coin item into user's desired list. So that the user see this item's price on next posts'''
    user = callback_query.by
    coin_symbol = callback_query.value
    if coin_symbol in user.desired_coins:
        user.desired_coins.remove(coin_symbol)
    else:
        user.desired_coins.append(coin_symbol)
    callback_query.replace_on_previous = True
    user.save()
    return callback_query, InlineKeyboard.CreateDynamicList("cg-cryp", bot.post_manager.cryptoManager.CoinsInPersian, user.desired_coins)

def update_desired_currency_list(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Add/Remove a currency item into user's desired list. So that the user see this item's price on next posts'''
    user = callback_query.by
    currency_symbol = callback_query.value
    if currency_symbol in user.desired_currencies:
        user.desired_currencies.remove(currency_symbol)
    else:
        user.desired_currencies.append(currency_symbol)
    callback_query.replace_on_previous = True
    user.save()
    return callback_query, InlineKeyboard.CreateDynamicList("cg-curr", bot.post_manager.currencyManager.CurrenciesInPersian, user.desired_currencies, user.language=='fa')

def update_desired_gold_list(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Add/Remove a gold item into user's desired list. So that the user see this item's price on next posts'''
    user = callback_query.by
    gold_symbol = callback_query.value
    if gold_symbol in user.desired_currencies:
        user.desired_currencies.remove(gold_symbol)
    else:
        user.desired_currencies.append(gold_symbol)
    callback_query.replace_on_previous = True
    user.save()
    return callback_query, InlineKeyboard.CreateDynamicList("cg-gold", bot.post_manager.currencyManager.GoldsInPersian, user.desired_currencies, user.language=='fa')


def stop_channel_plan_handler(bot: TelegramBotPlus, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
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
    chat_id = TelegramMessage.GetChatId(update)
    user = AccountPlus.Get(chat_id)
    
    if not user.is_member_plus():
        order = Order(buyer=user, months_counts=2)  # change this
        gateway = NowpaymentsGateway(buyer_chat_id=chat_id, order=order, callback_url=f'{bot.host_url}/verify', on_success_url=bot.get_telegram_link())
        response = TelegramMessage.Text(chat_id, text=gateway.get_payment_link())
        bot.send(message=response)

        return False
    return True


main_keyboard = {
    'en': Keyboard([text_resources["keywords"]["planning_section"]["en"], text_resources["keywords"]["config_selections"]["en"]]),
    'fa': Keyboard([text_resources["keywords"]["planning_section"]["fa"], text_resources["keywords"]["config_selections"]["fa"]])
}

bot = TelegramBotPlus(token=VIP_BOT_TOKEN, username=BOT_USERNAME, host_url=HOST_URL, text_resources=text_resources, _main_keyboard=main_keyboard, post_manager=channel_post_manager)

bot.add_cancel_key(bot.keyword('main_menu'))
bot.add_cancel_key(bot.cmd('cancel'))

bot.add_middleware(check_channels_membership)
bot.add_middleware(check_account_is_plus_member)

bot.add_state_handler(state=UserStates.SELECT_CHANNEL, handler=select_channel_handler)
bot.add_message_handler(message=bot.keyword('planning_section'), handler=planning_section_handler)
bot.add_message_handler(message=bot.keyword('config_selections'), handler=config_selections_handler)

bot.add_message_handler(message=bot.keyword('new_planning'), handler=select_channel_for_new_planning_handler)
bot.add_message_handler(message=bot.keyword('stop_planning'), handler=list_channels_for_stop_plan_handler)

bot.add_message_handler(message=bot.keyword('moneys')['gold'], handler=config_gold_list_handler)
bot.add_message_handler(message=bot.keyword('moneys')['currency'], handler=config_currency_list_handler)
bot.add_message_handler(message=bot.keyword('moneys')['crypto'], handler=config_crypto_list_handler)


bot.add_callback_query_handler(action="int", handler=save_channel_plan)
bot.add_callback_query_handler(action="cg-cryp", handler=update_desired_crypto_list)
bot.add_callback_query_handler(action="cg-gold", handler=update_desired_gold_list)
bot.add_callback_query_handler(action="cg-curr", handler=update_desired_currency_list)

bot.add_callback_query_handler(action="dlpl", handler=stop_channel_plan_handler)


bot.add_command_handler(command='uptime', handler=lambda bot, message: (TelegramMessage.Text(message.chat_id, bot.get_uptime()), None))
bot.add_command_handler(command=bot.cmd('lang_en'), handler=chnage_language_handler)
bot.add_command_handler(command=bot.cmd('lang_fa'), handler=chnage_language_handler)
bot.add_command_handler(command=bot.cmd('start'), handler=start_handler)

bot.prepare_new_parallel_job(ONLINE_PRICE_DEFAULT_INTERVAL / 2, channel_post_manager.update_latest_data)  # This will reload cached data for currency/crypto manager
# Reading cache files everytime by everychannel is a performance risk, and also may fail (Assume two channels try reading cache in the same time.)
# So I designed a Job that will read cache file one time on a specific interval and other channels use the loaded data from memory
# Since the online_pricer_bot itself updates on 10(or whatever) minutes interval, cache files are updated on that interval too, and re-reading the same cache everytime is really a DUMB move,
bot.load_channels_and_plans()

bot.start_clock()

bot.config_webhook()

@bot.app.route('/verify', methods=['POST'])
def verify_payment():
    print(request.json)

@bot.app.route('/payment-notification', methods=['POST'])
def handle_payment_notification(bot: TelegramBotPlus):
    # Extract necessary information from the payment notification
    payment = Payment(request.json).save()
    # Check if the payment was successful
    if payment.status == 'finished':
        # Assume you have a mechanism to map order_id to user_id
        account = AccountPlus.Get(payment.payer_chat_id)
        account.updgrade(payment.plus_plan.id)

        # Notify the user via Telegram bot about the status update
        bot.send(TelegramMessage(payment.payer_chat_id, f"Your payment of {payment.paid_amount} {payment.currency} was successful. You are now a VIP!"))

    return jsonify({'status': 'success'}), 200


if __name__ == '__main__':
    bot.go(False)  # Run the Flask app
