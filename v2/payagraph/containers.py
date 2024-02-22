from db.vip_models import VIPAccount
import json
from enum import Enum
from tools.mathematix import force_cast


class ChatTypes(Enum):
    USER = "user"
    CHANNEL = "channel"
    GROUP = "group"
    NONE = "none"

    @staticmethod
    def corresponding_member(value: str):
        value = value.lower()
        for member in ChatTypes:
            if member.value == value:
                return member

        return ChatTypes.NONE


class ForwardOrigin:
    def __init__(self, forward_data: dict) -> None:
        self.type: ChatTypes = ChatTypes.corresponding_member(forward_data['type'])
        self.id: int = None
        self.message_id: int = None
        self.title: str = None
        self.username: str = None
        if self.type == ChatTypes.CHANNEL:
            self.id = forward_data['chat']['id']
            self.message_id = forward_data['message_id']
            self.title = forward_data['chat']['title']
            if 'username' in forward_data['chat']:
                self.username = forward_data['chat']['username']
        elif self.type == ChatTypes.USER:
            self.id = forward_data['sender_user']['id']
            self.title = forward_data['sender_user']['first_name']
            if 'username' in forward_data['sender_user']:
                self.username = forward_data['sender_user']['username']

    def __str__(self) -> str:
        return f"type: {self.type}\ntitle:{self.title}\nid:{self.id}\nusername:{self.username}"



class TelegramMessage:

    def __init__(self, data: dict) -> None:
        self.msg: dict = data['message']
        self.id: int = self.msg['message_id'] if 'message_id' in self.msg else None
        self.text: str =  self.msg['text']

        # TODO: *** define two separate users: One is SENDER_USER and another is TARGET_USER
        self.chat_id: int = self.msg['chat']['id']  # this is target chat_id, it may differ from self.by.chat_id
        self.by: VIPAccount = VIPAccount.Get(self.msg['chat']['id']) if self.chat_id >= 0 else None  # negative chat_id means its a channel
        # TODO: *** define two separate users: One is SENDER_USER and another is TARGET_USER

        # cause bot may get a message from a user (with chat_id A) and send it to another user with another chat_id(B); so dont mistake them
        self.forward_origin: ForwardOrigin = ForwardOrigin(self.msg['forward_origin']) if 'forward_origin' in self.msg else None
        self.replace_on_previous = False

    @staticmethod
    def Text(target_chat_id: str, text: str = ''):
        return TelegramMessage({"message": {
            "text": text,
            "chat": {
                "id": target_chat_id
            }
        }})

    #TODO: WRITE METHODS FOR CREATING DIFFERENT KINDS OF MESSSAGES (PHOTO, VIDEO, ETC.)


class TelegramCallbackQuery(TelegramMessage):

    def __init__(self, data: dict) -> None:
        super().__init__(data['callback_query'])
        self.data: str|dict = data['callback_query']['data']
        self.action: str = None
        self.value : str = self.data
        try:
            self.data = json.loads(self.data)
            self.action: str|int|float = force_cast(  # if can be convert to numeric, do it
                self.data['a'] if 'a' in self.data else None
            )

            self.value: str|int|float =  force_cast(# if can be convert to numeric, do it
                self.data['v'] if 'v' in self.data else None
            )
        except:
            pass
