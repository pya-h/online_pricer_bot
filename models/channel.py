from tools import manuwriter
from db.interface import DatabaseInterface
from json import dumps as jsonify
from bot.types import GroupInlineKeyboardButtonTemplate
from typing import List
from tools.exceptions import MaxAddedCommunityException, UserNotAllowedException, InvalidInputException
from telegram import Chat


class PostInterval(GroupInlineKeyboardButtonTemplate):
    def __init__(self, title: str | None = None, minutes: int = 0, hours: int = 0, days: int = 0) -> None:
        self._title = title
        self.days = days
        self.hours = hours + self.days * 24  # total in hours
        self.minutes = minutes + self.hours * 60  # total interval in minutes

    @property
    def value(self) -> int:
        return self.minutes  # this is for GlassButton.Arrange

    @property
    def title(self) -> str:
        return self._title

    @property
    def as_json(self):
        return jsonify({"d": self.days, "h": self.hours, "m": self.minutes})

    @property
    def timestamps(self):
        if self.minutes < 60:
            return f"{self.minutes}m", f"{self.minutes} minutes", f"هر {self.minutes} دقیقه"

        days = 0
        hours = int(self.minutes / 60)
        mins = self.minutes - hours * 60
        if hours < 24:
            return (
                (f"{hours}h", "{hours} hours", f"{hours} ساعت")
                if not mins
                else (f"{hours}h, {mins}m", f"{hours} hours and {mins} minutes", f"{hours} ساعت و {mins} دقیقه")
            )

        days = int(hours / 24)
        hours -= days * 24
        result_short, result_en, result_fa = f"{days}d", f"{days} days", f"{days} روز"
        if hours:
            result_short += f", {hours}h"
            result_en += f" and {hours} hours"
            result_fa += f" و {hours} ساعت"
        if mins:
            result_short += f", {mins}m"
            result_en += f" and {mins} minutes"
            result_fa += f" و {mins} دقیقه"
        return result_short, result_en, result_fa

    @staticmethod
    def TimestampToMinutes(string: str):
        string = string.split()
        interval_in_mins: int = 0
        for term in string:
            if term[-1].lower() == "h":
                interval_in_mins += int(term[:-1]) * 60
            elif term[-1].lower() == "d":
                interval_in_mins += int(term[:-1]) * 24 * 60
            elif term[-1].lower() == "m" or term[-1].isdigit():
                interval_in_mins += int(term[:-1])
        return interval_in_mins


