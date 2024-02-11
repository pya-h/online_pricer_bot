from flask import Flask, request, jsonify
import logging
import requests
from telegrambot import TelegramBot, TelegramMessage
from decouple import config


# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# read .env configs
VIP_BOT_TOKEN = config('VIP_BOT_TOKEN')
bot = TelegramBot(VIP_BOT_TOKEN)

# Initialize Flask app
app = Flask(__name__)

# Define your Telegram bot token
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

# Define the endpoint for handling payment notifications from NowPayments
@app.route('/payment-notification', methods=['POST'])
def handle_payment_notification():
    data = request.json

    # Extract necessary information from the payment notification
    order_id = data.get('order_id')
    amount_paid = data.get('amount')
    currency = data.get('currency')
    payment_status = data.get('status')

    # Check if the payment was successful
    if payment_status == 'completed':
        # Assume you have a mechanism to map order_id to user_id
        user_id = get_user_id_from_order_id(order_id)

        # Update the user's VIP status to True in your database
        update_user_vip_status(user_id)

        # Notify the user via Telegram bot about the status update
        send_telegram_notification(user_id, f"Your payment of {amount_paid} {currency} was successful. You are now a VIP!")

    return jsonify({'status': 'success'}), 200

# Function to send a notification to the user via Telegram bot
def send_telegram_notification(user_id, message):
    telegram_api_url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': user_id,
        'text': message
    }
    response = requests.post(telegram_api_url, json=payload)
    if response.status_code != 200:
        print("Failed to send Telegram notification")

# Function to get the user ID from the order ID (You need to implement this)
def get_user_id_from_order_id(order_id):
    # This function should retrieve the user ID associated with the given order ID from your database
    pass

# Function to update the user's VIP status to True (You need to implement this)
def update_user_vip_status(user_id):
    # This function should update the user's VIP status to True in your database
    pass

if __name__ == '__main__':
    app.run(debug=True)  # Run the Flask app
