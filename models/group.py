from tools import manuwriter
from db.interface import DatabaseInterface
from json import dumps as jsonify


class Group:
    Instances = {}
    _database: DatabaseInterface = None


    @staticmethod
    def Database():
        if Group._database is None:
            Group._database = DatabaseInterface.Get()
        return Group._database

    @staticmethod
    def GetHasPlanGroups():
        """return all group table rows that has interval > 0"""
        Group.Instances.clear()
        groups_as_row = Group.Database.get_groups_by_interval()  # fetch all positive interval groups
        for row in groups_as_row:
            group = Group(group_id=int(row[0]), interval=int(row[1]), last_post_time=int(row[2]),
                              group_name=row[3], group_title=row[4], owner_id=int(row[-1]))
            Group.Instances[group.id] = group
        return Group.Instances

    def __init__(self, owner_id: int, group_id: int, group_name: str = None, group_title: str | None = None,
                 selected_coins: str | None = None, selected_currencies: str | None = None, message_header: str | None = None,
                 message_footer: str | None = None, message_show_date: bool = False, message_show_market_labels: bool = True) -> None:
        self.owner_id = owner_id
        self.id = group_id
        self.name = group_name  # username
        self.title = group_title
        self.selected_coins = selected_coins
        self.selected_currencies = selected_currencies
        self.message_header = message_header
        self.message_footer = message_footer
        self.message_footer = message_footer
        self.message_show_date = message_show_date
        self.message_show_market_labels = message_show_market_labels

        # TODO: extract and zip coins and currencies to string/list
        # TODO: Maybe create a MessageSetting class? to use in group/channel
        # TODO: Do the same for channels
        # TODO: write method in database to save group dara
        
    @staticmethod
    def Get(group_id):
        if group_id in Group.Instances:
            return Group.Instances[group_id]
        row = Group.Database.get_group(group_id)
        if row:
            return Group.ExtractQueryRowData(row)

        return None

    def __str__(self) -> str:
        return f"Username:{self.name}\nTitle: {self.title}\nId: {self.id}\nInterval: {self.interval}\nOwner Id: {self.owner_id}"
    
    @staticmethod
    def ExtractQueryRowData(row: tuple):
        return Group(group_id=int(row[0]), group_name=row[1], group_title=row[2], selected_coins=row[3], selected_currencies=row[4],
                           message_header=row[5], message_footer=row[6], message_show_date=bool(row[7]), message_show_market_labels=bool(row[8]), owner_id=int(row[-1]))
    
    @staticmethod
    def GetByOwner(owner_chat_id: int):
        rows = Group.Database().get_user_groups(owner_chat_id)
        return list(map(Group.ExtractQueryRowData, rows))
        