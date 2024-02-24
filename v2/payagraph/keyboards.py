import json
from math import ceil
from payagraph.raw import CanBeKeyboardItemInterface


class Keyboard:
    def __init__(self, *rows: list) -> None:
        self.keys = list([row if isinstance(row, list) else [row] for row in rows])
        self.one_time_keyboard = False
        self.resize_keyboard = True

    def make_one_time(self):
        self.one_time_keyboard = True

    def prevent_resizing(self):
        self.resize_keyboard = False

    def as_dict(self) -> dict:
        return {
            "keyboard": self.keys,
            "one_time_keyboard": self.one_time_keyboard,
            "resize_keyboard": self.resize_keyboard
        }

    def as_json(self) -> str:
        '''Return the json that canbe used for passing to reponse payload'''
        return json.dumps(self.as_dict())

    def attach_to(self, response_payload: dict) -> None:
        '''Attach the keyboard to the response payload, to make it easy for adding keyboard to messages'''
        response_payload['reply_markup'] = self.as_json()  # dicts are passed by reference, so there is no need to return this



class InlineKey:
    '''Inline kyeboard items'''
    def __init__(self, text: str, callback_data: dict|str = None, url: str = None, ask_location: bool = False, ask_contact: bool = False) -> None:
        self.text: str = text
        # From the fields below only one must be passed, otherwise it will consider it first as callback_data, then url, then ...
        self.callback_data: dict|str = callback_data
        self.url: str = url
        self.request_location: bool = ask_location
        self.request_contact: bool = ask_contact

    def set_params(self, param: dict):
        if "callback_data" in param:
            self.callback_data = param["callback_data"]
        elif "url" in param:
            self.url = param["url"]
        elif "request_contact" in param:
            self.request_contact = param["request_contact"]
        elif "request_location" in param:
            self.request_location = param["request_location"]
        return self


    def as_dict(self) -> dict:
        value = {"text": self.text}
        if self.callback_data:
            value["callback_data"] = json.dumps(self.callback_data) if isinstance(self.callback_data, dict) else str(self.callback_data)
        elif self.url:
            value["url"] = self.url
        elif self.request_contact:
            value["request_contact"] = True
        elif self.request_location:
            value["request_location"] = True
        else:
            value["callback_data"] = "null"

        return value


class InlineKeyboard(Keyboard):
    '''Telegram Inline keyboard implementation, to make it easy for adding inline keyboards to your messages'''
    def __init__(self, *rows):
        self.keys = list([row if isinstance(row, list) else [row] for row in rows])

    def make_standard_key(self, key: any) -> InlineKey:
        v = None
        try:
            v = key if isinstance(key, InlineKey) \
                else InlineKey(text=key["text"]).set_params(key) if isinstance(key, dict) \
                else InlineKey(str(key))
        except:
            v = InlineKey(text="!!")
        return v

    def as_dict(self) -> dict:
        '''Convert the obbject to a dict so then it be converted to a propper json. It's written in a way that it considers any kind of key param type'''
        if not len(self.keys):
            return None

        arranged_keys = [
            [self.make_standard_key(col).as_dict() for col in (row if isinstance(row, list) else [row])] \
                for row in self.keys]

        return {
            "inline_keyboard": arranged_keys
        }

    @staticmethod
    def Arrange(list_of_keys: list[CanBeKeyboardItemInterface], callback_action: str):
        keys_count = len(list_of_keys)
        keys = [[ InlineKey(list_of_keys[j].title(), {"a": callback_action, "v": list_of_keys[j].value()}) \
                 for j in range(i * 5, (i + 1) * 5 if (i + 1) * 5 < keys_count else keys_count)] \
                    for i in range(ceil(keys_count // 5))]

        return InlineKeyboard(*keys)


    @staticmethod
    # this function creates inline keyboard for selecting coin/currency as desired ones
    def CreateDynamicList(callback_action: str, all_choices: dict, selected_ones: list=None, show_full_names: bool=False):
        '''Creates a dynamic list, for welection; just provide a Dict containg short_form(symbol) of a word linking to its full form;
            Provide a list of selected symbols and determine that you want to show symbols or the full word, and the func will do the rest for you
        '''
        if not selected_ones:
            selected_ones = []
        buttons = []
        row = []
        i = 0
        for choice in all_choices:
            btn_text = choice if not show_full_names else all_choices[choice]
            i += 1 + int(len(btn_text) / 5)
            if choice in selected_ones:
                btn_text += "✅"
            row.append(InlineKey(btn_text, callback_data=json.dumps({"a": callback_action, "v": choice})))
            if i >= 5:
                buttons.append(row)
                row = []
                i = 0
        return InlineKeyboard(*buttons)
