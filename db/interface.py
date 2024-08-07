import mysql.connector
from mysql.connector import Error, MySQLConnection
from datetime import datetime
from tools.manuwriter import log, prepare_folder, fwrite_from_scratch
from tools.mathematix import after_n_months
from time import time
from typing import List
from decouple import config


class DatabaseInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    DATE_FORMAT = '%Y-%m-%d %H:%M'
    BACKUP_FOLDER = 'db_backups'
    ACCOUNT_COLUMNS = (ACCOUNT_ID, ACCOUNT_CURRENCIES, ACCOUNT_CRYPTOS, ACCOUNT_CALC_CURRENCIES, ACCOUNT_CALC_CRYPTOS, ACCOUNT_USERNAME,
                       ACCOUNT_LAST_INTERACTION, ACCOUNT_PLUS_END_DATE, ACCOUNT_STATE, ACCOUNT_CACHE, ACCOUNT_IS_ADMIN, ACCOUNT_LANGUAGE) = \
        ('id', 'currencies', 'cryptos', 'calc_cryptos', 'calc_currencies', 'username', 'last_interaction', 'plus_end_date',
         'state', 'cache', 'admin', 'language')

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNELS_COLUMNS = (CHANNEL_ID, CHANNEL_NAME, CHANNEL_TITLE, CHANNEL_INTERVAL, CHANNEL_LAST_POST_TIME, CHANNEL_OWNER_ID) = \
        ("id", "name", "title", "post_interval", "last_post_time", "owner_id")
    
    TABLE_GROUPS = "supergroups"  # group to be scheduled
    GROUPS_COLUMNS = (GROUP_ID, GROUP_NAME, GROUP_TITLE, GROUP_COINS, GROUP_CURRENCIES, GROUP_MESSAGE_HEADER, GROUP_MESSAGE_FOOTNOTE, GROUP_MESSAGE_SHOW_DATE, GROUP_MESSAGE_SHOW_MARKET_LABELS, GROUP_OWNER_ID) = \
        ("id", "name", "title", "coins", "currencies", "msg_header", "msg_footnote", "msg_show_date", "msg_show_market_labels", "owner_id")

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

    @staticmethod
    def StringToList(string: str):
        '''Use this method to extract saved currency or cryptocurrency list strings to List again.'''
        if not string:
            return None
        string = string if string[-1] != ";" else string[:-1]
        return string.split(';')
    
    def migrate(self):
        """This method is like a migration thing, after any major update, this must be called to perform any required structural change in db"""
        return
        # cursor.execute(f'ALTER TABLE {self.TABLE_ACCOUNTS} ADD {self.ACCOUNT_LAST_INTERACTION} DATE')
        # connection.commit()

    def connect(self):
        self.__connection_instance = mysql.connector.connect(
            host=self.__host,
            user=self.__username,
            password=self.__password,
            database=self.__name,
        )

    @property
    def connection(self):
        if not self.__connection_instance or not self.__connection_instance.is_connected:
            self.connect()
            
        return self.__connection_instance
    
    def setup(self):
        try:
            cursor = self.connection.cursor()
            # check if the table accounts was created
            cursor.execute(f"SELECT table_name from information_schema.tables WHERE table_schema = '{self.__name}' and table_name='{self.TABLE_ACCOUNTS}'")
            if not cursor.fetchone():
                query = f"CREATE TABLE {self.TABLE_ACCOUNTS} ({self.ACCOUNT_ID} BIGINT PRIMARY KEY," + \
                        f"{self.ACCOUNT_CURRENCIES} VARCHAR(1024), {self.ACCOUNT_CRYPTOS} VARCHAR(1024), {self.ACCOUNT_CALC_CURRENCIES} VARCHAR(1024), {self.ACCOUNT_CALC_CRYPTOS} VARCHAR(1024), {self.ACCOUNT_USERNAME} VARCHAR(32), " + \
                        f"{self.ACCOUNT_LAST_INTERACTION} DATETIME, {self.ACCOUNT_PLUS_END_DATE} DATETIME, {self.ACCOUNT_STATE} INTEGER DEFAULT 0, {self.ACCOUNT_CACHE} VARCHAR(256) DEFAULT NULL, " + \
                        f"{self.ACCOUNT_IS_ADMIN} BOOLEAN DEFAULT 0, {self.ACCOUNT_LANGUAGE} CHAR(2))"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_ACCOUNTS} table created successfully.", category_name='DatabaseInfo')
            else:
                # write any migration needed in the function called below
                self.migrate()

            cursor.execute(f"SELECT table_name from information_schema.tables WHERE table_schema = '{self.__name}' and table_name='{self.TABLE_CHANNELS}'")
            if not cursor.fetchone():
                query = f"CREATE TABLE {self.TABLE_CHANNELS} ({self.CHANNEL_ID} BIGINT PRIMARY KEY, " + \
                        f"{self.CHANNEL_NAME} VARCHAR(32), {self.CHANNEL_TITLE} VARCHAR(128) NOT NULL," + \
                        f"{self.CHANNEL_INTERVAL} INTEGER NOT NULL, {self.CHANNEL_LAST_POST_TIME} INTEGER, " + \
                        f"{self.CHANNEL_OWNER_ID} BIGINT NOT NULL, FOREIGN KEY({self.CHANNEL_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_CHANNELS} table created successfully.", category_name='DatabaseInfo')

            cursor.execute(f"SELECT table_name from information_schema.tables WHERE table_schema = '{self.__name}' and table_name='{self.TABLE_GROUPS}'")
            if not cursor.fetchone():
                query = f"CREATE TABLE {self.TABLE_GROUPS} ({self.GROUP_ID} BIGINT PRIMARY KEY, " + \
                        f"{self.GROUP_NAME} VARCHAR(32), {self.GROUP_TITLE} VARCHAR(128) NOT NULL," + \
                        f"{self.GROUP_COINS} VARCHAR(1024), {self.GROUP_CURRENCIES} VARCHAR(1024), " + \
                        f"{self.GROUP_MESSAGE_HEADER} VARCHAR(256), {self.GROUP_MESSAGE_FOOTNOTE} VARCHAR(256), " + \
                        f"{self.GROUP_MESSAGE_SHOW_DATE} BOOLEAN DEFAULT 0, {self.GROUP_MESSAGE_SHOW_MARKET_LABELS} BOOLEAN DEFAULT 1, " + \
                        f"{self.GROUP_OWNER_ID} BIGINT NOT NULL, FOREIGN KEY({self.GROUP_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_CHANNELS} table created successfully.", category_name='DatabaseInfo')

            cursor.execute(f"SELECT table_name from information_schema.tables WHERE table_schema = '{self.__name}' and table_name='{self.TABLE_PRICE_ALARMS}'")
            if not cursor.fetchone():
                query = f"CREATE TABLE {self.TABLE_PRICE_ALARMS} (" + \
                        f"{self.PRICE_ALARM_ID} INTEGER PRIMARY KEY AUTO_INCREMENT, {self.PRICE_ALARM_TARGET_CHAT_ID} BIGINT NOT NULL, " + \
                        f"{self.PRICE_ALARM_TARGET_PRICE} DOUBLE NOT NULL, {self.PRICE_ALARM_TARGET_CURRENCY} VARCHAR(16) NOT NULL, " + \
                        f"{self.PRICE_ALARM_CHANGE_DIRECTION} TINYINT(2), {self.PRICE_ALARM_PRICE_UNIT} VARCHAR(16) NOT NULL, " + \
                        f"FOREIGN KEY({self.PRICE_ALARM_TARGET_CHAT_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"

                cursor.execute(query)
                log(f"plus Database {self.TABLE_PRICE_ALARMS} table created successfully.", category_name='DatabaseInfo')

            log("plus Database setup completed.", category_name='DatabaseInfo')
            cursor.close()
        except Error as ex:
            log('Failed setting up database, app cannot continue...', ex, category_name='FUX')

    def add(self, account):
        if not account:
            raise Exception("You must provide an Account to save")
        try:
            columns = ', '.join(self.ACCOUNT_COLUMNS)
            query = f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (%s{', %s' * (len(self.ACCOUNT_COLUMNS) - 1)})"
            self.execute(False, query, account.chat_id, account.desired_currencies_as_str, account.desired_cryptos_as_str,
                         account.calc_currencies_as_str, account.calc_cryptos_as_str, account.username, account.last_interaction,
                         account.plus_end_date, account.state.value, account.cache_as_str(), account.is_admin, account.language)
            log(f"New account: {account} saved into database successfully.", category_name='DatabaseInfo')
        except Exception as ex:
            log(f"Cannot save this account:{account}", ex, category_name=f'DatabaseError')
            raise ex  # custom ex needed here too

    def get(self, chat_id):
        accounts = self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=%s LIMIT 1", chat_id)
        return accounts[0] if accounts else None

    def get_all(self, column: str = ACCOUNT_ID) -> list:
        rows = self.execute(True, f"SELECT ({column}) FROM {self.TABLE_ACCOUNTS}")
        return [row[0] for row in rows]  # just return a list of ids

    def get_special_accounts(self, property_field: str = ACCOUNT_IS_ADMIN, value: any = 1) -> list:
        return self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {property_field}=%s", value)

    def get_premium_accounts(self, from_date: datetime | None = None) -> list:
        from_date = from_date or datetime.now()
        return self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_PLUS_END_DATE} > %s", from_date)

    def update(self, account):
        cursor = self.connection.cursor()

        columns_to_set = ', '.join([f'{field}=%s' for field in self.ACCOUNT_COLUMNS[1:]])
        cursor.execute(f'UPDATE {self.TABLE_ACCOUNTS} SET {columns_to_set} WHERE {self.ACCOUNT_ID}=%s',
                        (account.desired_currencies_as_str, account.desired_cryptos_as_str,
                        account.calc_currencies_as_str, account.calc_cryptos_as_str, account.username,
                        account.last_interaction, account.plus_end_date,
                        account.state.value, account.cache_as_str(), account.is_admin, account.language, account.chat_id))

        if not cursor.rowcount:
            cursor.execute(f'SELECT 1 FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=%s', (account.chat_id, ))
            if cursor.fetchone():  # Id exists but no update happened.
                cursor.close()
                return
            columns: str = ', '.join(self.ACCOUNT_COLUMNS)
            cursor.execute(f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (%s{', %s' * (len(self.ACCOUNT_COLUMNS) - 1)})",
                           (account.chat_id, account.desired_currencies_as_str, account.desired_cryptos_as_str,
                            account.calc_currencies_as_str, account.calc_cryptos_as_str, account.username, account.last_interaction,
                            account.plus_end_date, account.state.value, account.cache_as_str(), account.is_admin, account.language))
            log("New account started using this bot with chat_id=: " + account.__str__(), category_name='DatabaseInfo')
        self.connection.commit()
        cursor.close()

    def update_username(self, account):
        self.execute(False, f'UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_USERNAME}=%s WHERE {self.ACCOUNT_ID}=%s',
                     account.username, account.chat_id)

    def upgrade_account(self, account, duration_in_months: int):
        account.plus_end_date = after_n_months(duration_in_months)
        self.execute(False, f'UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_END_DATE}=%s WHERE {self.ACCOUNT_ID}=%s',
                     account.plus_end_date, account.chat_id)
        log(f"Account with chat_id={account.chat_id} has extended its plus pre-villages until {account.plus_end_date}")

    def downgrade_account(self, account):
        self.execute(False, f'UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_END_DATE}=NULL WHERE {self.ACCOUNT_ID}=%s', account.chat_id)
        log(f"Account with chat_id={account.chat_id} downgraded to free user.")

    def plan_channel(self, owner_chat_id: int, channel_id: int, channel_name: str, interval: int, channel_title: str):
        cursor = self.connection.cursor()
        now_in_minutes = time() // 60
        columns_to_set = ', '.join([f'{field}=%s' for field in self.CHANNELS_COLUMNS[1:]])
        cursor.execute(f'UPDATE {self.TABLE_CHANNELS} SET {columns_to_set} WHERE {self.CHANNEL_ID}=%s', \
                        (channel_name, channel_title, owner_chat_id, interval, now_in_minutes, channel_id))
        
        if cursor.rowcount:
            log(f"Channel with the id of [{channel_id}, {channel_name}] has been RE-planned by owner_chat_id=: {owner_chat_id}",
                        category_name='DatabaseInfo')
        else:
            cursor.execute(f'SELECT 1 FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID}=%s', (channel_id, ))
            if cursor.fetchone():  # Id exists but no update happened.
                cursor.close()
                return
            columns = ', '.join(self.CHANNELS_COLUMNS)
            cursor.execute(f"INSERT INTO {self.TABLE_CHANNELS} ({columns}) VALUES (%s{', %s' * (len(self.CHANNELS_COLUMNS) - 1)})",
                           (channel_id, channel_name, channel_title, owner_chat_id, interval, now_in_minutes))
            log(f"New channel with the id of [{channel_id}, {channel_name}] has benn planned by owner_chat_id=: {owner_chat_id}",
                category_name='DatabaseInfo')
        self.connection.commit()
        cursor.close()

    def get_channel(self, channel_id: int):
        channels = self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID}=%s LIMIT 1",
                                channel_id)
        return channels[0] if channels else None

    def get_user_channels(self, owner_chat_id: int) -> list:
        """Get all channels related to this account"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_OWNER_ID}=%s", owner_chat_id)

    def get_channels_by_interval(self, min_interval: int = 0) -> list:
        """Finds all the channels with plan interval > min_interval"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_INTERVAL} > ?",
                            min_interval)

    def add_group(self, group):
        if not group:
            raise Exception("You must provide an Group to add")
        try:
            columns = ', '.join(self.GROUPS_COLUMNS)
            query = f"INSERT INTO {self.TABLE_GROUPS} ({columns}) VALUES (%s{', %s' * (len(self.GROUPS_COLUMNS) - 1)})"
            self.execute(False, query, group.id, group.name, group.title, group.coins_as_str, group.currencies_as_str,
                        group.message_header, group.message_footer, int(group.message_show_date), int(group.message_show_market_labels), group.owner_id)
            log(f"New group: {group} saved into database successfully.", category_name='DatabaseInfo')
        except Exception as ex:
            log(f"Cannot save this group:{group}", ex, category_name='DatabaseError')
            raise ex  # custom ex needed here too


    def update_group(self, group):
        cursor = self.connection.cursor()

        columns_to_set = ', '.join([f'{field}=%s' for field in self.GROUPS_COLUMNS[1:]])

        cursor.execute(f'UPDATE {self.TABLE_GROUPS} SET {columns_to_set} WHERE {self.GROUP_ID}=%s',
                        (group.name, group.title, group.coins_as_str, group.currencies_as_str, group.message_header,
                        group.message_footer, int(group.message_show_date),
                        int(group.message_show_market_labels), group.owner_id, group.id))

        if not cursor.rowcount:
            cursor.execute(f'SELECT 1 FROM {self.TABLE_GROUPS} WHERE {self.GROUP_ID}=%s', (group.id, ))
            if cursor.fetchone():  # Id exists but no update happened.
                cursor.close()
                return
            columns: str = ', '.join(self.GROUPS_COLUMNS)
            cursor.execute(f"INSERT INTO {self.TABLE_GROUPS} ({columns}) VALUES (%s{', %s' * (len(self.GROUPS_COLUMNS) - 1)})",
                           (group.id, group.name, group.title, group.coins_as_str, group.currencies_as_str,
                            group.message_header, group.message_footer, int(group.message_show_date), int(group.message_show_market_labels), group.owner_id))
            log("New group started using this bot with id=: " + group.__str__(), category_name='DatabaseInfo')
        self.connection.commit()
        cursor.close()

    def get_group(self, group_id: int):
        groups = self.execute(True, f"SELECT * FROM {self.TABLE_GROUPS} WHERE {self.GROUP_ID}=%s LIMIT 1",
                                group_id)
        return groups[0] if groups else None

    def get_user_groups(self, owner_chat_id: int) -> list:
        """Get all groups/supergroups related to this account"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_GROUPS} WHERE {self.GROUP_OWNER_ID}=%s", owner_chat_id)

    def execute(self, is_fetch_query: bool, query: str, *params):
        """Execute queries that doesnt return result such as insert or delete"""
        result = None
        cursor = self.connection.cursor()
        cursor.execute(query, (*params,))
        if is_fetch_query:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid
            self.connection.commit()
        cursor.close()
        return result

    def delete_channel(self, channel_id: int):
        """Delete channel and its planning"""
        self.execute(False, f"DELETE FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID} = ?", channel_id)

    def create_new_alarm(self, alarm):
        fields = ', '.join(
            self.PRICE_ALARMS_COLUMNS[1:])  # in creation mode admin just defines persian title and description
        # if he wants to add english texts, he should go to edit menu
        return self.execute(False, f"INSERT INTO {self.TABLE_PRICE_ALARMS} ({fields}) VALUES (%s{', %s' * (len(self.PRICE_ALARMS_COLUMNS) - 2)})",
                            alarm.chat_id, alarm.currency, alarm.target_price, alarm.change_direction.value,
                            alarm.target_unit)

    def get_single_alarm(self, id: int):
        return self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=%s", id)

    def get_alarms(self, currency: str | None = None):
        return self.execute(True, f"SELECT * from {self.TABLE_PRICE_ALARMS}") if not currency else \
            self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CURRENCY}=%s", currency)

    def get_alarms_by_currencies(self, currencies: List[str]):
        targets = 'n'.join([f"'{curr}'" for curr in currencies])
        return self.execute(True,
                            f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CURRENCY} IN ({targets})")

    def get_user_alarms(self, chat_id: int):
        return self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CHAT_ID}={chat_id}")

    def get_number_of_user_alarms(self, chat_id: int) -> int:
        result = self.execute(True, f"SELECT COUNT({self.PRICE_ALARM_ID}) FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CHAT_ID}={chat_id}")
        try:
            return result[0][0]
        except:
            pass
        return 0

    def delete_alarm(self, id: int):
        self.execute(False, f'DELETE FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=%s', id)

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

    def __init__(self):
        self.__host = config('DATABASE_HOST', 'localhost')
        self.__username = config('DATABASE_USERNAME', 'root')
        self.__password = config('DATABASE_PASSWORD', '')
        self.__name = config('DATABASE_NAME', 'database')
        self.__connection_instance: MySQLConnection = None
        self.setup()
