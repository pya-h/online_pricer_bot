from flask import Flask, request, jsonify
import logging
import requests
from payagraph.bot import *
from payagraph.containers import *
from payagraph.keyboards import *

from decouple import config
from payment.nowpayments import NowpaymentsGateway
from payment.order import Order
from db.vip_models import UserStates, Channel
from tools import manuwriter
from typing import Union
from tools.exceptions import *


# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# read .env configs
VIP_BOT_TOKEN = config('VIP_BOT_TOKEN')
HOST_URL = config('HOST_URL')
BOT_USERNAME = config('VIP_BOT_USERNAME')

text_resources = manuwriter.load_json('vip_texts', 'resources')

def plan_channel(bot: TelegramBot, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    user = message.by
    user.change_state(UserStates.SELECT_CHANNEL)
    return TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("just_forward_channel_message", user.language)), None


def select_channel_handler(bot: TelegramBot, message: TelegramMessage) -> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    user = message.by
    response: TelegramMessage = TelegramMessage.Text(target_chat_id=user.chat_id)

    if message.forward_origin and message.forward_origin.type == ChatTypes.CHANNEL:
        user.change_state(UserStates.SELECT_INTERVAL, message.forward_origin)
        response.text = bot.text("select_interval", user.language)
        return response, InlineKeyboard.Arrange(Channel.SupportedIntervals, "int")

    response.text = bot.text("just_forward_channel_message", user.language)
    return response, None


def save_channel_plan(bot: TelegramBot, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    user = callback_query.by
    if not isinstance(user.state_data, ForwardOrigin):
        return TelegramMessage.Text(user.chat_id, bot.text("channel_data_lost", user.language)), None
    channel_data: ForwardOrigin = user.state_data
    callback_query.text=f"{channel_data.__str__()}\nInterval: {callback_query.value} Minutes"
    try:
        channel = user.plan_new_channel(channel_id=channel_data.id, channel_name=channel_data.username or channel_data.title, interval=callback_query.value)
        callback_query.text += "\nChannel and its plan data saved"
    except NotVIPException:
        callback_query.text = bot.text("not_vip", user.language)
    except Exception as ex:
        callback_query.text = ex.__str__()
    callback_query.replace_on_previous = True
    user.change_state()  # reset user state

    return callback_query, None

# def show_uptime_handler(bot: TelegramBot, callback_query: TelegramCallbackQuery)-> Union[TelegramMessage, Keyboard|InlineKeyboard]::
def job_test(bot: TelegramBot, message: TelegramMessage)-> Union[TelegramMessage, Keyboard|InlineKeyboard]:
    from time import time
    def test(user: VIPAccount):
        bot.send(TelegramMessage.Text(user.chat_id, str(time()//60)))
    bot.parallels.append(
        ParallelJob(1, test, message.by).go()
    )
    return TelegramMessage.Text(message.by.chat_id, f"Job planned starting from now: {time()} sec(s)"), None
main_keyboard = {
    'en': Keyboard(text_resources["keywords"]["plan_channel"]["en"]),
    'fa': Keyboard(text_resources["keywords"]["plan_channel"]["fa"])
}

bot = TelegramBot(token=VIP_BOT_TOKEN, username=BOT_USERNAME, host_url=HOST_URL, text_resources=text_resources, _main_keyboard=main_keyboard)

bot.add_state_handler(state=UserStates.SELECT_CHANNEL, handler=select_channel_handler)
bot.add_message_handler(message=bot.keyword('plan_channel'), handler=plan_channel)
bot.add_callback_query_handler(action="int", handler=save_channel_plan)
bot.add_command_handler(command='uptime', handler=lambda bot, message: (TelegramMessage.Text(message.by.chat_id, bot.get_uptime()), None))
bot.add_command_handler(command='job', handler=job_test)

bot.start_clock()
### Flask App configs ###
app = Flask(__name__)

# ** Routes **
@app.route('/', methods=['POST'])
def main():

    # code below must be add to middlewares
    '''if not user.has_vip_privileges():
        order = Order(buyer=user, months_counts=2)  # change this
        gateway = NowpaymentsGateway(buyer_chat_id=message.chat_id, order=order, callback_url=f'{bot.host_url}/verify', on_success_url=bot.get_telegram_link())
        response = TelegramMessage.Text(message.chat_id, text=gateway.get_payment_link())
        bot.send(message=response)

        ### TEMP
        hint = TelegramMessage.Text(target_chat_id=user.chat_id, text=bot.text("select_channel", user.language))
        bot.send(hint)
        user.change_state(UserStates.SELECT_CHANNEL)

        return jsonify({'status': 'ok'})'''

    bot.handle(request.json)

    return jsonify({'status': 'ok'})

@app.route('/verify', methods=['POST'])
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
    app.run(debug=True)  # Run the Flask app
