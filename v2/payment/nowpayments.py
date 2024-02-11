import requests
from decouple import config
from payment.order import PaymentCost

class NowpaymentsGateway:
    # Define your NowPayments API key
    API_KEY = None

    # Define the base URL for the NowPayments API
    BASE_URL = 'https://api.nowpayments.io/v1'

    # Define the endpoint for creating payment links
    PAYMENT_ENDPOINT = 'invoice'

    def __init__(self, buyer_chat_id: int, cost: PaymentCost, callback_url: str, on_success_url: str) -> None:
        if not NowpaymentsGateway.API_KEY:
            NowpaymentsGateway.API_KEY = config('NOWPAYMENT_API_KEY')
        self.payment_payload: dict = {
            "price_amount": cost.amount,
            "price_currency": cost.Unit,  # Currency of the payment
            # "pay_currency": "BTC",
            "order_id": str(buyer_chat_id),
            "order_description": cost.description,
            "ipn_callback_url": callback_url,  # Callback URL for IPN notifications (to update datbase)
            # "success_redirect_url":  on_success_url # Redirect URL after successful payment
        }
        self.result = None
        self.payment_link: str = None


    def get_payment_link(self) -> str:
        self.payment_link = None
        # Define the headers for the API request
        headers = {
            'x-api-key': NowpaymentsGateway.API_KEY,
            'Content-Type': 'application/json'
        }
        # Make the API request to create the payment link
        self.result = requests.post(f"{NowpaymentsGateway.BASE_URL}/{NowpaymentsGateway.PAYMENT_ENDPOINT}", json=self.payment_payload, headers=headers)
        # Check if the request was successful
        # print(self.result.text)
        if self.result.status_code == 200:
            # Extract the payment link from the self.result
            self.payment_link = self.result.json()[f'{NowpaymentsGateway.PAYMENT_ENDPOINT}_url']
        return self.payment_link
