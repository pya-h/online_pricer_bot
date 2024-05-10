import sqlite3
from datetime import datetime
from tools.manuwriter import log
from tools.exceptions import NoSuchPlusPlanException
from tools.mathematix import after_n_months
from time import time


class DatabaseInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    DATE_FORMAT = '%Y-%m-%d'
    ACCOUNT_COLUMNS = (ACCOUNT_ID, ACCOUNT_CURRENCIES, ACCOUNT_CRYPTOS, ACCOUNT_CALC_CURRENCIES, ACCOUNT_CALC_CRYPTOS, ACCOUNT_LAST_INTERACTION, ACCOUNT_PLUS_END_DATE,
                       ACCOUNT_PLUS_PLAN_ID, ACCOUNT_STATE, ACCOUNT_CACHE, ACCOUNT_IS_ADMIN, ACCOUNT_LANGUAGE) = \
        ('id', 'currencies', 'cryptos', 'calc_cryptos', 'calc_currencies', 'last_interaction', 'plus_end_date', 'plus_plan_id', 'state', 'cache', 'admin',
         'language')

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNELS_COLUMNS = ( # TODO: Add cryptos/currencies list to this too. for configing what price data must be sent to channel
        CHANNEL_ID, CHANNEL_NAME, CHANNEL_TITLE, CHANNEL_OWNER_ID, CHANNEL_INTERVAL, CHANNEL_LAST_POST_TIME) = \
        ("id", "name", "title", "owner_id", "interval", "last_post_time")

    TABLE_PAYMENTS = "payments"
    PAYMENT_COLUMNS = (PAYMENT_ID, PAYMENT_CHATID, PAYMENT_ORDER_ID, PAYMENT_STATUS, PAYMENT_AMOUNT, PAYMENT_CURRENCY,
                       PAYMENT_PAID_AMOUNT, PAYMENT_PAID_CURRENCY, PAYMENT_PLUS_PLAN_ID, PAYMENT_CREATED_ON,
                       PAYMENT_MODIFIED_AT) = \
        ("order_id", "chat_id", "id", "status", "amount", "currency", "paid_amount", "paid_currency", "plus_plan_id",
         "created", "modified")

    TABLE_PLUS_PLANS = "plus_plans"
    PLUS_PLANS_COLUMNS = (
        PLUS_PLAN_ID, PLUS_PLAN_PRICE, PLUS_PLAN_PRICE_CURRENCY, PLUS_PLAN_DURATION, PLUS_PLAN_LEVEL, PLUS_PLAN_TITLE,
        PLUS_PLAN_TITLE_EN, PLUS_PLAN_DESCRIPTION, PLUS_PLAN_DESCRIPTION_EN) = \
        ("id", "price", "price_currency", "duration", "level", "title", "title_en", "description", "description_en")

    @staticmethod
    def Get():
        if not DatabaseInterface._instance:
            DatabaseInterface._instance = DatabaseInterface()
        return DatabaseInterface._instance

    def sync(self):
        """cursor.execute(f'ALTER TABLE {self.TABLE_ACCOUNTS} ADD {self.ACCOUNT_LAST_INTERACTION} DATE')
        connection.commit()"""

    def setup(self):
        connection = None
        try:
            connection = sqlite3.connect(self._name, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = connection.cursor()

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_PLUS_PLANS}'").fetchone():
                query = f"CREATE TABLE {self.TABLE_PLUS_PLANS} ({self.PLUS_PLAN_ID} INTEGER PRIMARY KEY," + \
                        f"{self.PLUS_PLAN_PRICE} REAL NOT NULL, {self.PLUS_PLAN_PRICE_CURRENCY} TEXT, " + \
                        f"{self.PLUS_PLAN_DURATION} INTEGER NOT NULL, {self.PLUS_PLAN_LEVEL} INTEGER, " + \
                        f"{self.PLUS_PLAN_TITLE} TEXT NOT NULL, {self.PLUS_PLAN_TITLE_EN} TEXT, " + \
                        f"{self.PLUS_PLAN_DESCRIPTION} TEXT, {self.PLUS_PLAN_DESCRIPTION_EN} TEXT)"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_PLUS_PLANS} table created successfuly.", category_name='plus_info')

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_ACCOUNTS}'").fetchone():
                query = f"CREATE TABLE {self.TABLE_ACCOUNTS} ({self.ACCOUNT_ID} INTEGER PRIMARY KEY," + \
                        f"{self.ACCOUNT_CURRENCIES} TEXT, {self.ACCOUNT_CRYPTOS} TEXT, {self.ACCOUNT_CALC_CURRENCIES} TEXT, {self.ACCOUNT_CALC_CRYPTOS} TEXT," + \
                        f"{self.ACCOUNT_LAST_INTERACTION} DATE, {self.ACCOUNT_PLUS_END_DATE} DATE, {self.ACCOUNT_PLUS_PLAN_ID} INTEGER," + \
                        f"{self.ACCOUNT_STATE} INTEGER DEFAULT 0, {self.ACCOUNT_CACHE} TEXT DEFAULT NULL, " + \
                        f"{self.ACCOUNT_IS_ADMIN} INTEGER DEFAULT 0, {self.ACCOUNT_LANGUAGE} TEXT, " + \
                        f"FOREIGN KEY({self.ACCOUNT_PLUS_PLAN_ID}) REFERENCES {self.TABLE_PLUS_PLANS}({self.PLUS_PLAN_ID}))"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_ACCOUNTS} table created successfully.", category_name='plus_info')
            else:  # TEMP-*****
                self.sync()

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_CHANNELS}'").fetchone():
                query = f"CREATE TABLE {self.TABLE_CHANNELS} ({self.CHANNEL_ID} INTEGER PRIMARY KEY, " + \
                        f"{self.CHANNEL_INTERVAL} INTEGER NOT_NULL, {self.CHANNEL_LAST_POST_TIME} INTEGER, " + \
                        f"{self.CHANNEL_NAME} TEXT, {self.CHANNEL_TITLE} TEXT NOT_NULL," + \
                        f"{self.CHANNEL_OWNER_ID} INTEGER NOT_NULL, FOREIGN KEY({self.CHANNEL_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_CHANNELS} table created successfuly.", category_name='plus_info')

            # Table payments existence check
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_PAYMENTS}'").fetchone():
                query = f"CREATE TABLE {self.TABLE_PAYMENTS} ({self.PAYMENT_ID} INTEGER NOT_NULL, " + \
                        f"{self.PAYMENT_ORDER_ID} INTEGER NOT_NULL, {self.PAYMENT_CHATID} INTEGER NOT_NULL, " + \
                        f"{self.PAYMENT_AMOUNT} REAL NOT_NULL, {self.PAYMENT_CURRENCY} TEXT NOT_NULL, " + \
                        f"{self.PAYMENT_PAID_AMOUNT} REAL, {self.PAYMENT_PAID_CURRENCY} TEXT, " + \
                        f"{self.PAYMENT_STATUS} TEXT NOT NULL, {self.PAYMENT_CREATED_ON} TEXT, {self.PAYMENT_MODIFIED_AT} TEXT," + \
                        f"{self.PAYMENT_PLUS_PLAN_ID} INTEGER NOT NULL, " + \
                        f"FOREIGN KEY({self.PAYMENT_CHATID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID})," + \
                        f"FOREIGN KEY({self.PAYMENT_PLUS_PLAN_ID}) REFERENCES {self.TABLE_PLUS_PLANS}({self.PLUS_PLAN_ID}))"
                # create table account
                cursor.execute(query)
                log(f"plus Database {self.TABLE_PAYMENTS} table created successfuly.", category_name='plus_info')

            log("plus Database setup completed.", category_name='plus_info')
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
            columns = ', '.join(self.ACCOUNT_COLUMNS)
            query = f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            self.execute(False, query, account.chat_id, account.str_desired_currencies(), account.str_desired_cryptos(), account.str_calc_currencies(),
                         account.str_calc_cryptos(), account.last_interaction.strftime(self.DATE_FORMAT), account.plus_end_date, account.plus_plan_id,
                         account.state.value, account.cache, account.is_admin, account.language)
            log(f"New account: {account} saved into plus database successfully.", category_name=f'plus_info')
        except Exception as ex:
            log(f"Cannot save this account:{account}", ex, category_name=f'plus_database')
            raise ex  # custom ex needed here too

    def get(self, chat_id):
        accounts = self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=? LIMIT 1", chat_id)
        return accounts[0] if accounts else None

    def get_all(self, column: str = ACCOUNT_ID) -> list:
        rows = self.execute(True, f"SELECT ({column}) FROM {self.TABLE_ACCOUNTS}")
        if column == self.ACCOUNT_LAST_INTERACTION:
            return [datetime.strptime(row[0], self.DATE_FORMAT) if row[0] else None for row in rows]
        return [row[0] for row in rows]  # just return a list of ids

    def update(self, account):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=? LIMIT 1", (account.chat_id,))
        if cursor.fetchone():  # if account with his chat id has been saved before in the database
            columns_to_set = ', '.join([f'{field}=?' for field in self.ACCOUNT_COLUMNS[1:]])

            cursor.execute(f'UPDATE {self.TABLE_ACCOUNTS} SET {columns_to_set} WHERE {self.ACCOUNT_ID}=?',
                           (account.str_desired_currencies(), account.str_desired_cryptos(), account.str_calc_currencies(),
                            account.str_calc_cryptos(), account.last_interaction.strftime(self.DATE_FORMAT),
                            account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None,
                            account.plus_plan_id, account.state.value, account.cache, account.is_admin, account.language, account.chat_id))
        else:
            columns = ', '.join(self.ACCOUNT_COLUMNS)
            cursor.execute(f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (account.chat_id, account.str_desired_currencies(), account.str_desired_cryptos(), account.str_calc_currencies(),
                            account.str_calc_cryptos(), account.last_interaction.strftime(self.DATE_FORMAT),
                            account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None,
                            account.plus_plan_id, account.state.value, account.cache, account.is_admin, account.language))
            log("New account started using this bot with chat_id=: " + account.__str__(), category_name=f'plus_info')
        connection.commit()
        cursor.close()
        connection.close()

    def upgrade_account(self, account, plus_plan):  # use plus mode
        account.plus_end_date = after_n_months(plus_plan.duration_in_months)
        str_plus_end_date = account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None
        self.execute(False,
                     f'UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_END_DATE}=?, {self.ACCOUNT_PLUS_PLAN_ID}=? WHERE {self.ACCOUNT_ID}=?', \
                     str_plus_end_date, plus_plan.id, account.chat_id)
        log(f"Account with chat_id={account.chat_id} has extended its plus previllages until {str_plus_end_date}")

    def plan_channel(self, owner_chat_id: int, channel_id: int, channel_name: str, interval: int, channel_title: str):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID}=? LIMIT 1", (channel_id,))
        now_in_minutes = time() // 60
        if cursor.fetchone():  # if account with his chat id has been saved before in the database
            columns_to_set = ', '.join([f'{field}=?' for field in self.CHANNELS_COLUMNS[1:]])
            cursor.execute(f'UPDATE {self.TABLE_CHANNELS} SET {columns_to_set} WHERE {self.CHANNEL_ID}=?', \
                           (channel_name, channel_title, owner_chat_id, interval, now_in_minutes, channel_id))
            log(f"Channel with the id of [{channel_id}, {channel_name}] has been RE-planned by owner_chat_id=: {owner_chat_id}",
                category_name='plus_info')
        else:
            columns = ', '.join(self.CHANNELS_COLUMNS)
            cursor.execute(f"INSERT INTO {self.TABLE_CHANNELS} ({columns}) VALUES (?, ?, ?, ?, ?, ?)", \
                           (channel_id, channel_name, channel_title, owner_chat_id, interval, now_in_minutes))
            log(f"New channel with the id of [{channel_id}, {channel_name}] has benn planned by owner_chat_id=: {owner_chat_id}",
                category_name='plus_info')
        connection.commit()
        cursor.close()
        connection.close()

    def get_channel(self, channel_id: int):
        channels = self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID}=? LIMIT 1",
                                channel_id)
        return channels[0] if channels else None

    def get_account_channels(self, owner_chat_id: int) -> list:
        """Get all channels related to this account"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_OWNER_ID}=?", owner_chat_id)

    def get_channels_by_interval(self, min_interval: int = 0) -> list:
        """Finds all the channels with plan interval > min_interval"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_INTERVAL} > ?",
                            min_interval)

    def execute(self, is_fetch_query: bool, query: str, *params):
        """Execute queries that doesnt return result such as insert or delete"""
        rows = None
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(query, (*params,))
        if is_fetch_query:
            rows = cursor.fetchall()
        else:
            connection.commit()
        cursor.close()
        connection.close()
        return rows

    def delete_channel(self, channel_id: int):
        """Delete channel and its planning"""
        self.execute(False, f"DELETE FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID} = ?", channel_id)

    def define_plus_plan(self, title: str, title_en: str, duration_in_months: int, price: float,
                         price_currency: str = "USDT", plus_level: int = 1):
        fields = ', '.join(
            self.PLUS_PLANS_COLUMNS[1:-2])  # in creation mode admin just defines persian title and description
        # if he wants to add english texts, he should go to edit menu
        self.execute(False, f"INSERT INTO {self.TABLE_PLUS_PLANS} ({fields}) VALUES (?, ?, ?, ?, ?, ?)", \
                     price, price_currency, duration_in_months, plus_level, title, title_en)

    def get_plus_plan(self, plus_plan_id: int):
        vplans = self.execute(True, f"SELECT * FROM {self.TABLE_PLUS_PLANS} WHERE {self.PLUS_PLAN_ID}=? LIMIT 1",
                              plus_plan_id)
        return vplans[0] if vplans else None

    def get_all_plus_plans(self):
        return self.execute(True, f"SELECT * FROM {self.TABLE_PLUS_PLANS}")

    def update_plus_plan(self, plus_plan):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {self.TABLE_PLUS_PLANS} WHERE {self.PLUS_PLAN_ID}=? LIMIT 1", (plus_plan.id,))
        if cursor.fetchone():  # if account with his chat id has been saved before in the database
            columns_to_set = ', '.join([f'{field}=?' for field in self.PLUS_PLANS_COLUMNS[1:]])

            cursor.execute(f'UPDATE {self.TABLE_PLUS_PLANS} SET {columns_to_set} WHERE {self.PLUS_PLAN_ID}=?', \
                           (plus_plan.price, plus_plan.price_currency, plus_plan.duration_in_months,
                            plus_plan.plus_level, plus_plan.title, plus_plan.title_en, plus_plan.description,
                            plus_plan.description_en))
        else:
            raise NoSuchPlusPlanException(plus_plan.id)
        connection.commit()
        cursor.close()
        connection.close()

    def update_payment(self, payment):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {self.TABLE_PAYMENTS} WHERE {self.PAYMENT_ORDER_ID}=? LIMIT 1",
                       (payment.order_id,))

        if cursor.fetchone():  # if account with his chat id has been saved before in the database
            columns = ', '.join(f"{field}=?" for field in self.PAYMENT_COLUMNS[2:])
            cursor.execute(f'UPDATE {self.TABLE_PAYMENTS} SET {columns} WHERE {self.PAYMENT_ORDER_ID}=?', \
                           (payment.id, payment.status, payment.amount, payment.currency, payment.paid_amount,
                            payment.paid_currency, payment.plus_plan.id, \
                            payment.created_at, payment.modified_at, payment.order_id))
            log(f"Payment with order_id of {payment.order_id}, and payment id of {payment.id} status changed to {payment.status}",
                category_name='payments')
        else:
            columns = ', '.join(self.PAYMENT_COLUMNS)
            cursor.execute(f"INSERT INTO {self.TABLE_PAYMENTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", \
                           (payment.order_id, payment.payer_chat_id, payment.id, payment.status, payment.amount,
                            payment.currency.upper(), \
                            payment.paid_amount, payment.paid_currency.upper(), payment.plus_plan.id,
                            payment.created_at, payment.modified_at))
            log(f"New payment with the id of {payment.id} and order_id of {payment.order_id}, and status of {payment.status} added for user with chatid =: {payment.payer_chat_id}",
                category_name='payments')
        connection.commit()
        cursor.close()
        connection.close()

    def get_payment(self, order_id):
        columns = ', '.join(self.PAYMENT_COLUMNS)
        return self.execute(True, f"SELECT {columns} from {self.TABLE_PAYMENTS} WHERE {self.PAYMENT_ORDER_ID}=? ",
                            order_id)

    def __init__(self, name="data.db"):
        self._name = name
        self.setup()
