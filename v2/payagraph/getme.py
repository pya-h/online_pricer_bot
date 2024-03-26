import requests
from decouple import config


bot_token = config("VIP_BOT_TOKEN")
def get_me():
    url = f'https://api.telegram.org/bot{bot_token}/getMe'
    response = requests.get(url)
    print(response.text)

if __name__ == '__main__':
    get_me()