class Channel:
    Instances = {}
    _database: DatabaseInterface = None

    @staticmethod
    def database():
        if not Channel._database:
            Channel._database = DatabaseInterface.get()
        return Channel._database

    @staticmethod
    def GetHasPlanChannels():
        """return all channel table rows that has interval > 0"""
        Channel.Instances.clear()
        channels_as_row = Channel.database().get_channels_by_interval()  # fetch all positive interval channels
        for row in channels_as_row:
            channel = Channel(
                channel_id=int(row[0]),
                interval=int(row[1]),
                last_post_time=int(row[2]),
                channel_name=row[3],
                channel_title=row[4],
                owner_id=int(row[-1]),
            )
            Channel.Instances[channel.id] = channel
        return Channel.Instances

    SupportedIntervals: list[PostInterval] = [
        PostInterval("1 MIN", minutes=1),
        *[PostInterval(f"{m} MINS", minutes=m) for m in [2, 5, 10, 30, 45]],
        PostInterval("1 HOUR", hours=1),
        *[PostInterval(f"{h} HOURS", hours=h) for h in [2, 3, 4, 6, 12]],
        PostInterval("1 DAY", days=1),
        *[PostInterval(f"{d} DAYS", days=d) for d in [2, 3, 4, 5, 6, 7, 10, 14, 30, 60]],
    ]

    def __init__(
        self,
        channel_id: int,
        owner_id: int,
        interval: int = 0,
        channel_name: str = None,
        channel_title: str = None,
        last_post_time: int = None,
        is_active: bool = False,
        selected_coins: List[str] | None = None,
        selected_currencies: List[str] | None = None,
        message_header: str | None = None,
        message_footnote: str | None = None,
        message_show_date_tag: bool = False,
        message_show_market_tags: bool = True,
    ) -> None:
        self.owner_id: int = int(owner_id)
        self.owner = None
        self.id: int = int(channel_id)
        self.name: str = channel_name  # username
        self.title: str = channel_title
        self.interval: int = interval
        self.is_active: bool = is_active
        self.selected_coins: List[str] = selected_coins or []
        self.selected_currencies: List[str] = selected_currencies or []
        self.message_header: str | None = message_header
        self.message_footnote: str | None = message_footnote
        self.message_show_date_tag: bool = message_show_date_tag
        self.message_show_market_tags: bool = message_show_market_tags
        self.last_post_time: int | None = last_post_time  # don't forget database has this

    def create(self, allowed_channels_count: int = 1):
        db = Channel.database()
        channel_columns = db.get_channel(self.id)
        if channel_columns:
            self.save()  # just update database
            return
        # enhanced check:
        if allowed_channels_count == 1:
            if Channel.userHasAnyChannels(self.owner_id):
                raise MaxAddedCommunityException("channel")
        elif allowed_channels_count > 1:
            if Channel.usersChannelsCount(self.owner_id) > allowed_channels_count:
                raise MaxAddedCommunityException("channel")
        elif not allowed_channels_count:
            raise UserNotAllowedException(self.owner_id, "have channels")

        db.add_channel(self)

    def plan(self) -> bool:
        if self.interval <= 0:
            if self.id in Channel.Instances:
                # plan and delete in database
                del Channel.Instances[self.id]
            return False  # Plan removed

        Channel.Instances[self.id] = self
        Channel.database().set_channel_state(self.id, True)
        return True

    def stop_plan(self) -> bool:
        try:
            Channel.database().delete_channel(self.id)
            if self.id in Channel.Instances:
                del Channel.Instances[self.id]
        except Exception as ex:
            manuwriter.log(f"Cannot remove channel:{self.id}", ex, category_name="PLUS_FATALITY")
            return False
        return True

    def __str__(self) -> str:
        return f"Username:{self.name}\nTitle: {self.title}\nId: {self.id}\nInterval: {self.interval}\nOwner Id: {self.owner_id}"

    def save(self):
        self.database().update_channel(self)
        return self

    def change(self, new_chat: Chat):
        if self.id == new_chat.id:
            raise InvalidInputException("chat id; it doesn't differ from the old one.")
        old_chat_id = self.id
        self.id = new_chat.id
        self.name = new_chat.username
        self.title = new_chat.title

        Channel.database().update_group(self.id, old_chat_id=old_chat_id)
        # if Channel.FastMemInstances[old_chat_id]:
        #     del Channel.FastMemInstances[old_chat_id]
        return self

    @property
    def coins_as_str(self):
        return ";".join(self.selected_coins)

    @property
    def currencies_as_str(self):
        return ";".join(self.selected_currencies)

    @staticmethod
    def get(channel_id):
        # FIXME: Use SQL 'JOIN ON' keyword to load group and owner accounts simultaneously.
        if channel_id in Channel.Instances:
            return Channel.Instances[channel_id]
        row = Channel.database().get_channel(channel_id)
        if row:
            return Channel.extractQueryRowData(row)

        return None

    @staticmethod
    def extractQueryRowData(row: tuple):
        return Channel(
            channel_id=int(row[0]),
            channel_name=row[1],
            channel_title=row[2],
            interval=int(row[3]),
            is_active=bool(row[4]),
            selected_coins=DatabaseInterface.stringToList(row[5]),
            selected_currencies=DatabaseInterface.stringToList(row[6]),
            message_header=row[7],
            message_footnote=row[8],
            message_show_date_tag=bool(row[9]),
            message_show_market_tags=bool(row[10]),
            last_post_time=int(row[-2] or 0),
            owner_id=int(row[-1]),
        )

    @staticmethod
    def getByOwner(owner_chat_id: int, take: int | None = 1):
        rows = Channel.database().get_user_channels(owner_chat_id, take)
        if not rows:
            return None
        if len(rows) == 1:
            return Channel.extractQueryRowData(rows[0])
        return list(map(Channel.extractQueryRowData, rows))


    @staticmethod
    def usersChannelsCount(user_chat_id: int) -> int:
        return Channel.database().user_channels_count(user_chat_id)

    @staticmethod
    def userHasAnyChannels(user_chat_id: int) -> bool:
        return bool(Channel.database().get_user_channels(user_chat_id, take=1))