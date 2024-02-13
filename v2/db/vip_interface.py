from db.interface import DatabaseInterface
import sqlite3
from tools import manuwriter
from tools.mathematix import after_n_months
from time import time

class VIPDatabaseInterface(DatabaseInterface):
    _instance = None

    ACCOUNT_VIP_END_DATE= 'vip_end_date'  # verified as vip
    ACCOUNT_ALL_FIELDS = f'({DatabaseInterface.ACCOUNT_ID}, {DatabaseInterface.ACCOUNT_CURRENCIES}, {DatabaseInterface.ACCOUNT_CRYPTOS}, {DatabaseInterface.ACCOUNT_LAST_INTERACTION}, {ACCOUNT_VIP_END_DATE})'

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNEL_ID = "id"
    CHANNEL_INTERVAL = "interval"
    CHANNEL_OWNER_ID = "owner_id"  # ref to account
    CHANNEL_NAME = "name"
    CHANNEL_LAST_POST_TIME = "last_post_time"
    CHANNEL_ALL_FIELDS = f'({CHANNEL_ID}, {CHANNEL_NAME}, {CHANNEL_OWNER_ID}, {CHANNEL_INTERVAL}, {CHANNEL_LAST_POST_TIME})'

    @staticmethod
    def Get():
        if not VIPDatabaseInterface._instance:
            VIPDatabaseInterface._instance = VIPDatabaseInterface()
        return VIPDatabaseInterface._instance

    def setup(self):
        connection = None
        try:
            connection = sqlite3.connect(self._name, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = connection.cursor()

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{VIPDatabaseInterface.TABLE_ACCOUNTS}'").fetchone():
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_ACCOUNTS} ({VIPDatabaseInterface.ACCOUNT_ID} INTEGER PRIMARY KEY," +\
                    f"{VIPDatabaseInterface.ACCOUNT_CURRENCIES} TEXT, {VIPDatabaseInterface.ACCOUNT_CRYPTOS} TEXT, {VIPDatabaseInterface.ACCOUNT_LAST_INTERACTION} DATE, {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE} DATE)"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"VIP Database {VIPDatabaseInterface.TABLE_ACCOUNTS} table created successfuly.", category_name='vip_info')

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{VIPDatabaseInterface.TABLE_CHANNELS}'").fetchone():
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_CHANNELS} ({VIPDatabaseInterface.CHANNEL_ID} INTEGER PRIMARY KEY, {VIPDatabaseInterface.CHANNEL_NAME} TEXT, {VIPDatabaseInterface.CHANNEL_LAST_POST_TIME} INTEGER, " +\
                    f"{VIPDatabaseInterface.CHANNEL_INTERVAL} INTEGER, {VIPDatabaseInterface.CHANNEL_OWNER_ID} INTEGER, FOREIGN KEY({VIPDatabaseInterface.CHANNEL_OWNER_ID}) REFERENCES {VIPDatabaseInterface.TABLE_ACCOUNTS}({VIPDatabaseInterface.ACCOUNT_ID}))"
                print(query)
                # create table account
                cursor.execute(query)
                manuwriter.log(f"VIP Database {VIPDatabaseInterface.TABLE_CHANNELS} table created successfuly.", category_name='vip_info')


                # else: # TEMP-*****
            #     cursor.execute(f'ALTER TABLE {DatabaseInterface.TABLE_ACCOUNTS} ADD {DatabaseInterface.ACCOUNT_LAST_INTERACTION} DATE')
            #     connection.commit()
            manuwriter.log("VIP Database setup completed.", category_name='vip_info')
            cursor.close()
            connection.close()
        except Exception as ex:
            if connection:
                connection.close()
            raise ex  # create custom exception for this


    def add(self, account):
        super().add(account, log_category_prefix='vip_')

    def update(self, account):
        super().update(account, log_category_prefix='vip_')

    def upgrade_account(self, account, months_count: int):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        str_vip_end_date = after_n_months(months_count).strftime(DatabaseInterface.DATE_FORMAT)
        cursor.execute(f'UPDATE {VIPDatabaseInterface.TABLE_ACCOUNTS} SET {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE}=? WHERE {VIPDatabaseInterface.ACCOUNT_ID}=?', \
            (str_vip_end_date, account.chat_id))
        manuwriter.log(f"Account with chat_id={account.chat_id} has extended its vip previllages until {str_vip_end_date}")
        connection.commit()
        cursor.close()
        connection.close()

    def plan_channel(self, owner_chat_id: int, channel_id: int, channel_name: str, interval: int):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_ID}=? LIMIT 1", (channel_id, ))
        now_in_minutes = time() // 60
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            FIELDS_TO_SET = f'{VIPDatabaseInterface.CHANNEL_OWNER_ID}=?, {VIPDatabaseInterface.CHANNEL_INTERVAL}=?, {VIPDatabaseInterface.CHANNEL_NAME}=?, {VIPDatabaseInterface.CHANNEL_LAST_POST_TIME}=?'
            cursor.execute(f'UPDATE {VIPDatabaseInterface.TABLE_CHANNELS} SET {FIELDS_TO_SET} WHERE {VIPDatabaseInterface.CHANNEL_ID}=?', \
                (owner_chat_id, interval, channel_name, now_in_minutes, channel_id))
            manuwriter.log(f"Channel with the id of [{channel_id}, {channel_name}] has been RE-planned by owner_chat_id=: {owner_chat_id}", category_name='vip_info')
        else:
            cursor.execute(f"INSERT INTO {VIPDatabaseInterface.TABLE_CHANNELS} {VIPDatabaseInterface.CHANNEL_ALL_FIELDS} VALUES (?, ?, ?, ?, ?)", \
                (channel_id, channel_name, owner_chat_id, interval, now_in_minutes))
            manuwriter.log(f"New channel with the id of [{channel_id}, {channel_name}] has benn planned by owner_chat_id=: {owner_chat_id}", category_name='vip_info')
        connection.commit()
        cursor.close()
        connection.close()

    def get_channel(self, channel_id: int):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_ID}=? LIMIT 1", (channel_id, ))
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        return row

    def get_account_channels(self, owner_chat_id: int) -> list:
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_OWNER_ID}=?", (owner_chat_id, ))
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        return rows


    def __init__(self, name="vip_data.db"):
        self._name = name
        self.setup()

