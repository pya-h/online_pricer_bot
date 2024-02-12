import requests
from decouple import config
from payment.order import Order

NOWPAYMENTS_API_KEY = config('NOWPAYMENT_API_KEY')
    # Define the base URL for the NowPayments API
NOWPAYMENTS_BASE_URL = 'https://api.nowpayments.io/v1'

class NowpaymentsGateway:
    # Define the endpoint for creating payment links
    PAYMENT_ENDPOINT = 'invoice'

    def __init__(self, buyer_chat_id: int, order: Order, callback_url: str, on_success_url: str) -> None:

        self.payment_payload: dict = {
            "price_amount": order.cost,
            "price_currency": order.CostUnit,  # Currency of the payment
            # "pay_currency": "BTC",
            "order_id": str(buyer_chat_id),
            "order_description": order.description,
            "ipn_callback_url": callback_url,  # Callback URL for IPN notifications (to update datbase)
            # "success_redirect_url":  on_success_url # Redirect URL after successful payment
        }
        self.result = None
        self.payment_link: str = None


    def get_payment_link(self) -> str:
        self.payment_link = None
        # Define the headers for the API request
        headers = {
            'x-api-key': NOWPAYMENTS_API_KEY,
            'Content-Type': 'application/json'
        }
        # Make the API request to create the payment link
        self.result = requests.post(f"{NOWPAYMENTS_BASE_URL}/{NowpaymentsGateway.PAYMENT_ENDPOINT}", json=self.payment_payload, headers=headers)
        # Check if the request was successful
        # print(self.result.text)
        if self.result.status_code == 200:
            # Extract the payment link from the self.result
            self.payment_link = self.result.json()[f'{NowpaymentsGateway.PAYMENT_ENDPOINT}_url']
        return self.payment_link
