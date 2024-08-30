import sqlite3
from datetime import datetime
from tools.manuwriter import log, prepare_folder, fwrite_from_scratch
from tools.mathematix import n_months_later
from time import time
from typing import List


class DatabaseInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    DATE_FORMAT = "%Y-%m-%d"
    BACKUP_FOLDER = "db_backups"
    ACCOUNT_COLUMNS = (
        ACCOUNT_ID,
        ACCOUNT_CURRENCIES,
        ACCOUNT_CRYPTOS,
        ACCOUNT_CALC_CURRENCIES,
        ACCOUNT_CALC_CRYPTOS,
        ACCOUNT_USERNAME,
        ACCOUNT_LAST_INTERACTION,
        ACCOUNT_PLUS_END_DATE,
        ACCOUNT_STATE,
        ACCOUNT_CACHE,
        ACCOUNT_IS_ADMIN,
        ACCOUNT_LANGUAGE,
    ) = (
        "id",
        "currencies",
        "cryptos",
        "calc_cryptos",
        "calc_currencies",
        "username",
        "last_interaction",
        "plus_end_date",
        "state",
        "cache",
        "admin",
        "language",
    )

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNELS_COLUMNS = (CHANNEL_ID, CHANNEL_NAME, CHANNEL_TITLE, CHANNEL_INTERVAL, CHANNEL_LAST_POST_TIME, CHANNEL_OWNER_ID) = (
        "id",
        "name",
        "title",
        "interval",
        "last_post_time",
        "owner_id",
    )

    TABLE_GROUPS = "groups"  # group to be scheduled
    GROUPS_COLUMNS = (
        GROUP_ID,
        GROUP_NAME,
        GROUP_TITLE,
        GROUP_COINS,
        GROUP_CURRENCIES,
        GROUP_MESSAGE_HEADER,
        GROUP_MESSAGE_FOOTNOTE,
        GROUP_MESSAGE_DATE_TAG,
        GROUP_MESSAGE_MARKET_TAGS,
        GROUP_OWNER_ID,
    ) = (
        "id",
        "name",
        "title",
        "coins",
        "currencies",
        "msg_header",
        "msg_footnote",
        "msg_date_tag",
        "msg_market_tags",
        "owner_id",
    )

    TABLE_PRICE_ALARMS = "alarms"
    PRICE_ALARMS_COLUMNS = (
        PRICE_ALARM_ID,
        PRICE_ALARM_TARGET_CHAT_ID,
        PRICE_ALARM_TARGET_CURRENCY,
        PRICE_ALARM_TARGET_PRICE,
        PRICE_ALARM_CHANGE_DIRECTION,
        PRICE_ALARM_PRICE_UNIT,
    ) = ("id", "chat_id", "currency", "price", "change_dir", "unit")

    @staticmethod
    def get():
        if not DatabaseInterface._instance:
            DatabaseInterface._instance = DatabaseInterface()
        return DatabaseInterface._instance

    @staticmethod
    def stringToList(string: str):
        """Use this method to extract saved currency or cryptocurrency list strings to List again."""
        if not string:
            return None
        string = string if string[-1] != ";" else string[:-1]
        return string.split(";")

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
                query = (
                    f"CREATE TABLE {self.TABLE_ACCOUNTS} ({self.ACCOUNT_ID} INTEGER PRIMARY KEY,"
                    + f"{self.ACCOUNT_CURRENCIES} TEXT, {self.ACCOUNT_CRYPTOS} TEXT, {self.ACCOUNT_CALC_CURRENCIES} TEXT, {self.ACCOUNT_CALC_CRYPTOS} TEXT, {self.ACCOUNT_USERNAME} TEXT, "
                    + f"{self.ACCOUNT_LAST_INTERACTION} DATE, {self.ACCOUNT_PLUS_END_DATE} DATE, {self.ACCOUNT_STATE} INTEGER DEFAULT 0, {self.ACCOUNT_CACHE} TEXT DEFAULT NULL, "
                    + f"{self.ACCOUNT_IS_ADMIN} INTEGER DEFAULT 0, {self.ACCOUNT_LANGUAGE} TEXT)"
                )
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_ACCOUNTS} table created successfully.", category_name="DatabaseInfo")
            else:
                # write any migration needed in the function called below
                self.migrate()

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_CHANNELS}'").fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_CHANNELS} ({self.CHANNEL_ID} INTEGER PRIMARY KEY, "
                    + f"{self.CHANNEL_NAME} TEXT, {self.CHANNEL_TITLE} TEXT NOT_NULL,"
                    + f"{self.CHANNEL_INTERVAL} INTEGER NOT_NULL, {self.CHANNEL_LAST_POST_TIME} INTEGER, "
                    + f"{self.CHANNEL_OWNER_ID} INTEGER NOT_NULL, FOREIGN KEY({self.CHANNEL_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"
                )
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_CHANNELS} table created successfully.", category_name="DatabaseInfo")

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_GROUPS}'").fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_GROUPS} ({self.GROUP_ID} INTEGER PRIMARY KEY, "
                    + f"{self.GROUP_NAME} TEXT, {self.GROUP_TITLE} TEXT NOT_NULL,"
                    + f"{self.GROUP_COINS} TEXT, {self.GROUP_CURRENCIES} TEXT, "
                    + f"{self.GROUP_MESSAGE_HEADER} TEXT, {self.GROUP_MESSAGE_FOOTNOTE} TEXT, "
                    + f"{self.GROUP_MESSAGE_DATE_TAG} INTEGER DEFAULT 0, {self.GROUP_MESSAGE_MARKET_TAGS} INTEGER DEFAULT 1, "
                    + f"{self.GROUP_OWNER_ID} INTEGER NOT_NULL, FOREIGN KEY({self.GROUP_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"
                )
                # create table account
                cursor.execute(query)
                log(f"PLUS Database {self.TABLE_CHANNELS} table created successfully.", category_name="DatabaseInfo")

            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{self.TABLE_PRICE_ALARMS}'").fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_PRICE_ALARMS} ("
                    + f"{self.PRICE_ALARM_ID} INTEGER PRIMARY KEY AUTOINCREMENT, {self.PRICE_ALARM_TARGET_CHAT_ID} INTEGER NOT_NULL, "
                    + f"{self.PRICE_ALARM_TARGET_PRICE} REAL NOT_NULL, {self.PRICE_ALARM_TARGET_CURRENCY} TEXT NOT_NULL, "
                    + f"{self.PRICE_ALARM_CHANGE_DIRECTION} INTEGER, {self.PRICE_ALARM_PRICE_UNIT} TEXT NOT_NULL, "
                    + f"FOREIGN KEY({self.PRICE_ALARM_TARGET_CHAT_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID}))"
                )

                cursor.execute(query)
                log(f"plus Database {self.TABLE_PRICE_ALARMS} table created successfully.", category_name="DatabaseInfo")

            log("plus Database setup completed.", category_name="DatabaseInfo")
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
            columns = ", ".join(self.ACCOUNT_COLUMNS)
            query = f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (?{', ?' * (len(self.ACCOUNT_COLUMNS) - 1)})"
            self.execute(
                False,
                query,
                account.chat_id,
                account.desired_currencies_as_str,
                account.desired_cryptos_as_str,
                account.calc_currencies_as_str,
                account.calc_cryptos_as_str,
                account.username,
                account.last_interaction.strftime(self.DATE_FORMAT),
                account.plus_end_date,
                account.state.value,
                account.scache_as_str,
                account.is_admin,
                account.language,
            )
            log(f"New account: {account} saved into database successfully.", category_name="DatabaseInfo")
        except Exception as ex:
            log(f"Cannot save this account:{account}", ex, category_name=f"DatabaseError")
            raise ex  # custom ex needed here too

    def get_account(self, chat_id):
        accounts = self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=? LIMIT 1", chat_id)
        return accounts[0] if accounts else None

    def get_all_accounts(self, column: str = ACCOUNT_ID) -> list:
        rows = self.execute(True, f"SELECT ({column}) FROM {self.TABLE_ACCOUNTS}")
        if column == self.ACCOUNT_LAST_INTERACTION:
            return [datetime.strptime(row[0], self.DATE_FORMAT) if row[0] else None for row in rows]
        return [row[0] for row in rows]  # just return a list of ids

    def get_special_accounts(self, property_field: str = ACCOUNT_IS_ADMIN, value: any = 1) -> list:
        return self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {property_field}=?", value)

    def get_premium_accounts(self, from_date: datetime | None = None) -> list:
        from_date: str = (from_date if from_date else datetime.now()).strftime(self.DATE_FORMAT)
        return self.execute(True, f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_PLUS_END_DATE} > ?", from_date)

    def update(self, account):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()

        columns_to_set = ", ".join([f"{field}=?" for field in self.ACCOUNT_COLUMNS[1:]])
        result = cursor.execute(
            f"UPDATE {self.TABLE_ACCOUNTS} SET {columns_to_set} WHERE {self.ACCOUNT_ID}=?",
            (
                account.desired_currencies_as_str,
                account.desired_cryptos_as_str,
                account.calc_currencies_as_str,
                account.calc_cryptos_as_str,
                account.username,
                account.last_interaction.strftime(self.DATE_FORMAT),
                account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None,
                account.state.value,
                account.scache_as_str,
                account.is_admin,
                account.language,
                account.chat_id,
            ),
        )

        if not result.rowcount:
            columns: str = ", ".join(self.ACCOUNT_COLUMNS)
            cursor.execute(
                f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (?{', ?' * (len(self.ACCOUNT_COLUMNS) - 1)})",
                (
                    account.chat_id,
                    account.desired_currencies_as_str,
                    account.desired_cryptos_as_str,
                    account.calc_currencies_as_str,
                    account.calc_cryptos_as_str,
                    account.username,
                    account.last_interaction.strftime(self.DATE_FORMAT),
                    account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None,
                    account.state.value,
                    account.scache_as_str,
                    account.is_admin,
                    account.language,
                ),
            )
            log("New account started using this bot with chat_id=: " + account.__str__(), category_name="DatabaseInfo")
        connection.commit()
        cursor.close()
        connection.close()

    def update_username(self, account):
        self.execute(
            False,
            f"UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_USERNAME}=? WHERE {self.ACCOUNT_ID}=?",
            account.username,
            account.chat_id,
        )

    def upgrade_account(self, account, duration_in_months: int):
        account.plus_end_date = n_months_later(duration_in_months)
        str_plus_end_date = account.plus_end_date.strftime(self.DATE_FORMAT) if account.plus_end_date else None
        self.execute(
            False,
            f"UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_END_DATE}=? WHERE {self.ACCOUNT_ID}=?",
            str_plus_end_date,
            account.chat_id,
        )
        log(f"Account with chat_id={account.chat_id} has extended its plus pre-villages until {str_plus_end_date}")

    def downgrade_account(self, account):
        self.execute(
            False,
            f"UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_END_DATE}=NULL WHERE {self.ACCOUNT_ID}=?",
            account.chat_id,
        )
        log(f"Account with chat_id={account.chat_id} downgraded to free user.")

    def plan_channel(self, owner_chat_id: int, channel_id: int, channel_name: str, interval: int, channel_title: str):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        now_in_minutes = time() // 60
        columns_to_set = ", ".join([f"{field}=?" for field in self.CHANNELS_COLUMNS[1:]])
        affected = cursor.execute(
            f"UPDATE {self.TABLE_CHANNELS} SET {columns_to_set} WHERE {self.CHANNEL_ID}=?",
            (channel_name, channel_title, owner_chat_id, interval, now_in_minutes, channel_id),
        )

        if affected.rowcount:
            log(
                f"Channel with the id of [{channel_id}, {channel_name}] has been RE-planned by owner_chat_id=: {owner_chat_id}",
                category_name="DatabaseInfo",
            )
        else:
            columns = ", ".join(self.CHANNELS_COLUMNS)
            cursor.execute(
                f"INSERT INTO {self.TABLE_CHANNELS} ({columns}) VALUES (?{', ?' * (len(self.CHANNELS_COLUMNS) - 1)})",
                (channel_id, channel_name, channel_title, owner_chat_id, interval, now_in_minutes),
            )
            log(
                f"New channel with the id of [{channel_id}, {channel_name}] has benn planned by owner_chat_id=: {owner_chat_id}",
                category_name="DatabaseInfo",
            )
        connection.commit()
        cursor.close()
        connection.close()

    def get_channel(self, channel_id: int):
        channels = self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID}=? LIMIT 1", channel_id)
        return channels[0] if channels else None

    def get_user_channels(self, owner_chat_id: int) -> list:
        """Get all channels related to this account"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_OWNER_ID}=?", owner_chat_id)

    def get_channels_by_interval(self, min_interval: int = 0) -> list:
        """Finds all the channels with plan interval > min_interval"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_INTERVAL} > ?", min_interval)

    def add_group(self, group):
        if not group:
            raise Exception("You must provide an Group to add")
        try:
            columns = ", ".join(self.GROUPS_COLUMNS)
            query = f"INSERT INTO {self.TABLE_GROUPS} ({columns}) VALUES (?{', ?' * (len(self.GROUPS_COLUMNS) - 1)})"
            self.execute(
                False,
                query,
                group.id,
                group.name,
                group.title,
                group.coins_as_str,
                group.currencies_as_str,
                group.message_header,
                group.message_footnote,
                int(group.message_show_date_tag),
                int(group.message_show_market_tags),
                group.owner_id,
            )
            log(f"New group: {group} saved into database successfully.", category_name="DatabaseInfo")
        except Exception as ex:
            log(f"Cannot save this group:{group}", ex, category_name="DatabaseError")
            raise ex  # custom ex needed here too

    def update_group(self, group):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()

        columns_to_set = ", ".join([f"{field}=?" for field in self.GROUPS_COLUMNS[1:]])

        affected_groups = cursor.execute(
            f"UPDATE {self.TABLE_GROUPS} SET {columns_to_set} WHERE {self.GROUP_ID}=?",
            (
                group.name,
                group.title,
                group.coins_as_str,
                group.currencies_as_str,
                group.message_header,
                group.message_footnote,
                int(group.message_show_date_tag),
                int(group.message_show_market_tags),
                group.owner_id,
                group.id,
            ),
        )

        if not affected_groups.rowcount:
            columns: str = ", ".join(self.GROUPS_COLUMNS)
            cursor.execute(
                f"INSERT INTO {self.TABLE_GROUPS} ({columns}) VALUES (?{', ?' * (len(self.GROUPS_COLUMNS) - 1)})",
                (
                    group.id,
                    group.name,
                    group.title,
                    group.coins_as_str,
                    group.currencies_as_str,
                    group.message_header,
                    group.last_interaction.strftime(self.DATE_FORMAT),
                    int(group.message_show_date_tag),
                    int(group.message_show_market_tags),
                    group.owner_id,
                ),
            )
            log("New group started using this bot with id=: " + group.__str__(), category_name="DatabaseInfo")
        connection.commit()
        cursor.close()
        connection.close()

    def get_group(self, group_id: int):
        groups = self.execute(True, f"SELECT * FROM {self.TABLE_GROUPS} WHERE {self.GROUP_ID}=? LIMIT 1", group_id)
        return groups[0] if groups else None

    def get_user_groups(self, owner_chat_id: int) -> list:
        """Get all groups/supergroups related to this account"""
        return self.execute(True, f"SELECT * FROM {self.TABLE_GROUPS} WHERE {self.GROUP_OWNER_ID}=?", owner_chat_id)

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
        fields = ", ".join(self.PRICE_ALARMS_COLUMNS[1:])  # in creation mode admin just defines persian title and description
        # if he wants to add english texts, he should go to edit menu
        return self.execute(
            False,
            f"INSERT INTO {self.TABLE_PRICE_ALARMS} ({fields}) VALUES (?{', ?' * (len(self.PRICE_ALARMS_COLUMNS) - 2)})",
            alarm.chat_id,
            alarm.currency,
            alarm.target_price,
            alarm.change_direction.value,
            alarm.target_unit,
        )

    def get_single_alarm(self, id: int):
        return self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=?", id)

    def get_alarms(self, currency: str | None = None):
        return (
            self.execute(True, f"SELECT * from {self.TABLE_PRICE_ALARMS}")
            if not currency
            else self.execute(
                True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CURRENCY}=?", currency
            )
        )

    def get_alarms_by_currencies(self, currencies: List[str]):
        targets = "n".join([f"'{curr}'" for curr in currencies])
        return self.execute(
            True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CURRENCY} IN ({targets})"
        )

    def get_user_alarms(self, chat_id: int):
        return self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CHAT_ID}={chat_id}")

    def get_number_of_user_alarms(self, chat_id: int) -> int:
        result = self.execute(
            True,
            f"SELECT COUNT({self.PRICE_ALARM_ID}) FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CHAT_ID}={chat_id}",
        )
        try:
            return result[0][0]
        except:
            pass
        return 0

    def delete_alarm(self, id: int):
        self.execute(False, f"DELETE FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=?", id)

    def get_table_columns(self, table: str):
        columns_info = self.execute(True, f"PRAGMA table_info({table});")
        column_names = [column[1] for column in columns_info]
        return column_names

    def backup(self, single_table_name: str = None, output_filename_suffix: str = "backup"):
        tables = (
            [single_table_name] if single_table_name else [self.TABLE_ACCOUNTS, self.TABLE_CHANNELS, self.TABLE_PRICE_ALARMS]
        )
        backup_folder_created, _ = prepare_folder(self.BACKUP_FOLDER)

        filename_prefix = f"./{self.BACKUP_FOLDER}/" if backup_folder_created else "./"

        for table in tables:
            rows = self.execute(True, f"SELECT * FROM {table}")
            # add column names of a table as the first row
            rows.insert(0, self.get_table_columns(table))

            fwrite_from_scratch(f"{filename_prefix}{table}_{output_filename_suffix}.txt", "\n".join(rows))

    def __init__(self, name="data.db"):
        self._name = name
        self.setup()
