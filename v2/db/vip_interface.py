import sqlite3
from tools import manuwriter
from tools.mathematix import after_n_months
from time import time
from datetime import datetime


class VIPDatabaseInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    ACCOUNT_ID = 'id'
    ACCOUNT_CURRENCIES = 'currencies'
    ACCOUNT_CRYPTOS = 'cryptos'
    ACCOUNT_LAST_INTERACTION = 'last_interaction'
    ACCOUNT_LANGUAGE = 'language'
    DATE_FORMAT = '%Y-%m-%d'
    ACCOUNT_VIP_END_DATE= 'vip_end_date'  # verified as vip
    ACCOUNT_VIP_MODE = 'vip_mode'
    ACCOUNT_ALL_FIELDS = f'({ACCOUNT_ID}, {ACCOUNT_CURRENCIES}, {ACCOUNT_CRYPTOS}, {ACCOUNT_LAST_INTERACTION}, {ACCOUNT_VIP_END_DATE}, {ACCOUNT_VIP_MODE}, {ACCOUNT_LANGUAGE})'

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNEL_ID = "id"
    CHANNEL_INTERVAL = "interval"
    CHANNEL_OWNER_ID = "owner_id"  # ref to account
    CHANNEL_NAME = "name"
    CHANNEL_LAST_POST_TIME = "last_post_time"
    CHANNEL_TITLE = "title"
    CHANNEL_ALL_FIELDS = f'({CHANNEL_ID}, {CHANNEL_NAME}, {CHANNEL_TITLE}, {CHANNEL_OWNER_ID}, {CHANNEL_INTERVAL}, {CHANNEL_LAST_POST_TIME})'

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
                    f"{VIPDatabaseInterface.ACCOUNT_CURRENCIES} TEXT, {VIPDatabaseInterface.ACCOUNT_CRYPTOS} TEXT, {VIPDatabaseInterface.ACCOUNT_LAST_INTERACTION} DATE, " +\
                        f"{VIPDatabaseInterface.ACCOUNT_VIP_END_DATE} DATE, {VIPDatabaseInterface.ACCOUNT_VIP_MODE} DATE, {VIPDatabaseInterface.ACCOUNT_LANGUAGE} TEXT)"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"VIP Database {VIPDatabaseInterface.TABLE_ACCOUNTS} table created successfuly.", category_name='vip_info')

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{VIPDatabaseInterface.TABLE_CHANNELS}'").fetchone():
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_CHANNELS} ({VIPDatabaseInterface.CHANNEL_ID} INTEGER PRIMARY KEY, " +\
                    f"{VIPDatabaseInterface.CHANNEL_INTERVAL} INTEGER, {VIPDatabaseInterface.CHANNEL_LAST_POST_TIME} INTEGER, " +\
                    f"{VIPDatabaseInterface.CHANNEL_NAME} TEXT, {VIPDatabaseInterface.CHANNEL_TITLE} TEXT," +\
                    f"{VIPDatabaseInterface.CHANNEL_OWNER_ID} INTEGER, FOREIGN KEY({VIPDatabaseInterface.CHANNEL_OWNER_ID}) REFERENCES {VIPDatabaseInterface.TABLE_ACCOUNTS}({VIPDatabaseInterface.ACCOUNT_ID}))"
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
        connection = None
        if not account:
            raise Exception("You must provide an Account to save")
        try:
            query = f"INSERT INTO {VIPDatabaseInterface.TABLE_ACCOUNTS} {VIPDatabaseInterface.ACCOUNT_ALL_FIELDS} VALUES (?, ?, ?, ?, ?, ?, ?)"
            connection = sqlite3.connect(self._name)
            cursor = connection.cursor()
            cursor.execute(query, (account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(VIPDatabaseInterface.DATE_FORMAT), \
                                   account.vip_end_date, account.vip_mode, account.language))
            manuwriter.log(f"New account: {account} saved into vip database successfully.", category_name=f'vip_info')
            cursor.close()
            connection.commit()
            connection.close()
        except Exception as ex:
            manuwriter.log(f"Cannot save this account:{account}", ex, category_name=f'vip_database')
            if connection:
                connection.close()
            raise ex  # custom ex needed here too

    def get(self, chat_id):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {VIPDatabaseInterface.TABLE_ACCOUNTS} WHERE {VIPDatabaseInterface.ACCOUNT_ID}=? LIMIT 1", (chat_id, ))
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        return row

    def get_all(self, column: str=ACCOUNT_ID) -> list:
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT ({column}) FROM {VIPDatabaseInterface.TABLE_ACCOUNTS}")
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        if column == VIPDatabaseInterface.ACCOUNT_LAST_INTERACTION:
            return [datetime.strptime(row[0], VIPDatabaseInterface.DATE_FORMAT) if row[0] else None for row in rows]
        return [row[0] for row in rows] # just return a list of ids

    def update(self, account):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {VIPDatabaseInterface.TABLE_ACCOUNTS} WHERE {VIPDatabaseInterface.ACCOUNT_ID}=? LIMIT 1", (account.chat_id, ))
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            FIELDS_TO_SET = f'{VIPDatabaseInterface.ACCOUNT_CURRENCIES}=?, {VIPDatabaseInterface.ACCOUNT_CRYPTOS}=?, {VIPDatabaseInterface.ACCOUNT_LAST_INTERACTION}=?, {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE}=?, {VIPDatabaseInterface.ACCOUNT_VIP_MODE}=?, {VIPDatabaseInterface.ACCOUNT_LANGUAGE}=?'
            cursor.execute(f'UPDATE {VIPDatabaseInterface.TABLE_ACCOUNTS} SET {FIELDS_TO_SET} WHERE {VIPDatabaseInterface.ACCOUNT_ID}=?', \
                (account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(VIPDatabaseInterface.DATE_FORMAT), \
                 account.vip_end_date.strftime(VIPDatabaseInterface.DATE_FORMAT) if account.vip_end_date else None, account.vip_mode, account.language, account.chat_id))
        else:
            cursor.execute(f"INSERT INTO {VIPDatabaseInterface.TABLE_ACCOUNTS} {VIPDatabaseInterface.ACCOUNT_ALL_FIELDS} VALUES (?, ?, ?, ?, ?, ?, ?)", \
                (account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(VIPDatabaseInterface.DATE_FORMAT), \
                 account.vip_end_date.strftime(VIPDatabaseInterface.DATE_FORMAT) if account.vip_end_date else None, account.vip_mode,  account.language))
            manuwriter.log("New account started using this bot with chat_id=: " + account.__str__(), category_name=f'vip_info')
        connection.commit()
        cursor.close()
        connection.close()

    def upgrade_account(self, account, months_count: int, vip_mode: int = 0):  # use vip mode
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        account.vip_end_date = after_n_months(months_count)
        str_vip_end_date = account.vip_end_date.strftime(VIPDatabaseInterface.DATE_FORMAT)
        cursor.execute(f'UPDATE {VIPDatabaseInterface.TABLE_ACCOUNTS} SET {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE}=?, {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE}=? WHERE {VIPDatabaseInterface.ACCOUNT_ID}=?', \
            (str_vip_end_date, vip_mode, account.chat_id))
        manuwriter.log(f"Account with chat_id={account.chat_id} has extended its vip previllages until {str_vip_end_date}")
        connection.commit()
        cursor.close()
        connection.close()

    def plan_channel(self, owner_chat_id: int, channel_id: int, channel_name: str, interval: int, channel_title: str):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_ID}=? LIMIT 1", (channel_id, ))
        now_in_minutes = time() // 60
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            FIELDS_TO_SET = f'{VIPDatabaseInterface.CHANNEL_OWNER_ID}=?, {VIPDatabaseInterface.CHANNEL_INTERVAL}=?, {VIPDatabaseInterface.CHANNEL_NAME}=?, {VIPDatabaseInterface.CHANNEL_TITLE}=?, {VIPDatabaseInterface.CHANNEL_LAST_POST_TIME}=?'
            cursor.execute(f'UPDATE {VIPDatabaseInterface.TABLE_CHANNELS} SET {FIELDS_TO_SET} WHERE {VIPDatabaseInterface.CHANNEL_ID}=?', \
                (owner_chat_id, interval, channel_name, channel_title, now_in_minutes, channel_id))
            manuwriter.log(f"Channel with the id of [{channel_id}, {channel_name}] has been RE-planned by owner_chat_id=: {owner_chat_id}", category_name='vip_info')
        else:
            cursor.execute(f"INSERT INTO {VIPDatabaseInterface.TABLE_CHANNELS} {VIPDatabaseInterface.CHANNEL_ALL_FIELDS} VALUES (?, ?, ?, ?, ?, ?)", \
                (channel_id, channel_name, channel_title, owner_chat_id, interval, now_in_minutes))
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

    def get_channels_by_interval(self, min_interval: int = 0) -> list:
        '''Finds all the channels with plan interval > min_interval'''
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_INTERVAL} > ?", (min_interval, ))
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        return rows

    def delete_channel(self, channel_id):
        '''Delete channel and its planning'''
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"DELETE FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_ID} = ?", (channel_id, ))
        connection.commit()
        cursor.close()
        connection.close()

    def __init__(self, name="vip_data.db"):
        self._name = name
        self.setup()

