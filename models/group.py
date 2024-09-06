from tools.mathematix import now_in_minute, from_now_time_diff
from db.interface import DatabaseInterface
from typing import Dict, Set
from telegram import Chat
from .account import Account
from tools.exceptions import (
    MaxAddedCommunityException,
    UserNotAllowedException,
    InvalidInputException,
    NoSuchThingException,
)
from tools.manuwriter import log
from bot.settings import BotSettings
import gc
from json import loads as load_json
from api.crypto_service import CryptoCurrencyService
from api.currency_service import NavasanService


class Group:
    fastMemInstances = {}
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
        selected_coins: Set[str] | None = None,
        selected_currencies: Set[str] | None = None,
        message_header: str | None = None,
        message_footnote: str | None = None,
        message_show_date_tag: bool = False,
        message_show_market_tags: bool = True,
        no_fastmem: bool = False,
        owner: Account = None,
    ) -> None:
        self.owner_id: int = int(owner_id)
        self.id: int = int(group_id)
        self.name: str | None = group_name  # username
        self.title: str = group_title
        self.selected_coins: Set[str] = selected_coins or set()
        self.selected_currencies: Set[str] = selected_currencies or set()
        self.message_header: str | None = message_header
        self.message_footnote: str | None = message_footnote
        self.message_show_date_tag: bool = message_show_date_tag
        self.message_show_market_tags: bool = message_show_market_tags
        self.last_interaction: int = now_in_minute()

        self.owner: Account | None = owner or Account.getFast(
            self.owner_id
        )  # TODO: Use SQL JOIN and Use it In case fastmem is empty
        if not no_fastmem:
            self.organize_fastmem()
        # TODO: Maybe create a MessageSetting class? to use in group/channel
        # TODO: Do the same for channels

    def organize_fastmem(self):
        Group.garbageCollect()
        Group.fastMemInstances[self.id] = self

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

        Group.database().update_group(self, old_chat_id=old_chat_id)
        if Group.fastMemInstances[old_chat_id]:
            del Group.fastMemInstances[old_chat_id]
        return self

    def delete(self) -> bool:
        try:
            Group.database().delete_group(self.id)
            if self.id in Group.fastMemInstances:
                del Group.fastMemInstances[self.id]
        except Exception as ex:
            log(f"Cannot remove Group:{self.id}", ex, category_name="Groups")
            return False
        return True

    def throw_in_trashcan(self):
        self.database().trash_sth(
            self.owner_id, DatabaseInterface.TrashType.GROUP, self.id, self.as_dict
        )

    def getTrashedCustomization(
        trash_identifier: int,
    ) -> Dict[str, int | float | str | bool]:
        trash = Group.database().get_trash_by_identifier(
            DatabaseInterface.TrashType.GROUP, trash_identifier
        )
        try:
            return trash[-2]
        except:
            pass
        return None

    def use_trash_data(self, trash: Dict[str, int | float | str | bool]):
        try:
            self.selected_coins = (
                DatabaseInterface.stringToSet(trash["coins"])
                if "coins" in trash
                else None
            ) or set()
            self.selected_currencies = (
                DatabaseInterface.stringToSet(trash["currencies"])
                if "currencies" in trash
                else None
            ) or set()
            self.name = trash["name"] if "name" in trash else None
            self.title = trash["title"] if "title" in trash else None
            self.name = trash["name"] if "name" in trash else None
            msg_settings = trash["message"] if "message" in trash else None
            if msg_settings:
                self.message_header = (
                    msg_settings["header"] if "header" in msg_settings else None
                )
                self.message_footnote = (
                    msg_settings["footnote"] if "footnote" in msg_settings else None
                )
                self.message_show_date_tag = (
                    msg_settings["date_tag"] if "date_tag" in msg_settings else False
                )
                self.message_show_market_tags = (
                    msg_settings["market_tags"]
                    if "market_tags" in msg_settings
                    else False
                )

            self.last_interaction = now_in_minute()
        except:
            pass
        return self

    @property
    def as_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "name": self.name,
            "title": self.title,
            "coins": self.coins_as_str,
            "currencies": self.currencies_as_str,
            "message": {
                "header": self.message_header,
                "footnote": self.message_footnote,
                "date_tag": self.message_show_date_tag,
                "market_tags": self.message_show_market_tags,
            },
            "last_interaction": self.last_interaction,
        }

    @property
    def coins_as_str(self):
        return ";".join(self.selected_coins) if self.selected_coins else ""

    @property
    def currencies_as_str(self):
        return ";".join(self.selected_currencies) if self.selected_currencies else ""

    @property
    def is_active(self):
        """Check owner premium date is valid or not"""
        owner = Account.getById(self.owner_id)
        return owner.is_premium

    @property
    def description(self):
        if not self.owner:
            self.owner = Account.getById(self.owner_id, no_fastmem=True)
        return {
            "title": self.title,
            "username": f"@{self.name}" or self.id,
            "owner": self.owner,
        }

    @staticmethod
    def get(group_id, no_fastmem: bool = False):
        # FIXME: Use SQL 'JOIN ON' keyword to load group and owner accounts simultaneously.
        if group_id in Group.fastMemInstances:
            Group.fastMemInstances[group_id].last_interaction = now_in_minute()
            return Group.fastMemInstances[group_id]
        row = Group.database().get_group(group_id)
        if row:
            return Group.extractQueryRowData(row, no_fastmem)

        return None

    @staticmethod
    def extractQueryRowData(
        row: tuple, owner: Account | None = None, no_fastmem: bool = False
    ):
        return Group(
            group_id=int(row[0]),
            group_name=row[1],
            group_title=row[2],
            selected_coins=DatabaseInterface.stringToSet(row[3]),
            selected_currencies=DatabaseInterface.stringToSet(row[4]),
            message_header=row[5],
            message_footnote=row[6],
            message_show_date_tag=bool(row[7]),
            message_show_market_tags=bool(row[8]),
            owner_id=int(row[-1]),
            no_fastmem=no_fastmem,
            owner=owner,
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
    def register(chat: Chat, owner_id: int):
        """Create group model and save into database. set its active_until field same as user premium date.
        return the database data if group is existing from before (just update its owner id).
        """
        db = Group.database()
        owner = Account.getById(owner_id)
        allowed_group_count = BotSettings.get().EACH_COMMUNITY_COUNT_LIMIT(
            owner.user_type
        )
        group_columns = db.get_group(chat.id)
        if group_columns:
            group = Group.extractQueryRowData(group_columns, owner=owner)
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

        group = Group(
            owner_id=owner_id,
            group_id=chat.id,
            group_title=chat.title,
            group_name=chat.username,
            owner=owner,
            selected_coins=CryptoCurrencyService.getUserDefaultCryptos(),
            selected_currencies=NavasanService.getUserDefaultCurrencies(),
        )
        db.add_group(group)
        return group

    @staticmethod
    def garbageCollect():
        now = now_in_minute()
        if (
            now - Group.PreviousFastMemGarbageCollectionTime
            <= Group.FastMemGarbageCollectionInterval
        ):
            return

        Group.fastMemInstances = {
            chat_id: group
            for chat_id, group in Group.fastMemInstances.items()
            if group.last_interaction < Group.FastMemGarbageCollectionInterval
        }

        Group.PreviousFastMemGarbageCollectionTime = now
        gc.collect()

    @staticmethod
    def refreshFastMem():
        Group.fastMemInstances.clear()
        gc.collect()

    @staticmethod
    def usersGroupCount(user_chat_id: int) -> int:
        return Group.database().user_groups_count(user_chat_id)

    @staticmethod
    def userHasAnyGroups(user_chat_id: int) -> bool:
        return bool(Group.database().get_user_groups(user_chat_id, take=1))

    @staticmethod
    def getFast(group_id: int):
        return (
            Group.fastMemInstances[group_id]
            if group_id in Group.fastMemInstances
            else None
        )

    @staticmethod
    def restoreTrash(trash_identifier: int):
        db = Group.database()
        trash = db.get_trash_by_identifier(
            DatabaseInterface.TrashType.GROUP, trash_identifier
        )
        if not trash:
            raise NoSuchThingException(trash_identifier, "Trashed Group")
        try:
            data = load_json(trash[-3])
            group = Group(trash[2], trash_identifier).use_trash_data(data).save()
            db.throw_trash_away(trash[0])
            return group
        except Exception as x:
            log("Returning trashed group failed!", x, "Group")
        return None

    @staticmethod
    def selectGroups(take: int = 10, page: int = 0):
        groups_query_data = Group.database().select_groups_with_owner(limit=take, offset=take*page)
        return list(
            map(
                lambda row: Group.extractQueryRowData(
                    row[:len(DatabaseInterface.GROUPS_COLUMNS)],
                    no_fastmem=True,
                    owner=Account.extractQueryRowData(row[len(DatabaseInterface.GROUPS_COLUMNS):], no_fastmem=True),
                ),
                groups_query_data,
            )
        )

    @staticmethod
    def getAllGroupsCount():
        return Group.database().get_all_groups_count()