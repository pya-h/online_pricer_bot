import sqlite3
from datetime import datetime
from tools.manuwriter import log, prepare_folder, fwrite_from_scratch
from tools.mathematix import after_n_months
from time import time
from typing import List


class DatabaseInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    DATE_FORMAT = '%Y-%m-%d'
    BACKUP_FOLDER = 'db_backups'
    ACCOUNT_COLUMNS = (ACCOUNT_ID, ACCOUNT_CURRENCIES, ACCOUNT_CRYPTOS, ACCOUNT_CALC_CURRENCIES, ACCOUNT_CALC_CRYPTOS,
                       ACCOUNT_LAST_INTERACTION, ACCOUNT_PLUS_END_DATE, ACCOUNT_STATE, ACCOUNT_CACHE, ACCOUNT_IS_ADMIN, ACCOUNT_LANGUAGE) = \
        ('id', 'currencies', 'cryptos', 'calc_cryptos', 'calc_currencies', 'last_interaction', 'plus_end_date',
         'state', 'cache', 'admin', 'language')

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNELS_COLUMNS = (
        # TODO: Add cryptos/currencies list to this too. to choose what price data must be sent to channel
        CHANNEL_ID, CHANNEL_NAME, CHANNEL_TITLE, CHANNEL_OWNER_ID, CHANNEL_INTERVAL, CHANNEL_LAST_POST_TIME) = \
        ("id", "name", "title", "owner_id", "interval", "last_post_time")

    TABLE_PRICE_ALARMS = "alarms"
    PRICE_ALARMS_COLUMNS = (
        PRICE_ALARM_ID, PRICE_ALARM_TARGET_CHAT_ID, PRICE_ALARM_TARGET_CURRENCY, PRICE_ALARM_TARGET_PRICE,
        PRICE_ALARM_CHANGE_DIRECTION, PRICE_ALARM_PRICE_UNIT) = \
        ("id", "chat_id", "currency", "price", "change_dir", "unit")

    @staticmethod
    def Get():
        if not DatabaseInterface._instance:
            DatabaseInterface._instance = DatabaseInterface()
        return DatabaseInterface._instance

    def migrate(self):
        """This method is like a migration thing, after any major update, this must be called to perform any required structural change in db"""
        return
        # cursor.execute(f'ALTER TABLE {self.TABLE_ACCOUNTS} ADD {self.ACCOUNT_LAST_INTERACTION} DATE')
        # connection.commit()

    def setup(self):
        connection = None
        try:
            connection = sqlite3.connect(self._name, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = connection.cursor()

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_ACCOUNTS}'").fetchone():
                query = f"CREATE TABLE {self.TABLE_ACCOUNTS} ({self.ACCOUNT_ID} INTEGER PRIMARY KEY," + \
                        f"{self.ACCOUNT_CURRENCIES} TEXT, {self.ACCOUNT_CRYPTOS} TEXT, {self.ACCOUNT_CALC_CURRENCIES} TEXT, {self.ACCOUNT_CALC_CRYPTOS} TEXT," + \
                        f"{self.ACCOUNT_LAST_INTERACTION} DATE, {self.ACCOUNT_PLUS_END_DATE} DATE, {self.ACCOUNT_STATE} INTEGER DEFAULT 0, {self.ACCOUNT_CACHE} TEXT DEFAULT NULL, " + \
                        f"{self.ACCOUNT_IS_ADMIN} INTEGER DEFAULT 0, {self.ACCOUNT_LANGUAGE} TEXT)"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_ACCOUNTS} table created successfully.", category_name='plus_info')
            else:
                # write any migration needed in the function called below
                self.migrate()

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_CHANNELS}'").fetchone():
                query = f"CREATE TABLE {self.TABLE_CHANNELS} ({self.CHANNEL_ID} INTEGER PRIMARY KEY, " + \
                        f"{self.CHANNEL_INTERVAL} INTEGER NOT_NULL, {self.CHANNEL_LAST_POST_TIME} INTEGER, " + \
                        f"{self.CHANNEL_NAME} TEXT, {self.CHANNEL_TITLE} TEXT NOT_NULL," + \
                        f"{self.CHANNEL_OWNER_ID} INTEGER NOT_NULL, FOREIGN KEY({self.CHANNEL_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_CHANNELS} table created successfully.", category_name='plus_info')

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_PRICE_ALARMS}'").fetchone():
                query = f"CREATE TABLE {self.TABLE_PRICE_ALARMS} (" + \
                        f"{self.PRICE_ALARM_ID} INTEGER PRIMARY KEY AUTOINCREMENT, {self.PRICE_ALARM_TARGET_CHAT_ID} INTEGER NOT_NULL, " + \
                        f"{self.PRICE_ALARM_TARGET_PRICE} REAL NOT_NULL, {self.PRICE_ALARM_TARGET_CURRENCY} TEXT NOT_NULL, " + \
                        f"{self.PRICE_ALARM_CHANGE_DIRECTION} INTEGER, {self.PRICE_ALARM_PRICE_UNIT} TEXT NOT_NULL, " + \
                        f"FOREIGN KEY({self.PRICE_ALARM_TARGET_CHAT_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"

                cursor.execute(query)
                log(f"plus Database {self.TABLE_PRICE_ALARMS} table created successfully.", category_name='plus_info')

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
            query = f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            self.execute(False, query, account.chat_id, account.str_desired_currencies(), account.str_desired_cryptos(),
                         account.str_calc_currencies(), account.str_calc_cryptos(), account.last_interaction.strftime(self.DATE_FORMAT),
                         account.plus_end_date, account.state.value, account.cache_as_str(), account.is_admin, account.language)
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

    def get_special_accounts(self, property_field: str = ACCOUNT_IS_ADMIN, value: any = 1) -> list:
        return self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {property_field}=?", value)

    def update(self, account):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=? LIMIT 1", (account.chat_id,))
        if cursor.fetchone():  # if account with his chat id has been saved before in the database
            columns_to_set = ', '.join([f'{field}=?' for field in self.ACCOUNT_COLUMNS[1:]])

            cursor.execute(f'UPDATE {self.TABLE_ACCOUNTS} SET {columns_to_set} WHERE {self.ACCOUNT_ID}=?',
                           (account.str_desired_currencies(), account.str_desired_cryptos(),
                            account.str_calc_currencies(), account.str_calc_cryptos(), account.last_interaction.strftime(self.DATE_FORMAT),
                            account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None,
                            account.state.value, account.cache_as_str(), account.is_admin, account.language, account.chat_id))
        else:
            columns: str = ', '.join(self.ACCOUNT_COLUMNS)
            cursor.execute(f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (account.chat_id, account.str_desired_currencies(), account.str_desired_cryptos(),
                            account.str_calc_currencies(), account.str_calc_cryptos(), account.last_interaction.strftime(self.DATE_FORMAT),
                            account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None,
                            account.state.value, account.cache_as_str(), account.is_admin, account.language))
            log("New account started using this bot with chat_id=: " + account.__str__(), category_name=f'plus_info')
        connection.commit()
        cursor.close()
        connection.close()

    def upgrade_account(self, account, duration_in_months: int):  # use plus mode
        account.plus_end_date = after_n_months(duration_in_months)
        str_plus_end_date = account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None
        self.execute(False, f'UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_END_DATE}=? WHERE {self.ACCOUNT_ID}=?',
                     str_plus_end_date, account.chat_id)
        log(f"Account with chat_id={account.chat_id} has extended its plus pre-villages until {str_plus_end_date}")

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
            cursor.execute(f"INSERT INTO {self.TABLE_CHANNELS} ({columns}) VALUES (?, ?, ?, ?, ?, ?)",
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
        result = None
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(query, (*params,))
        if is_fetch_query:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid
            connection.commit()
        cursor.close()
        connection.close()
        return result

    def delete_channel(self, channel_id: int):
        """Delete channel and its planning"""
        self.execute(False, f"DELETE FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID} = ?", channel_id)

    def create_new_alarm(self, alarm):
        fields = ', '.join(
            self.PRICE_ALARMS_COLUMNS[1:])  # in creation mode admin just defines persian title and description
        # if he wants to add english texts, he should go to edit menu
        return self.execute(False, f"INSERT INTO {self.TABLE_PRICE_ALARMS} ({fields}) VALUES (?, ?, ?, ?, ?)",
                            alarm.chat_id, alarm.currency, alarm.target_price, alarm.change_direction.value,
                            alarm.target_unit)

    def get_single_alarm(self, id: int):
        return self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=?", id)

    def get_alarms(self, currency: str | None = None):
        return self.execute(True, f"SELECT * from {self.TABLE_PRICE_ALARMS}") if not currency else \
            self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CURRENCY}=?",
                         currency)  # TODO: does currency string needs '' ?

    def get_alarms_by_currencies(self, currencies: List[str]):
        targets = 'n'.join([f"'{curr}'" for curr in currencies])
        return self.execute(True,
                            f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CURRENCY} IN ({targets})")

    def delete_alarm(self, id: int):
        self.execute(False, f'DELETE FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=?', id)

    def get_table_columns(self, table: str):
        columns_info = self.execute(True, f'PRAGMA table_info({table});')
        column_names = [column[1] for column in columns_info]
        return column_names

    def backup(self, single_table_name: str = None, output_filename_suffix: str = 'backup'):
        tables = [single_table_name] if single_table_name else [self.TABLE_ACCOUNTS, self.TABLE_CHANNELS,
                                                                self.TABLE_PRICE_ALARMS]
        backup_folder_created, _ = prepare_folder(self.BACKUP_FOLDER)

        filename_prefix = f'./{self.BACKUP_FOLDER}/' if backup_folder_created else './'

        for table in tables:
            rows = self.execute(True, f'SELECT * FROM {table}')
            # add column names of a table as the first row
            rows.insert(0, self.get_table_columns(table))

            fwrite_from_scratch(f'{filename_prefix}{table}_{output_filename_suffix}.txt', "\n".join(rows))

    def __init__(self, name="data.db"):
        self._name = name
        self.setup()
