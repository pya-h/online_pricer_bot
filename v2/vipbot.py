from flask import Flask, request, jsonify
import logging
import requests
from payagraph.bot import *
from payagraph.containers import *
from payagraph.keyboards import *
from payagraph.job import *

from decouple import config
from payment.nowpayments import NowpaymentsGateway
from payment.order import Order
from db.vip_models import UserStates, Channel
from tools import manuwriter
from typing import Union
from tools.exceptions import *
from db.post import VIPPostManager, PostJob


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

channel_post_manager = VIPPostManager(source_arena_api_key=CURRENCY_SOURCEARENA_TOKEN, coinmarketcap_api_key=COINMARKETCAP_API_KEY, aban_tether_api_key=ABAN_TETHER_TOKEN, bot_username=BOT_USERNAME)

# Read the text resource containing the multilanguage data for the bot texts, messages, commands and etc.
# Also you can write your texts by hard coding but it will be hard implementing multilanguage texts that way,
text_resources = manuwriter.load_json('vip_texts', 'resources')

def plan_channel(bot: TelegramBot, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''Handles the user request on adding a new channel and plan.'''
    user = message.by
    user.change_state(UserStates.SELECT_CHANNEL)
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("just_forward_channel_message", user.language)), None


def select_channel_handler(bot: TelegramBot, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''When bot asks for channel message forward, and user performs an action, this function will handle the action and proceed to next step if data provided is correct.'''
    user = message.by
    response: TelegramMessage = TelegramMessage.Text(target_chat_id=user.chat_id)

    if message.forward_origin and message.forward_origin.type == ChatTypes.CHANNEL:
        user.change_state(UserStates.SELECT_INTERVAL, message.forward_origin)
        response.text = bot.text("select_interval", user.language)
        return response, InlineKeyboard.Arrange(Channel.SupportedIntervals, "int")

    response.text = bot.text("just_forward_channel_message", user.language)
    return response, None


def save_channel_plan(bot: TelegramBot, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    '''After user selects the channel and planning interval, this function will be called and will save and plan the result.'''
    user = callback_query.by
    if not isinstance(user.state_data, ForwardOrigin):
        return TelegramMessage.Text(user.chat_id, bot.text("channel_data_lost", user.language)), None
    channel_data: ForwardOrigin = user.state_data
    callback_query.text=f"{channel_data.__str__()}\nInterval: {callback_query.value} Minutes"
    try:
        channel = user.plan_new_channel(channel_id=channel_data.id, channel_name=channel_data.username or channel_data.title, interval=callback_query.value)
        callback_query.text += "\nChannel and its plan data saved"
        # TODO: **** CREATE PostJob TO UPDATE CHANNEL ON ASKED INTERVAL***
    except NotVIPException:
        callback_query.text = bot.text("not_vip", user.language)
    except Exception as ex:
        callback_query.text = ex.__str__()
    callback_query.replace_on_previous = True
    user.change_state()  # reset user state

    return callback_query, None


# add a latest_crypto_data and latest_currency_data to ChannelPostManager
# create a bot job for channel that updates it every minute(or 5 minute or whatever)
# create postjobs for each channel with its intewrval and pass a re to ChannelPostManager to it

# Parallel Jovbs:
def load_channel_plans(bot: TelegramBot)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    for channel in Channel.Instances:
        if channel.id is not None and channel.interval > 0:
            post_job = PostJob(channel=channel, ) # COMPLETE UWQKKE]
            #TODO:

main_keyboard = {
    'en': Keyboard(text_resources["keywords"]["plan_channel"]["en"]),
    'fa': Keyboard(text_resources["keywords"]["plan_channel"]["fa"])
}

bot = TelegramBot(token=VIP_BOT_TOKEN, username=BOT_USERNAME, host_url=HOST_URL, text_resources=text_resources, _main_keyboard=main_keyboard)

bot.add_state_handler(state=UserStates.SELECT_CHANNEL, handler=select_channel_handler)
bot.add_message_handler(message=bot.keyword('plan_channel'), handler=plan_channel)
bot.add_callback_query_handler(action="int", handler=save_channel_plan)
bot.add_command_handler(command='uptime', handler=lambda bot, message: (TelegramMessage.Text(message.by.chat_id, bot.get_uptime()), None))

bot.prepare_new_parallel_job(ONLINE_PRICE_DEFAULT_INTERVAL / 2, channel_post_manager.update_latest_data)  # This will reload cached data for currency/crypto manager
# Reading cache files everytime by everychannel is a performance risk, and also may fail (Assume two channels try reading cache in the same time.)
# So I designed a Job that will read cache file one time on a specific interval and other channels use the loaded data from memory
# Since the online_pricer_bot itself updates on 10(or whatever) minutes interval, cache files are updated on that interval too, and re-reading the same cache everytime is really a DUMB move,
bot.start_clock()
bot.config_webhook()

@bot.app.route('/verify', methods=['POST'])
def verify_payment():
    print(request.json)
# @app.route('/payment-notification', methods=['POST'])
# def handle_payment_notification():
#     data = request.json

#     # Extract necessary information from the payment notification
#     order_id = data.get('order_id')
#     amount_paid = data.get('amount')
#     currency = data.get('currency')
#     payment_status = data.get('status')

#     # Check if the payment was successful
#     if payment_status == 'completed':
#         # Assume you have a mechanism to map order_id to user_id
#         user_id = get_user_id_from_order_id(order_id)

#         # Update the user's VIP status to True in your database
#         update_user_vip_status(user_id)

#         # Notify the user via Telegram bot about the status update
#         send_telegram_notification(user_id, f"Your payment of {amount_paid} {currency} was successful. You are now a VIP!")

#     return jsonify({'status': 'success'}), 200


### Function ###
# Function to send a notification to the user via Telegram bot
def send_telegram_notification(user_id, message):
    telegram_api_url = f'https://api.telegram.org/bot{VIP_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': user_id,
        'text': message
    }
    response = requests.post(telegram_api_url, json=payload)
    if response.status_code != 200:
        print("Failed to send Telegram notification")



if __name__ == '__main__':
    bot.go(False)  # Run the Flask app
