from tools import manuwriter
from models.plusplan import PlanInterval
from db.interface import DatabaseInterface


class Channel:

    Instances = {}
    Database: DatabaseInterface = DatabaseInterface.Get()

    @staticmethod
    def GetHasPlanChannels():
        '''return all channel table rows that has interval > 0'''
        Channel.Instances.clear()
        channels_as_row = Channel.Database.get_channels_by_interval()  # fetch all positive interval channels
        for row in channels_as_row:
            channel = Channel(channel_id=int(row[0]), interval=int(row[1]), last_post_time=int(row[2]), channel_name=row[3], channel_title=row[4], owner_id=int(row[-1]))
            Channel.Instances[channel.id] = channel
        return Channel.Instances

    SupportedIntervals: list[PlanInterval] = [
        PlanInterval("1 MIN", minutes=1), *[PlanInterval(f"{m} MINS", minutes=m) for m in [2, 5, 10, 30, 45]],
        PlanInterval("1 HOUR", hours=1), *[PlanInterval(f"{h} HOURS", hours=h) for h in [2, 3, 4, 6, 12]],
        PlanInterval("1 DAY", days=1), *[PlanInterval(f"{d} DAYS", days=d) for d in [2, 3, 4, 5, 6, 7, 10, 14, 30, 60]]
    ]

    def __init__(self, owner_id: int, channel_id: int, interval: int = 0, channel_name: str = None, channel_title:str = None, last_post_time: int=None) -> None:
        self.owner_id = owner_id
        self.id = channel_id
        self.name = channel_name  # username
        self.title = channel_title
        self.interval = interval
        self.last_post_time = last_post_time  # dont forget database has this

    # TODO: Write garbage collector for this class too
    
    def plan(self) -> bool:
        if self.interval <= 0:
            if self.id in Channel.Instances:
                # plan and delete in database
                del Channel.Instances[self.id]
            return False  # Plan removed

        # if self.interval < 60:
        #     Channel.Instances[self.id] = self
        Channel.Instances[self.id] = self
        Channel.Database.plan_channel(self.owner_id, self.id, self.name, self.interval, self.title)
        return True

    def stop_plan(self) -> bool:
        try:
            Channel.Database.delete_channel(self.id)
            del Channel.Instances[self.id]
        except Exception as ex:
            manuwriter.log(f'Cannot remove chnnel:{self.id}', ex, category_name="PLUS_FATALITY")
            return False
        return True

    @staticmethod
    def Get(channel_id):
        if channel_id in Channel.Instances:
            return Channel.Instances[channel_id]
        row = Channel.Database.get_channel(channel_id)
        if row:
            return Channel(channel_id=int(row[0]), interval=int(row[1]), last_post_time=int(row[2]), channel_name=row[3], channel_title=row[4], owner_id=int(row[-1]))

        return None

    def __str__(self) -> str:
        return f"Username:{self.name}\nTitle: {self.title}\nId: {self.id}\nInterval: {self.interval}\nOwner Id: {self.owner_id}"