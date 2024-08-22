from tools.mathematix import now_in_minute
from db.interface import DatabaseInterface
from typing import List
from telegram import Chat
from .account import Account
from tools.exceptions import MaxAddedCommunityException, UserNotAllowedException, InvalidInputException


class Group:
    FastMemInstances = {}
    _database: DatabaseInterface = None
    PreviousFastMemGarbageCollectionTime: int = now_in_minute()
    FastMemGarbageCollectionInterval: int = 5

    @staticmethod
    def database():
        if not Group._database:
            Group._database = DatabaseInterface.get()
        return Group._database

    def __init__(
        self,
        owner_id: int,
        group_id: int,
        group_name: str = None,
        group_title: str | None = None,
        selected_coins: List[str] | None = None,
        selected_currencies: List[str] | None = None,
        message_header: str | None = None,
        message_footnote: str | None = None,
        message_show_date_tag: bool = False,
        message_show_market_tags: bool = True,
        no_fastmem: bool = False,
    ) -> None:
        self.owner_id: int = int(owner_id)
        self.id: int = int(group_id)
        self.name: str | None = group_name  # username
        self.title: str = group_title
        self.selected_coins: List[str] = selected_coins or []
        self.selected_currencies: List[str] = selected_currencies or []
        self.message_header: str | None = message_header
        self.message_footnote: str | None = message_footnote
        self.message_show_date_tag: bool = message_show_date_tag
        self.message_show_market_tags: bool = message_show_market_tags
        self.last_interaction: int = now_in_minute()

        if not no_fastmem:
            self.organize_fastmem()
        # TODO: Maybe create a MessageSetting class? to use in group/channel
        # TODO: Do the same for channels

    def organize_fastmem(self):
        Group.garbageCollect()
        Group.FastMemInstances[self.id] = self

    def __str__(self) -> str:
        return f"Groupname:{self.name}\nId: {self.id}\nOwner Id: {self.owner_id}"

    def save(self):
        self.database().update_group(self)
        return self

    def change(self, new_chat: Chat):
        if self.id == new_chat.id:
            raise InvalidInputException("chat id; it doesn't differ from the old one.")
        old_chat_id = self.id
        self.id = new_chat.id
        self.name = new_chat.username
        self.title = new_chat.title

        Group.database().update_group(self.id, old_chat_id=old_chat_id)
        if Group.FastMemInstances[old_chat_id]:
            del Group.FastMemInstances[old_chat_id]
        return self

    @property
    def coins_as_str(self):
        return ";".join(self.selected_coins)

    @property
    def currencies_as_str(self):
        return ";".join(self.selected_currencies)

    @property
    def is_active(self):
        """Check owner premium date is valid or not"""
        owner = Account.getById(self.owner_id)  # FIXME: Account SEEMS AS A CIRCULAR DEPENDENCY
        return owner.is_premium

    @staticmethod
    def get(group_id, no_fastmem: bool = False):
        # FIXME: Use SQL 'JOIN ON' keyword to load group and owner accounts simultaneously.
        if group_id in Group.FastMemInstances:
            return Group.FastMemInstances[group_id]
        row = Group.database().get_group(group_id)
        if row:
            return Group.extractQueryRowData(row, no_fastmem)

        return None

    @staticmethod
    def extractQueryRowData(row: tuple, no_fastmem: bool = False):
        return Group(
            group_id=int(row[0]),
            group_name=row[1],
            group_title=row[2],
            selected_coins=DatabaseInterface.stringToList(row[3]),
            selected_currencies=DatabaseInterface.stringToList(row[4]),
            message_header=row[5],
            message_footnote=row[6],
            message_show_date_tag=bool(row[7]),
            message_show_market_tags=bool(row[8]),
            owner_id=int(row[-1]),
            no_fastmem=no_fastmem,
        )

    @staticmethod
    def getByOwner(owner_chat_id: int, take: int | None = 1):
        rows = Group.database().get_user_groups(owner_chat_id, take)
        if not rows:
            return None
        if len(rows) == 1:
            return Group.extractQueryRowData(rows[0])
        return list(map(Group.extractQueryRowData, rows))

    @staticmethod
    def register(chat: Chat, owner_id: int, allowed_group_count: int = 1):
        """Create group model and save into database. set its active_until field same as user premium date.
        return the database data if group is existing from before (just update its owner id)."""
        db = Group.database()
        group_columns = db.get_group(chat.id)
        if group_columns:
            group = Group.extractQueryRowData(group_columns)
            group.name = chat.username
            group.title = chat.title
            group.owner_id = owner_id
            group.save()
            return group

        # enhanced check:
        if allowed_group_count == 1:
            if Group.userHasAnyGroups(owner_id):
                raise MaxAddedCommunityException("group")
        elif allowed_group_count > 1:
            if Group.usersGroupCount(owner_id) > allowed_group_count:
                raise MaxAddedCommunityException("group")
        elif not allowed_group_count:
            raise UserNotAllowedException(owner_id, "have groups")

        group = Group(owner_id=owner_id, group_id=chat.id, group_title=chat.title, group_name=chat.username)
        db.add_group(group)
        return group

    @staticmethod
    def garbageCollect():
        now = now_in_minute()
        if now - Group.PreviousFastMemGarbageCollectionTime <= Group.FastMemGarbageCollectionInterval:
            return

        garbage = filter(
            lambda group_id: Group.FastMemInstances[group_id].last_interaction >= Group.FastMemGarbageCollectionInterval,
            Group.FastMemInstances,
        )
        Group.PreviousFastMemGarbageCollectionTime = now

        for g in garbage:
            del Group.FastMemInstances[g]

    @staticmethod
    def usersGroupCount(user_chat_id: int) -> int:
        return Group.database().user_groups_count(user_chat_id)

    @staticmethod
    def userHasAnyGroups(user_chat_id: int) -> bool:
        return bool(Group.database().get_user_groups(user_chat_id, take=1))
