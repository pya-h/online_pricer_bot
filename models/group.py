from tools.manuwriter import log
from tools.mathematix import now_in_minute
from db.interface import DatabaseInterface
from typing import List
from telegram import Chat
from .account import Account


class Group:
    Instances = {}
    _database: DatabaseInterface = None
    PreviousCleanupTime: int = now_in_minute()
    CleanupInterval: int = 10

    @staticmethod
    def Database():
        if not Group._database:
            Group._database = DatabaseInterface.Get()
        return Group._database

    def __init__(self, owner_id: int, group_id: int, group_name: str = None, group_title: str | None = None,
                 selected_coins: List[str] | None = None, selected_currencies: List[str] | None = None, message_header: str | None = None,
                 message_footer: str | None = None, message_show_date: bool = False, message_show_market_labels: bool = True, prevent_cache_cleanup: bool = False) -> None:
        self.owner_id: int = owner_id
        self.id: int = group_id
        self.name: str | None = group_name  # username
        self.title: str = group_title
        self.selected_coins: List[str] = selected_coins
        self.selected_currencies: List[str] = selected_currencies
        self.message_header: str | None = message_header
        self.message_footer: str | None = message_footer
        self.message_show_date: bool = message_show_date
        self.message_show_market_labels: bool = message_show_market_labels

        if not prevent_cache_cleanup:
            Group.cache_cleanup()
        # TODO: extract and zip coins and currencies to string/list
        # TODO: Maybe create a MessageSetting class? to use in group/channel
        # TODO: Do the same for channels
        # TODO: write method in database to save group dara
        

    def cache_cleanup(self):
        Group.GarbageCollect()
        Group.Instances[self.id] = self

    def __str__(self) -> str:
        return f"Groupname:{self.name}\nId: {self.id}\nOwner Id: {self.owner_id}"

    def save(self):
        self.Database().update_group(self)
        return self

    @property
    def coins_as_str(self):
        return ';'.join(self.selected_coins)

    @property
    def currencies_as_str(self):
        return ';'.join(self.selected_currencies)
    
    @property
    def is_active(self):
        '''Check owner premium date is valid or not'''
        owner = Account.Get(self.owner_id)
        return owner.is_premium
    
    @staticmethod
    def Get(group_id):
        # FXIME: Use SQL 'JOIN ON' keyword to load group and owner accounts simultaneously.
        if group_id in Group.Instances:
            return Group.Instances[group_id]
        row = Group.Database.get_group(group_id)
        if row:
            return Group.ExtractQueryRowData(row)

        return None

    @staticmethod
    def ExtractQueryRowData(row: tuple):
        return Group(group_id=int(row[0]), group_name=row[1], group_title=row[2], selected_coins=DatabaseInterface.StringToList(row[3]), selected_currencies=DatabaseInterface.StringToList(row[4]),
                           message_header=row[5], message_footer=row[6], message_show_date=bool(row[7]), message_show_market_labels=bool(row[8]), owner_id=int(row[-1]))
    
    @staticmethod
    def GetByOwner(owner_chat_id: int):
        rows = Group.Database().get_user_groups(owner_chat_id)
        return list(map(Group.ExtractQueryRowData, rows))
    
    @staticmethod
    def Register(chat: Chat, owner_id: int):
        '''Create group model and save into database. set its active_until field same as user premium date.
        retuen the database data if group is existing from before (just update its owner id).'''
        group_columns = Group.Database().get_group(chat.id)
        if group_columns:
            group = Group.ExtractQueryRowData(group_columns)
            group.name = chat.username
            group.title = chat.title
            group.owner_id = owner_id
            group.save()
            return group
        
        group = Group(owner_id=owner_id, group_id=chat.id, group_title=chat.title, group_name=chat.username)
        Group.Database().add_group(group)
        return group
    
    @staticmethod
    def GarbageCollect():
        now = now_in_minute()
        if now - Group.PreviousCleanupTime <= Group.CleanupInterval:
            return

        garbage = []
        Group.PreviousCleanupTime = now
        for group_id in Group.Instances:
            if Group.Instances[group_id].no_interaction_duration() >= Group.CleanupInterval / 2:
                garbage.append(group_id)
        cleaned_counts = len(garbage)
        for g in garbage:
            del Group.Instances[g]

        log(f"Cleaned {cleaned_counts} groups from cache.", category_name="gc")
