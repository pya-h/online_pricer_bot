import logging
from telegram.ext import Updater, CommandHandler
import requests

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define your NowPayments API key
API_KEY = 'your_api_key_here'

# Define the base URL for the NowPayments API
BASE_URL = 'https://api.nowpayments.io/v1'

# Define the endpoint for creating payment links
CREATE_PAYMENT_LINK_ENDPOINT = '/payment-links'


# Define the start command handler
def start(update, context):
    update.message.reply_text('Welcome to the NowPayments Bot! Use /createpaymentlink to create a payment link.')


# Define the create payment link command handler
def create_payment_link(update, context):
    # Define the payload for creating a payment link
    payload = {
        "price_amount": 10,  # Amount to be paid
        "price_currency": "USD",  # Currency of the payment
        "order_id": "unique_order_id",  # Unique identifier for the order
        "order_description": "Description of the order",  # Description of the order
        "ipn_callback_url": "https://your-callback-url.com",  # Callback URL for IPN notifications
        "success_redirect_url": "https://your-success-redirect-url.com"  # Redirect URL after successful payment
    }

    # Define the headers for the API request
    headers = {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json'
    }

    # Make the API request to create the payment link
    response = requests.post(BASE_URL + CREATE_PAYMENT_LINK_ENDPOINT, json=payload, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the payment link from the response
        payment_link = response.json()['data']['payment_link']
        update.message.reply_text(f"Payment link created successfully: {payment_link}")
    else:
        update.message.reply_text("Error creating payment link. Please try again later.")


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("YOUR_TELEGRAM_BOT_TOKEN", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Define command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("createpaymentlink", create_payment_link))

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
