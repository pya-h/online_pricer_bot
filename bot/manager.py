from enum import Enum
from tools.manuwriter import load_json
from decouple import config


class ResourceManager:

    def __call__(self, source_filename: str, source_foldername: str):
        self.source = load_json(source_filename, source_foldername)

    def mainkeyboard(self, key: str, language: str = 'fa') -> str:
        return self.source['main_keyboard'][key][language]
    
    def text(self, text_key: str, language: str = 'fa') -> str:
        return self.source[text_key][language]


resourceman = ResourceManager('texts', 'resources')

class BotMan:
        
    class Commands(Enum):
        GET_FA = resourceman.mainkeyboard('get_prices')
        CONFIG_PRICE_LIST_FA = resourceman.mainkeyboard('config_lists')
        EQUALIZER_FA = resourceman.mainkeyboard('calculator')
        SELECT_COINS_FA = 'ارز دیجیتال'
        SELECT_CURRENCIES_FA = "ارز"
        SELECT_GOLDS_FA = 'طلا'
        CANCEL_FA = 'لغو'

        ADMIN_POST_FA = 'اطلاع رسانی'
        ADMIN_START_SCHEDULE_FA = 'زمانبندی کانال'
        ADMIN_STOP_SCHEDULE_FA = 'توقف زمانبندی'
        ADMIN_STATISTICS_FA = 'آمار'

        BACK_TO_MAIN_MENU = resourceman.mainkeyboard('calculator')

    def __init__(self) -> None:
        self.resourceman = resourceman
        # environment values
        self.token: str = config('BOT_TOKEN')
        self.main_channel_id: int = config('CHANNEL_ID')
        self.supporting_channel_id: int = config('SECOND_CHANNEL_ID')
        self.main_queue_id: str = config('MAIN_SCHEDULER_IDENTIFIER')

        self.text = self.resourceman.text