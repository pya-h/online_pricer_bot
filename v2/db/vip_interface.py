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
    ACCOUNT_VIP_PLAN_ID = 'vip_plan_id'
    ACCOUNT_ALL_FIELDS = f'({ACCOUNT_ID}, {ACCOUNT_CURRENCIES}, {ACCOUNT_CRYPTOS}, {ACCOUNT_LAST_INTERACTION}, {ACCOUNT_VIP_END_DATE}, {ACCOUNT_VIP_PLAN_ID}, {ACCOUNT_LANGUAGE})'

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNEL_ID = "id"
    CHANNEL_INTERVAL = "interval"
    CHANNEL_OWNER_ID = "owner_id"  # ref to account
    CHANNEL_NAME = "name"
    CHANNEL_LAST_POST_TIME = "last_post_time"
    CHANNEL_TITLE = "title"
    CHANNEL_ALL_FIELDS = f'({CHANNEL_ID}, {CHANNEL_NAME}, {CHANNEL_TITLE}, {CHANNEL_OWNER_ID}, {CHANNEL_INTERVAL}, {CHANNEL_LAST_POST_TIME})'

    TABLE_PAYMENTS = "payments"
    PAYMENT_ID = "id"
    PAYMENT_ORDER_ID = "order_id"
    PAYMENT_STATUS = "status"
    PAYMENT_AMOUNT = "amount"
    PAYMENT_CURRENCY = "CURRENCY"
    PAYMENT_PAID_AMOUNT = "paid_amount"
    PAYMENT_PAID_CURRENCY = "paid_CURRENCY"
    PAYMENT_CHATID = "chat_id"
    PAYMENT_VIP_PLAN_ID = "vip_plan_id"
    PAYMENT_NETWORK = "network"
    
    TABLE_VIP_PLANS = "vip_plans"
    VIP_PLAN_ID = "id"
    VIP_PLAN_DESCRIPTION = "description"
    VIP_PLAN_TITLE = "title"
    VIP_PLAN_DURATION = "duration" # in months
    VIP_PLAN_LEVEL = "level"

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
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{VIPDatabaseInterface.TABLE_VIP_PLANS}'").fetchone():
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_VIP_PLANS} ({VIPDatabaseInterface.VIP_PLAN_ID} INTEGER PRIMARY KEY," +\
                    f"{VIPDatabaseInterface.VIP_PLAN_TITLE} TEXT, {VIPDatabaseInterface.VIP_PLAN_DESCRIPTION} TEXT, " +\
                    f"{VIPDatabaseInterface.VIP_PLAN_DURATION} INTEGER, {VIPDatabaseInterface.VIP_PLAN_LEVEL} INTEGER)"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"VIP Database {VIPDatabaseInterface.TABLE_VIP_PLANS} table created successfuly.", category_name='vip_info')

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{VIPDatabaseInterface.TABLE_ACCOUNTS}'").fetchone():
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_ACCOUNTS} ({VIPDatabaseInterface.ACCOUNT_ID} INTEGER PRIMARY KEY," +\
                    f"{VIPDatabaseInterface.ACCOUNT_CURRENCIES} TEXT, {VIPDatabaseInterface.ACCOUNT_CRYPTOS} TEXT, {VIPDatabaseInterface.ACCOUNT_LAST_INTERACTION} DATE, " +\
                    f"{VIPDatabaseInterface.ACCOUNT_VIP_END_DATE} DATE, {VIPDatabaseInterface.ACCOUNT_VIP_PLAN_ID} INTEGER, {VIPDatabaseInterface.ACCOUNT_LANGUAGE} TEXT," +\
                    f"FOREIGN KEY({VIPDatabaseInterface.ACCOUNT_VIP_PLAN_ID}) REFERENCES {VIPDatabaseInterface.TABLE_VIP_PLANS}({VIPDatabaseInterface.VIP_PLAN_ID}))"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"VIP Database {VIPDatabaseInterface.TABLE_ACCOUNTS} table created successfuly.", category_name='vip_info')

            # Table channels existence
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{VIPDatabaseInterface.TABLE_CHANNELS}'").fetchone():
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_CHANNELS} ({VIPDatabaseInterface.CHANNEL_ID} INTEGER PRIMARY KEY, " +\
                    f"{VIPDatabaseInterface.CHANNEL_INTERVAL} INTEGER, {VIPDatabaseInterface.CHANNEL_LAST_POST_TIME} INTEGER, " +\
                    f"{VIPDatabaseInterface.CHANNEL_NAME} TEXT, {VIPDatabaseInterface.CHANNEL_TITLE} TEXT," +\
                    f"{VIPDatabaseInterface.CHANNEL_OWNER_ID} INTEGER, FOREIGN KEY({VIPDatabaseInterface.CHANNEL_OWNER_ID}) REFERENCES {VIPDatabaseInterface.TABLE_ACCOUNTS}({VIPDatabaseInterface.ACCOUNT_ID}))"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"VIP Database {VIPDatabaseInterface.TABLE_CHANNELS} table created successfuly.", category_name='vip_info')

            # Table payments existence check
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{VIPDatabaseInterface.TABLE_PAYMENTS}'").fetchone():
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_PAYMENTS} ({VIPDatabaseInterface.PAYMENT_ID} INTEGER PRIMARY KEY, " +\
                    f"{VIPDatabaseInterface.PAYMENT_ORDER_ID} INTEGER, {VIPDatabaseInterface.PAYMENT_CHATID} INTEGER, " +\
                    f"{VIPDatabaseInterface.PAYMENT_AMOUNT} REAL, {VIPDatabaseInterface.PAYMENT_CURRENCY} TEXT, " +\
                    f"{VIPDatabaseInterface.PAYMENT_PAID_AMOUNT} REAL, {VIPDatabaseInterface.PAYMENT_PAID_CURRENCY} TEXT, " +\
                    f"{VIPDatabaseInterface.PAYMENT_STATUS} TEXT, {VIPDatabaseInterface.PAYMENT_NETWORK} TEXT," +\
                    f"{VIPDatabaseInterface.PAYMENT_VIP_PLAN_ID} INTEGER, " +\
                    f"FOREIGN KEY({VIPDatabaseInterface.PAYMENT_CHATID}) REFERENCES {VIPDatabaseInterface.TABLE_ACCOUNTS}({VIPDatabaseInterface.ACCOUNT_ID})," +\
                    f"FOREIGN KEY({VIPDatabaseInterface.PAYMENT_VIP_PLAN_ID}) REFERENCES {VIPDatabaseInterface.TABLE_VIP_PLANS}({VIPDatabaseInterface.VIP_PLAN_ID}))"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"VIP Database {VIPDatabaseInterface.TABLE_PAYMENTS} table created successfuly.", category_name='vip_info')


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
        if not account:
            raise Exception("You must provide an Account to save")
        try:
            query = f"INSERT INTO {VIPDatabaseInterface.TABLE_ACCOUNTS} {VIPDatabaseInterface.ACCOUNT_ALL_FIELDS} VALUES (?, ?, ?, ?, ?, ?, ?)"
            self.execute(False, query, account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(VIPDatabaseInterface.DATE_FORMAT), \
                                   account.vip_end_date, account.vip_plan_id, account.language)
            manuwriter.log(f"New account: {account} saved into vip database successfully.", category_name=f'vip_info')
        except Exception as ex:
            manuwriter.log(f"Cannot save this account:{account}", ex, category_name=f'vip_database')
            raise ex  # custom ex needed here too

    def get(self, chat_id):
        accounts = self.execute(True, f"SELECT * FROM {VIPDatabaseInterface.TABLE_ACCOUNTS} WHERE {VIPDatabaseInterface.ACCOUNT_ID}=? LIMIT 1", chat_id)
        return accounts[0] if accounts else None

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
            FIELDS_TO_SET = f'{VIPDatabaseInterface.ACCOUNT_CURRENCIES}=?, {VIPDatabaseInterface.ACCOUNT_CRYPTOS}=?, {VIPDatabaseInterface.ACCOUNT_LAST_INTERACTION}=?, {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE}=?, {VIPDatabaseInterface.ACCOUNT_VIP_PLAN_ID}=?, {VIPDatabaseInterface.ACCOUNT_LANGUAGE}=?'
            cursor.execute(f'UPDATE {VIPDatabaseInterface.TABLE_ACCOUNTS} SET {FIELDS_TO_SET} WHERE {VIPDatabaseInterface.ACCOUNT_ID}=?', \
                (account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(VIPDatabaseInterface.DATE_FORMAT), \
                 account.vip_end_date.strftime(VIPDatabaseInterface.DATE_FORMAT) if account.vip_end_date else None, account.vip_plan_id, account.language, account.chat_id))
        else:
            cursor.execute(f"INSERT INTO {VIPDatabaseInterface.TABLE_ACCOUNTS} {VIPDatabaseInterface.ACCOUNT_ALL_FIELDS} VALUES (?, ?, ?, ?, ?, ?, ?)", \
                (account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(VIPDatabaseInterface.DATE_FORMAT), \
                 account.vip_end_date.strftime(VIPDatabaseInterface.DATE_FORMAT) if account.vip_end_date else None, account.vip_plan_id,  account.language))
            manuwriter.log("New account started using this bot with chat_id=: " + account.__str__(), category_name=f'vip_info')
        connection.commit()
        cursor.close()
        connection.close()

    def upgrade_account(self, account, months_count: int, vip_plan_id: int = 0):  # use vip mode
        account.vip_end_date = after_n_months(months_count)
        str_vip_end_date = account.vip_end_date.strftime(VIPDatabaseInterface.DATE_FORMAT)
        self.execute(False, f'UPDATE {VIPDatabaseInterface.TABLE_ACCOUNTS} SET {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE}=?, {VIPDatabaseInterface.ACCOUNT_VIP_END_DATE}=? WHERE {VIPDatabaseInterface.ACCOUNT_ID}=?', \
            str_vip_end_date, vip_plan_id, account.chat_id)
        manuwriter.log(f"Account with chat_id={account.chat_id} has extended its vip previllages until {str_vip_end_date}")


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
        channels = self.execute(True, f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_ID}=? LIMIT 1", channel_id)
        return channels[0] if channels else None

    def get_account_channels(self, owner_chat_id: int) -> list:
        '''Get all channels related to this account'''
        return self.execute(True, f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_OWNER_ID}=?", owner_chat_id)


    def get_channels_by_interval(self, min_interval: int = 0) -> list:
        '''Finds all the channels with plan interval > min_interval'''
        return self.execute(True, f"SELECT * FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_INTERVAL} > ?", min_interval)

    def execute(self, is_fetch_query: bool, query: str, *params):
        '''Execute queries that doesnt return result such as insert or delete'''
        rows = None
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(query, (*params, ))
        if is_fetch_query:
            rows = cursor.fetchall()
        else:  # its a change and needs to be saved
            connection.commit()
        cursor.close()
        connection.close()
        return rows
        
    def delete_channel(self, channel_id: int):
        '''Delete channel and its planning'''
        self.execute(False, f"DELETE FROM {VIPDatabaseInterface.TABLE_CHANNELS} WHERE {VIPDatabaseInterface.CHANNEL_ID} = ?", channel_id)

    def define_plan(self, title: str, description: str, duration_in_months: int, level: int = 1):
        pass
    def __init__(self, name="vip_data.db"):
        self._name = name
        self.setup()

