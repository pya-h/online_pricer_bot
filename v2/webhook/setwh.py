import requests
from decouple import config


bot_token = config("VIP_BOT_TOKEN")
webhook_url = config('HOST_URL')
def set_webhook():
    url = f'https://api.telegram.org/bot{bot_token}/setWebhook'
    print(url)
    payload = {'url': webhook_url}
    response = requests.post(url, json=payload)
    print(response.text)

if __name__ == '__main__':
    set_webhook()
