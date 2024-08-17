from tools.mathematix import now_in_minute
from db.interface import DatabaseInterface
from typing import List
from telegram import Chat
from .account import Account
from tools.exceptions import MaxAddedCommunityException, UserNotAllowedException


class Group:
    FastMemInstances = {}
    _database: DatabaseInterface = None
    PreviousFastMemGarbageCollectionTime: int = now_in_minute()
    FastMemGarbageCollectionInterval: int = 5

    @staticmethod
    def Database():
        if not Group._database:
            Group._database = DatabaseInterface.Get()
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
        Group.GarbageCollect()
        Group.FastMemInstances[self.id] = self

    def __str__(self) -> str:
        return f"Groupname:{self.name}\nId: {self.id}\nOwner Id: {self.owner_id}"

    def save(self):
        self.Database().update_group(self)
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
        owner = Account.GetById(self.owner_id)
        return owner.is_premium

    @staticmethod
    def Get(group_id, no_fastmem: bool = False):
        # FIXME: Use SQL 'JOIN ON' keyword to load group and owner accounts simultaneously.
        if group_id in Group.FastMemInstances:
            return Group.FastMemInstances[group_id]
        row = Group.Database().get_group(group_id)
        if row:
            return Group.ExtractQueryRowData(row, no_fastmem)

        return None

    @staticmethod
    def ExtractQueryRowData(row: tuple, no_fastmem: bool = False):
        return Group(
            group_id=int(row[0]),
            group_name=row[1],
            group_title=row[2],
            selected_coins=DatabaseInterface.StringToList(row[3]),
            selected_currencies=DatabaseInterface.StringToList(row[4]),
            message_header=row[5],
            message_footnote=row[6],
            message_show_date_tag=bool(row[7]),
            message_show_market_tags=bool(row[8]),
            owner_id=int(row[-1]),
            no_fastmem=no_fastmem,
        )

    @staticmethod
    def GetByOwner(owner_chat_id: int, take: int | None = 1):
        rows = Group.Database().get_user_groups(owner_chat_id, take)
        if len(rows) == 1:
            return Group.ExtractQueryRowData(rows[0])
        return list(map(Group.ExtractQueryRowData, rows))

    @staticmethod
    def Register(chat: Chat, owner_id: int, allowed_group_count: int = 1):
        """Create group model and save into database. set its active_until field same as user premium date.
        return the database data if group is existing from before (just update its owner id)."""
        db = Group.Database()
        group_columns = db.get_group(chat.id)
        if group_columns:
            group = Group.ExtractQueryRowData(group_columns)
            group.name = chat.username
            group.title = chat.title
            group.owner_id = owner_id
            group.save()
            return group

        # enhanced check:
        if allowed_group_count == 1:
            if Group.OwnerHasGroup(owner_id):
                raise MaxAddedCommunityException("group")
        elif allowed_group_count > 1:
            if Group.OwnerGroupCount(owner_id) > allowed_group_count:
                raise MaxAddedCommunityException("group")
        elif not allowed_group_count:
            raise UserNotAllowedException(owner_id, "have groups")

        group = Group(owner_id=owner_id, group_id=chat.id, group_title=chat.title, group_name=chat.username)
        db.add_group(group)
        return group

    @staticmethod
    def OwnerHasGroup(owner_id: int):
        return bool(Group.Database().get_user_groups(owner_id, take=1))

    @staticmethod
    def OwnerGroupCount(owner_id: int):
        return Group.Database().user_groups_count(owner_id)

    @staticmethod
    def GarbageCollect():
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
