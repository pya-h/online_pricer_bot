import sqlite3
from tools import manuwriter
from tools.mathematix import after_n_months, tz_today
from time import time
from datetime import datetime
from tools.exceptions import NoSuchPlusPlanException


class DatabasePlusInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    DATE_FORMAT = '%Y-%m-%d'
    ACCOUNT_COLUMNS = (ACCOUNT_ID, ACCOUNT_CURRENCIES, ACCOUNT_CRYPTOS, ACCOUNT_LAST_INTERACTION, ACCOUNT_PLUS_END_DATE, ACCOUNT_PLUS_PLAN_ID, ACCOUNT_LANGUAGE) =\
        ('id', 'currencies', 'cryptos', 'last_interaction', 'plus_end_date', 'plus_plan_id', 'language')
    ACCOUNT_ALL_FIELDS = f'({ACCOUNT_ID}, {ACCOUNT_CURRENCIES}, {ACCOUNT_CRYPTOS}, {ACCOUNT_LAST_INTERACTION}, {ACCOUNT_PLUS_END_DATE}, {ACCOUNT_PLUS_PLAN_ID}, {ACCOUNT_LANGUAGE})'

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNELS_COLUMNS = (CHANNEL_ID, CHANNEL_NAME, CHANNEL_TITLE, CHANNEL_OWNER_ID, CHANNEL_INTERVAL, CHANNEL_LAST_POST_TIME) =\
        ("id", "name", "title", "owner_id", "interval", "last_post_time")

    TABLE_PAYMENTS = "payments"
    PAYMENT_COLUMNS = (PAYMENT_ID, PAYMENT_CHATID, PAYMENT_ORDER_ID, PAYMENT_STATUS, PAYMENT_AMOUNT, PAYMENT_CURRENCY,\
        PAYMENT_PAID_AMOUNT, PAYMENT_PAID_CURRENCY, PAYMENT_PLUS_PLAN_ID, PAYMENT_CREATED_ON, PAYMENT_MODIFIED_AT) =\
        ("order_id", "chat_id", "id", "status", "amount", "currency", "paid_amount", "paid_currency", "plus_plan_id", "created", "modified")

    TABLE_PLUS_PLANS = "plus_plans"
    PLUS_PLANS_COLUMNS = (PLUS_PLAN_ID, PLUS_PLAN_PRICE, PLUS_PLAN_PRICE_CURRENCY, PLUS_PLAN_DURATION, PLUS_PLAN_LEVEL, PLUS_PLAN_TITLE, \
                          PLUS_PLAN_TITLE_EN,  PLUS_PLAN_DESCRIPTION, PLUS_PLAN_DESCRIPTION_EN) =\
        ("id", "price", "price_currency", "duration", "level", "title", "title_en", "description", "description_en")


    @staticmethod
    def Get():
        if not DatabasePlusInterface._instance:
            DatabasePlusInterface._instance = DatabasePlusInterface()
        return DatabasePlusInterface._instance

    def setup(self):
        connection = None
        try:
            connection = sqlite3.connect(self._name, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = connection.cursor()

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{DatabasePlusInterface.TABLE_PLUS_PLANS}'").fetchone():
                query = f"CREATE TABLE {DatabasePlusInterface.TABLE_PLUS_PLANS} ({DatabasePlusInterface.PLUS_PLAN_ID} INTEGER PRIMARY KEY," +\
                    f"{DatabasePlusInterface.PLUS_PLAN_PRICE} REAL NOT NULL, {DatabasePlusInterface.PLUS_PLAN_PRICE_CURRENCY} TEXT, " +\
                    f"{DatabasePlusInterface.PLUS_PLAN_DURATION} INTEGER NOT NULL, {DatabasePlusInterface.PLUS_PLAN_LEVEL} INTEGER, " +\
                    f"{DatabasePlusInterface.PLUS_PLAN_TITLE} TEXT NOT NULL, {DatabasePlusInterface.PLUS_PLAN_TITLE_EN} TEXT, " +\
                    f"{DatabasePlusInterface.PLUS_PLAN_DESCRIPTION} TEXT, {DatabasePlusInterface.PLUS_PLAN_DESCRIPTION_EN} TEXT)"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"PLUS Database {DatabasePlusInterface.TABLE_PLUS_PLANS} table created successfuly.", category_name='plus_info')

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{DatabasePlusInterface.TABLE_ACCOUNTS}'").fetchone():
                query = f"CREATE TABLE {DatabasePlusInterface.TABLE_ACCOUNTS} ({DatabasePlusInterface.ACCOUNT_ID} INTEGER PRIMARY KEY," +\
                    f"{DatabasePlusInterface.ACCOUNT_CURRENCIES} TEXT, {DatabasePlusInterface.ACCOUNT_CRYPTOS} TEXT, {DatabasePlusInterface.ACCOUNT_LAST_INTERACTION} DATE, " +\
                    f"{DatabasePlusInterface.ACCOUNT_PLUS_END_DATE} DATE, {DatabasePlusInterface.ACCOUNT_PLUS_PLAN_ID} INTEGER, {DatabasePlusInterface.ACCOUNT_LANGUAGE} TEXT," +\
                    f"FOREIGN KEY({DatabasePlusInterface.ACCOUNT_PLUS_PLAN_ID}) REFERENCES {DatabasePlusInterface.TABLE_PLUS_PLANS}({DatabasePlusInterface.PLUS_PLAN_ID}))"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"PLUS Database {DatabasePlusInterface.TABLE_ACCOUNTS} table created successfuly.", category_name='plus_info')

            # Table channels existence
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{DatabasePlusInterface.TABLE_CHANNELS}'").fetchone():
                query = f"CREATE TABLE {DatabasePlusInterface.TABLE_CHANNELS} ({DatabasePlusInterface.CHANNEL_ID} INTEGER PRIMARY KEY, " +\
                    f"{DatabasePlusInterface.CHANNEL_INTERVAL} INTEGER NOT_NULL, {DatabasePlusInterface.CHANNEL_LAST_POST_TIME} INTEGER, " +\
                    f"{DatabasePlusInterface.CHANNEL_NAME} TEXT, {DatabasePlusInterface.CHANNEL_TITLE} TEXT NOT_NULL," +\
                    f"{DatabasePlusInterface.CHANNEL_OWNER_ID} INTEGER NOT_NULL, FOREIGN KEY({DatabasePlusInterface.CHANNEL_OWNER_ID}) REFERENCES {DatabasePlusInterface.TABLE_ACCOUNTS}({DatabasePlusInterface.ACCOUNT_ID}))"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"PLUS Database {DatabasePlusInterface.TABLE_CHANNELS} table created successfuly.", category_name='plus_info')

            # Table payments existence check
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{DatabasePlusInterface.TABLE_PAYMENTS}'").fetchone():
                query = f"CREATE TABLE {DatabasePlusInterface.TABLE_PAYMENTS} ({DatabasePlusInterface.PAYMENT_ID} INTEGER NOT_NULL, " +\
                    f"{DatabasePlusInterface.PAYMENT_ORDER_ID} INTEGER NOT_NULL, {DatabasePlusInterface.PAYMENT_CHATID} INTEGER NOT_NULL, " +\
                    f"{DatabasePlusInterface.PAYMENT_AMOUNT} REAL NOT_NULL, {DatabasePlusInterface.PAYMENT_CURRENCY} TEXT NOT_NULL, " +\
                    f"{DatabasePlusInterface.PAYMENT_PAID_AMOUNT} REAL, {DatabasePlusInterface.PAYMENT_PAID_CURRENCY} TEXT, " +\
                    f"{DatabasePlusInterface.PAYMENT_STATUS} TEXT NOT NULL, {DatabasePlusInterface.PAYMENT_CREATED_ON} TEXT, {DatabasePlusInterface.PAYMENT_MODIFIED_AT} TEXT," +\
                    f"{DatabasePlusInterface.PAYMENT_PLUS_PLAN_ID} INTEGER NOT NULL, " +\
                    f"FOREIGN KEY({DatabasePlusInterface.PAYMENT_CHATID}) REFERENCES {DatabasePlusInterface.TABLE_ACCOUNTS}({DatabasePlusInterface.ACCOUNT_ID})," +\
                    f"FOREIGN KEY({DatabasePlusInterface.PAYMENT_PLUS_PLAN_ID}) REFERENCES {DatabasePlusInterface.TABLE_PLUS_PLANS}({DatabasePlusInterface.PLUS_PLAN_ID}))"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"plus Database {DatabasePlusInterface.TABLE_PAYMENTS} table created successfuly.", category_name='plus_info')


                # else: # TEMP-*****
            #     cursor.execute(f'ALTER TABLE {DatabaseInterface.TABLE_ACCOUNTS} ADD {DatabaseInterface.ACCOUNT_LAST_INTERACTION} DATE')
            #     connection.commit()
            manuwriter.log("plus Database setup completed.", category_name='plus_info')
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
            columns = ', '.join(DatabasePlusInterface.ACCOUNT_COLUMNS)
            query = f"INSERT INTO {DatabasePlusInterface.TABLE_ACCOUNTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?)"
            self.execute(False, query, account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(DatabasePlusInterface.DATE_FORMAT), \
                                   account.plus_end_date, account.plus_plan_id, account.language)
            manuwriter.log(f"New account: {account} saved into plus database successfully.", category_name=f'plus_info')
        except Exception as ex:
            manuwriter.log(f"Cannot save this account:{account}", ex, category_name=f'plus_database')
            raise ex  # custom ex needed here too

    def get(self, chat_id):
        accounts = self.execute(True, f"SELECT * FROM {DatabasePlusInterface.TABLE_ACCOUNTS} WHERE {DatabasePlusInterface.ACCOUNT_ID}=? LIMIT 1", chat_id)
        return accounts[0] if accounts else None

    def get_all(self, column: str=ACCOUNT_ID) -> list:
        rows = self.execute(True, f"SELECT ({column}) FROM {DatabasePlusInterface.TABLE_ACCOUNTS}")
        if column == DatabasePlusInterface.ACCOUNT_LAST_INTERACTION:
            return [datetime.strptime(row[0], DatabasePlusInterface.DATE_FORMAT) if row[0] else None for row in rows]
        return [row[0] for row in rows] # just return a list of ids

    def update(self, account):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {DatabasePlusInterface.TABLE_ACCOUNTS} WHERE {DatabasePlusInterface.ACCOUNT_ID}=? LIMIT 1", (account.chat_id, ))
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            columns_to_set = ', '.join([f'{field}=?' for field in DatabasePlusInterface.ACCOUNT_COLUMNS[1:]])

            cursor.execute(f'UPDATE {DatabasePlusInterface.TABLE_ACCOUNTS} SET {columns_to_set} WHERE {DatabasePlusInterface.ACCOUNT_ID}=?', \
                (account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(DatabasePlusInterface.DATE_FORMAT), \
                 account.plus_end_date.strftime(DatabasePlusInterface.DATE_FORMAT) if account.plus_end_date else None, account.plus_plan_id, account.language, account.chat_id))
        else:
            columns = ', '.join(DatabasePlusInterface.ACCOUNT_COLUMNS)
            cursor.execute(f"INSERT INTO {DatabasePlusInterface.TABLE_ACCOUNTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?)", \
                (account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(DatabasePlusInterface.DATE_FORMAT), \
                 account.plus_end_date.strftime(DatabasePlusInterface.DATE_FORMAT) if account.plus_end_date else None, account.plus_plan_id,  account.language))
            manuwriter.log("New account started using this bot with chat_id=: " + account.__str__(), category_name=f'plus_info')
        connection.commit()
        cursor.close()
        connection.close()

    def upgrade_account(self, account, plus_plan):  # use plus mode
        account.plus_end_date = after_n_months(plus_plan.duration_in_months)
        str_plus_end_date = account.plus_end_date.strftime(DatabasePlusInterface.DATE_FORMAT) if account.plus_end_date else None
        self.execute(False, f'UPDATE {DatabasePlusInterface.TABLE_ACCOUNTS} SET {DatabasePlusInterface.ACCOUNT_PLUS_END_DATE}=?, {DatabasePlusInterface.ACCOUNT_PLUS_PLAN_ID}=? WHERE {DatabasePlusInterface.ACCOUNT_ID}=?', \
            str_plus_end_date, plus_plan.id, account.chat_id)
        manuwriter.log(f"Account with chat_id={account.chat_id} has extended its plus previllages until {str_plus_end_date}")

    def plan_channel(self, owner_chat_id: int, channel_id: int, channel_name: str, interval: int, channel_title: str):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {DatabasePlusInterface.TABLE_CHANNELS} WHERE {DatabasePlusInterface.CHANNEL_ID}=? LIMIT 1", (channel_id, ))
        now_in_minutes = time() // 60
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            columns_to_set = ', '.join([f'{field}=?' for field in DatabasePlusInterface.CHANNELS_COLUMNS[1:]])
            cursor.execute(f'UPDATE {DatabasePlusInterface.TABLE_CHANNELS} SET {columns_to_set} WHERE {DatabasePlusInterface.CHANNEL_ID}=?', \
                (channel_name, channel_title, owner_chat_id, interval, now_in_minutes, channel_id))
            manuwriter.log(f"Channel with the id of [{channel_id}, {channel_name}] has been RE-planned by owner_chat_id=: {owner_chat_id}", category_name='plus_info')
        else:
            columns = ', '.join(DatabasePlusInterface.CHANNELS_COLUMNS)
            cursor.execute(f"INSERT INTO {DatabasePlusInterface.TABLE_CHANNELS} ({columns}) VALUES (?, ?, ?, ?, ?, ?)", \
                (channel_id, channel_name, channel_title, owner_chat_id, interval, now_in_minutes))
            manuwriter.log(f"New channel with the id of [{channel_id}, {channel_name}] has benn planned by owner_chat_id=: {owner_chat_id}", category_name='plus_info')
        connection.commit()
        cursor.close()
        connection.close()

    def get_channel(self, channel_id: int):
        channels = self.execute(True, f"SELECT * FROM {DatabasePlusInterface.TABLE_CHANNELS} WHERE {DatabasePlusInterface.CHANNEL_ID}=? LIMIT 1", channel_id)
        return channels[0] if channels else None

    def get_account_channels(self, owner_chat_id: int) -> list:
        '''Get all channels related to this account'''
        return self.execute(True, f"SELECT * FROM {DatabasePlusInterface.TABLE_CHANNELS} WHERE {DatabasePlusInterface.CHANNEL_OWNER_ID}=?", owner_chat_id)


    def get_channels_by_interval(self, min_interval: int = 0) -> list:
        '''Finds all the channels with plan interval > min_interval'''
        return self.execute(True, f"SELECT * FROM {DatabasePlusInterface.TABLE_CHANNELS} WHERE {DatabasePlusInterface.CHANNEL_INTERVAL} > ?", min_interval)

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
        self.execute(False, f"DELETE FROM {DatabasePlusInterface.TABLE_CHANNELS} WHERE {DatabasePlusInterface.CHANNEL_ID} = ?", channel_id)

    def define_plus_plan(self, title: str, titile_en: str, duration_in_months: int, price: float, price_currency: str = "USDT", plus_level: int = 1):
        fields = ', '.join(DatabasePlusInterface.PLUS_PLANS_COLUMNS[1:-2])  # in creation mode admin just defines persian title and description
        # if he wants to add english texts, he should go to edit menu
        self.execute(f"INSERT INTO {DatabasePlusInterface.TABLE_PLUS_PLANS} ({fields}) VALUES (?, ?, ?, ?, ?, ?)", \
            price, price_currency, duration_in_months, plus_level, title, titile_en)

    def get_plus_plan(self, plus_plan_id: int):
        vplans = self.execute(True, f"SELECT * FROM {DatabasePlusInterface.TABLE_PLUS_PLANS} WHERE {DatabasePlusInterface.PLUS_PLAN_ID}=? LIMIT 1", plus_plan_id)
        return vplans[0] if vplans else None

    def get_all_plus_plans(self):
        return self.execute(True, f"SELECT * FROM {DatabasePlusInterface.TABLE_PLUS_PLANS}")

    def update_plus_plan(self, plus_plan):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {DatabasePlusInterface.TABLE_PLUS_PLANS} WHERE {DatabasePlusInterface.PLUS_PLAN_ID}=? LIMIT 1", (plus_plan.id, ))
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            columns_to_set = ', '.join([f'{field}=?' for field in DatabasePlusInterface.PLUS_PLANS_COLUMNS[1:]])

            cursor.execute(f'UPDATE {DatabasePlusInterface.TABLE_PLUS_PLANS} SET {columns_to_set} WHERE {DatabasePlusInterface.PLUS_PLAN_ID}=?', \
                (plus_plan.price, plus_plan.price_currency, plus_plan.duration_in_months, plus_plan.plus_level, plus_plan.title, plus_plan.title_en, plus_plan.description, plus_plan.description_en))
        else:
            raise NoSuchPlusPlanException(plus_plan.id)
        connection.commit()
        cursor.close()
        connection.close()

    def update_payment(self, payment):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {DatabasePlusInterface.TABLE_PAYMENTS} WHERE {DatabasePlusInterface.PAYMENT_ORDER_ID}=? LIMIT 1", (payment.order_id, ))

        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            columns = ', '.join(f"{field}=?" for field in DatabasePlusInterface.PAYMENT_COLUMNS[2:])
            cursor.execute(f'UPDATE {DatabasePlusInterface.TABLE_PAYMENTS} SET {columns} WHERE {DatabasePlusInterface.PAYMENT_ORDER_ID}=?', \
                (payment.id, payment.status, payment.amount, payment.currency, payment.paid_amount, payment.paid_currency, payment.plus_plan.id, \
                    payment.created_at, payment.modified_at, payment.order_id))
            manuwriter.log(f"Payment with order_id of {payment.order_id}, and payment id of {payment.id} status changed to {payment.status}", category_name='payments')
        else:
            columns = ', '.join(DatabasePlusInterface.PAYMENT_COLUMNS)
            cursor.execute(f"INSERT INTO {DatabasePlusInterface.TABLE_PAYMENTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", \
                (payment.order_id, payment.payer_chat_id, payment.id, payment.status, payment.amount, payment.currency.upper(), \
                payment.paid_amount, payment.paid_currency.upper(), payment.plus_plan.id, payment.created_at, payment.modified_at))
            manuwriter.log(f"New payment with the id of {payment.id} and order_id of {payment.order_id}, and status of {payment.status} added for user with chatid =: {payment.payer_chat_id}", category_name='payments')
        connection.commit()
        cursor.close()
        connection.close()

    def get_payment(self, order_id):
        columns = ', '.join(DatabasePlusInterface.PAYMENT_COLUMNS)
        return self.execute(True, f"SELECT {columns} from {DatabasePlusInterface.TABLE_PAYMENTS} WHERE {DatabasePlusInterface.PAYMENT_ORDER_ID}=? ", order_id)

    def __init__(self, name="plus_data.db"):
        self._name = name
        self.setup()

