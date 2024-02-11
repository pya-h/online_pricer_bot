from flask import Flask, request, jsonify
import logging
import requests
from webhook.p4ya_telegraph import TelegramBot, TelegramMessage
from decouple import config
from payment.nowpayments import NowpaymentsGateway
from payment.order import Order


# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# read .env configs
VIP_BOT_TOKEN = config('VIP_BOT_TOKEN')
HOST_URL = config('HOST_URL')
BOT_USERNAME = config('VIP_BOT_USERNAME')

bot = TelegramBot(VIP_BOT_TOKEN, BOT_USERNAME, HOST_URL)


### Flask App configs ###
app = Flask(__name__)

# ** Routes **
@app.route('/', methods=['POST'])
def webhook():
    message = TelegramMessage(request.json)  # read necessary message info from telegram object
    # Echo the message back to the user
    cost = Order(buyer=message.by, month_counts=2)  # change this
    gateway = NowpaymentsGateway(buyer_chat_id=message.chat_id, cost=cost, callback_url=f'{bot.host_url}/verify', on_success_url=bot.get_telegram_link())
    response = TelegramMessage.Create(message.chat_id, text=gateway.get_payment_link())
    bot.send(message=response)
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
