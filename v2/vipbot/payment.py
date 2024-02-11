import requests

class NowpaymentInteface:
    # Define your NowPayments API key
    API_KEY = 'your_NOWPAYMENT_api_key_here'

    # Define the base URL for the NowPayments API
    BASE_URL = 'https://api.nowpayments.io/v1'

    # Define the endpoint for creating payment links
    CREATE_PAYMENT_LINK_ENDPOINT = '/payment-links'

    def __init__(self, buyer_chat_id: int, vip_cost: int, cost_unit: str, callback_url: str, description: str, bot_url) -> None:
        self.payment_payload: dict = {
            "price_amount": vip_cost,
            "price_currency": cost_unit,  # Currency of the payment
            "order_id": str(buyer_chat_id),
            "order_description": description,
            "ipn_callback_url": callback_url,  # Callback URL for IPN notifications (to update datbase)
            "success_redirect_url":  bot_url # Redirect URL after successful payment
        }
        self.result = None
        self.payment_link: str = None


    def get_payment_link(self) -> str:
        self.payment_link = None
        # Define the headers for the API request
        headers = {
            'x-api-key': NowpaymentInteface.API_KEY,
            'Content-Type': 'application/json'
        }
        # Make the API request to create the payment link
        self.result = requests.post(NowpaymentInteface.BASE_URL + NowpaymentInteface.CREATE_PAYMENT_LINK_ENDPOINT, json=self.payment_payload, headers=headers)

        # Check if the request was successful
        if self.result.status_code == 200:
            # Extract the payment link from the self.result
            self.payment_link = self.result.json()['data']['payment_link']
        return self.payment_link
