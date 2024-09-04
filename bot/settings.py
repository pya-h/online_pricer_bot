from tools.manuwriter import load_json, fwrite_from_scratch
from typing import Self, Dict
from enum import Enum
import gc
import json

class BotSettings:
    class UserTypes(Enum):
        FREE = 'free'
        PREMIUM = 'plus'
        ADMIN = 'admin'

    class Language(Enum):
        FA = 'fa'
        EN = 'en'

    singleInstance: Self | None = None

    @staticmethod
    def init():
        BotSettings.singleInstance = BotSettings()

    @staticmethod
    def get():
        if not BotSettings.singleInstance:
            print('X Reloading settings json again.')
            BotSettings.singleInstance = BotSettings()
        return BotSettings.singleInstance

    def __init__(self, resource_folder: str = 'resources', settings_file_name: str = 'settings.json') -> None:
        self.resource_folder = resource_folder
        self.settings_file_name = settings_file_name
        self.settings = load_json(settings_file_name, parent_folder=resource_folder)
        self.rules: Dict[str, int | float] = self.settings['rules']
        self.premium_plans_post_text: Dict[str, str] = self.settings['premiums_plans_text']
        self.premium_plans_post_file_id: Dict[str, str] = self.settings['premiums_plans_file_id']

    def TOKENS_COUNT_LIMIT(self, user_type: UserTypes = UserTypes.FREE):
        return BotSettings.singleInstance.rules['token_selection'][user_type.value]

    def CALCULATOR_TOKENS_COUNT_LIMIT(self, user_type: UserTypes = UserTypes.FREE):
        return BotSettings.singleInstance.rules['calculator_token_selection'][user_type.value]

    def COMMUNITY_TOKENS_COUNT_LIMIT(self, user_type: UserTypes = UserTypes.FREE):
        return BotSettings.singleInstance.rules['community_token_selection'][user_type.value]

    def ALARM_COUNT_LIMIT(self, user_type: UserTypes = UserTypes.FREE):
        return BotSettings.singleInstance.rules['alarm_selection'][user_type.value]

    def EACH_COMMUNITY_COUNT_LIMIT(self, user_type: UserTypes = UserTypes.FREE):
        return BotSettings.singleInstance.rules['community_count_limit'][user_type.value]

    def PREMIUM_PLANS_TEXT(self, language: str):
        return BotSettings.singleInstance.premium_plans_post_text[language]
    
    def PREMIUM_PLANS_IMAGE(self, language: str):
        return BotSettings.singleInstance.premium_plans_post_file_id[language]

    def PREMIUM_PLANS_POST(self, language: str):
        text = BotSettings.singleInstance.premium_plans_post_text[language]
        file_id = BotSettings.singleInstance.premium_plans_post_file_id[language] or None
        return (text, file_id)

    def update_premium_plans_post(self, text: str, file_id: str | None = None, language: Language = Language.FA):
        self.settings['premiums_plans_text'][language.value] = text
        self.settings['premiums_plans_file_id'][language.value] = file_id
        fwrite_from_scratch(f'./{self.resource_folder}/{self.settings_file_name}', fdata=json.dumps(self.settings), source='Settings')

    @staticmethod
    def refresh():
        BotSettings.singleInstance = None
        gc.collect()
        BotSettings.init()