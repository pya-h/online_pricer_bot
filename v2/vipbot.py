from flask import Flask, request, jsonify
import logging
import requests
from webhook.p4ya_telegraph import *
from decouple import config
from payment.nowpayments import NowpaymentsGateway
from payment.order import Order
from db.vip_models import UserStates, Channel
from tools import manuwriter
from typing import Union


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


main_keyboard = {
    'en': Keyboard(text_resources["keywords"]["plan_channel"]["en"]),
    'fa': Keyboard(text_resources["keywords"]["plan_channel"]["fa"])
}
bot = TelegramBot(token=VIP_BOT_TOKEN, username=BOT_USERNAME, host_url=HOST_URL, text_resources=text_resources, _main_keyboard=main_keyboard)

bot.add_state_handler(state=UserStates.SELECT_CHANNEL, handler=select_channel_handler)
bot.add_message_handler(message=bot.keyword('plan_channel'), handler=plan_channel)

### Flask App configs ###
app = Flask(__name__)

# ** Routes **
@app.route('/', methods=['POST'])
def main():
    message: TelegramMessage | TelegramCallbackQuery = TelegramMessage(request.json) if 'callback_query' not in request.json else TelegramCallbackQuery(request.json)  # read necessary message info from telegram object
    user = message.by

    # Echo the message back to the user
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
    # if account is current;y a vip:
    if user.state == UserStates.NONE:
        user.change_state(UserStates.SELECT_CHANNEL)
    bot.handle(request.json)
    # response = TelegramMessage.Text(user.chat_id)
    # print(user.state)
    # match user.state:
    #     case UserStates.SELECT_CHANNEL:
    #         if not message.forward_origin or message.forward_origin.type != ChatTypes.CHANNEL:
    #             response.text = bot.text("just_forward_channel_message", user.language)
    #             bot.send(response)
    #         else:
    #             print(message.forward_origin)
    #             user.change_state(UserStates.SELECT_INTERVAL, message.forward_origin)
    #             response.text = bot.text("select_interval", user.language)
    #             bot.send(message=response, keyboard=InlineKeyboard.Arrange(Channel.SupportedIntervals, "int"))
    #     case UserStates.SELECT_INTERVAL:
    #         pass
    #     case _:
    #         print("None")
    #         response.text = bot.text("wrong_command", user.language)

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
