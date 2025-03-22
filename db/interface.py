from mysql.connector import Error, pooling
from datetime import datetime
from tools.manuwriter import log, prepare_folder, fwrite_from_scratch
from tools.mathematix import n_days_later, now_in_minute, tz_today
from typing import List, Tuple
from decouple import config
from enum import Enum
import json


class DatabaseInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    DATE_FORMAT = "%Y-%m-%d %H:%M"
    BACKUP_FOLDER = "db_backups"
    ACCOUNT_COLUMNS = (
        ACCOUNT_ID,
        ACCOUNT_CURRENCIES,
        ACCOUNT_CRYPTOS,
        ACCOUNT_CALC_CURRENCIES,
        ACCOUNT_CALC_CRYPTOS,
        ACCOUNT_USERNAME,
        ACCOUNT_FIRSTNAME,
        ACCOUNT_JOIN_DATE,
        ACCOUNT_LAST_INTERACTION,
        ACCOUNT_PLUS_START_DATE,
        ACCOUNT_PLUS_END_DATE,
        ACCOUNT_STATE,
        ACCOUNT_CACHE,
        ACCOUNT_MODE,
        ACCOUNT_LANGUAGE,
    ) = (
        "id",
        "currencies",
        "cryptos",
        "calc_currencies",
        "calc_cryptos",
        "username",
        "firstname",
        "join_date",
        "last_interaction",
        "plus_start_date",
        "plus_end_date",
        "state",
        "cache",
        "mode",
        "language",
    )

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNELS_COLUMNS = (
        CHANNEL_ID,
        CHANNEL_NAME,
        CHANNEL_TITLE,
        CHANNEL_INTERVAL,
        CHANNEL_IS_ACTIVE,
        CHANNEL_COINS,
        CHANNEL_CURRENCIES,
        CHANNEL_MESSAGE_HEADER,
        CHANNEL_MESSAGE_FOOTNOTE,
        CHANNEL_MESSAGE_SHOW_DATE_TAG,
        CHANNEL_MESSAGE_SHOW_MARKET_TAGS,
        CHANNEL_LANGUAGE,
        CHANNEL_LAST_POST_TIME,
        CHANNEL_OWNER_ID,
    ) = (
        "id",
        "name",
        "title",
        "post_interval",
        "is_active",
        "coins",
        "currencies",
        "msg_header",
        "msg_footnote",
        "msg_date_tag",
        "msg_market_tags",
        "language",
        "last_post_time",
        "owner_id",
    )

    TABLE_GROUPS = "supergroups"  # group to be scheduled
    GROUPS_COLUMNS = (
        GROUP_ID,
        GROUP_NAME,
        GROUP_TITLE,
        GROUP_COINS,
        GROUP_CURRENCIES,
        GROUP_MESSAGE_HEADER,
        GROUP_MESSAGE_FOOTNOTE,
        GROUP_MESSAGE_SHOW_DATE_TAG,
        GROUP_MESSAGE_SHOW_MARKET_TAGS,
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
        PRICE_ALARM_TARGET_TOKEN,
        PRICE_ALARM_TARGET_PRICE,
        PRICE_ALARM_MARKET,
        PRICE_ALARM_CHANGE_DIRECTION,
        PRICE_ALARM_PRICE_UNIT,
    ) = ("id", "chat_id", "token", "price", "token_market", "change_dir", "unit")

    TABLE_TRASH = "trash"
    TRASH_COLUMNS = (
        TRASH_ID,
        TRASH_TYPE,
        TRASH_OWNER_ID,
        TRASH_IDENTIFIER,
        TRASH_DELETE_AT,
        TRASH_DATA,
        TRASH_TRASHED_AT,
    ) = (
        "id",
        "type",
        "owner_id",
        "trash_ident",
        "delete_at",
        "data",
        "trashed_at",
    )

    class TrashType(Enum):
        CHANNEL = 1
        GROUP = 2
        ALARM = 3
        MESSAGE = 4
        USER = 5
        NONE = 0

        @staticmethod
        def which(value: int):
            try:
                return DatabaseInterface.TrashTypeOptions[value]
            except:
                pass
            return DatabaseInterface.TrashType.NONE

    TrashTypeOptions = (
        TrashType.NONE,
        TrashType.CHANNEL,
        TrashType.GROUP,
        TrashType.ALARM,
        TrashType.MESSAGE,
        TrashType.USER,
    )

    @staticmethod
    def get():
        if not DatabaseInterface._instance:
            DatabaseInterface._instance = DatabaseInterface()
        return DatabaseInterface._instance

    @staticmethod
    def stringToList(string: str) -> list:
        """Use this method to extract saved token list strings to List again."""
        if not string:
            return []
        string = string if string[-1] != ";" else string[:-1]
        return string.split(";")

    def migrate(self):
        """This method is like a migration thing, after any major update, this must be called to perform any required structural change in db"""
        return
        # cursor.execute(f'ALTER TABLE {self.TABLE_ACCOUNTS} ADD {self.ACCOUNT_LAST_INTERACTION} DATE')
        # connection.commit()

    def connection(self):
        return self.__connection_pool.get_connection()

    def execute(self, is_fetch_query: bool, query: str, *params):
        """Execute queries that doesn't return result such as insert or delete"""
        conn = self.connection()
        cursor = conn.cursor()
        cursor.execute(query, (*params,))
        if is_fetch_query:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid
            conn.commit()
        cursor.close()
        conn.close()

        return result

    def bulk_query(self, query: str, params: list | tuple):
        conn = self.connection()
        cursor = conn.cursor()
        res = cursor.executemany(query, params)
        conn.commit()
        cursor.close()
        conn.close()
        return res

    def setup(self):
        try:
            conn, cursor = self.set_timezone(close_connection=False)

            table_exist_query_start = (
                f"SELECT table_name from information_schema.tables WHERE table_schema = '{self.__name}' AND table_name"
            )
            tables_common_charset = "CHARACTER SET utf8mb4 COLLATE utf8mb4_persian_ci"
            # check if the table accounts was created
            cursor.execute(f"{table_exist_query_start}='{self.TABLE_ACCOUNTS}'")
            if not cursor.fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_ACCOUNTS} ({self.ACCOUNT_ID} BIGINT PRIMARY KEY,"
                    + f"{self.ACCOUNT_CURRENCIES} VARCHAR(1024), {self.ACCOUNT_CRYPTOS} VARCHAR(1024), {self.ACCOUNT_CALC_CURRENCIES} VARCHAR(1024), {self.ACCOUNT_CALC_CRYPTOS} VARCHAR(1024), {self.ACCOUNT_USERNAME} VARCHAR(32), {self.ACCOUNT_FIRSTNAME} VARCHAR(256) DEFAULT NULL,"
                    + f"{self.ACCOUNT_JOIN_DATE} DATETIME, {self.ACCOUNT_LAST_INTERACTION} DATETIME, {self.ACCOUNT_PLUS_START_DATE} DATETIME, {self.ACCOUNT_PLUS_END_DATE} DATETIME, {self.ACCOUNT_STATE} INTEGER DEFAULT 0, {self.ACCOUNT_CACHE} JSON DEFAULT NULL, "
                    + f"{self.ACCOUNT_MODE} TINYINT DEFAULT 0, {self.ACCOUNT_LANGUAGE} CHAR(2)) {tables_common_charset};"
                )
                # create table account
                cursor.execute(query)
                log(
                    f"Table {self.TABLE_ACCOUNTS} created successfully.",
                    category_name="DatabaseInfo",
                )

            cursor.execute(f"{table_exist_query_start}='{self.TABLE_CHANNELS}'")
            if not cursor.fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_CHANNELS} ({self.CHANNEL_ID} BIGINT PRIMARY KEY, "
                    + f"{self.CHANNEL_NAME} VARCHAR(32), {self.CHANNEL_TITLE} VARCHAR(256), {self.CHANNEL_INTERVAL} INTEGER NOT NULL,"
                    + f"{self.CHANNEL_IS_ACTIVE} TINYINT DEFAULT 0, {self.CHANNEL_COINS} VARCHAR(1024), {self.CHANNEL_CURRENCIES} VARCHAR(1024), "
                    + f"{self.CHANNEL_MESSAGE_HEADER} VARCHAR(256), {self.CHANNEL_MESSAGE_FOOTNOTE} VARCHAR(256), "
                    + f"{self.CHANNEL_MESSAGE_SHOW_DATE_TAG} BOOLEAN DEFAULT 0, {self.CHANNEL_MESSAGE_SHOW_MARKET_TAGS} BOOLEAN DEFAULT 1, "
                    + f"{self.CHANNEL_LANGUAGE} CHAR(2),{self.CHANNEL_LAST_POST_TIME} BIGINT DEFAULT NULL, "
                    + f"{self.CHANNEL_OWNER_ID} BIGINT NOT NULL, FOREIGN KEY({self.CHANNEL_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID})) {tables_common_charset};"
                )
                # create table account
                cursor.execute(query)
                log(
                    f"Table {self.TABLE_CHANNELS} created successfully.",
                    category_name="DatabaseInfo",
                )

            cursor.execute(f"{table_exist_query_start}='{self.TABLE_GROUPS}'")
            if not cursor.fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_GROUPS} ({self.GROUP_ID} BIGINT PRIMARY KEY, "
                    + f"{self.GROUP_NAME} VARCHAR(32), {self.GROUP_TITLE} VARCHAR(256),"
                    + f"{self.GROUP_COINS} VARCHAR(1024), {self.GROUP_CURRENCIES} VARCHAR(1024), "
                    + f"{self.GROUP_MESSAGE_HEADER} VARCHAR(256), {self.GROUP_MESSAGE_FOOTNOTE} VARCHAR(256), "
                    + f"{self.GROUP_MESSAGE_SHOW_DATE_TAG} BOOLEAN DEFAULT 0, {self.GROUP_MESSAGE_SHOW_MARKET_TAGS} BOOLEAN DEFAULT 1, "
                    + f"{self.GROUP_OWNER_ID} BIGINT NOT NULL, FOREIGN KEY({self.GROUP_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID})) {tables_common_charset};"
                )
                # create table account
                cursor.execute(query)
                log(
                    f"Table {self.TABLE_GROUPS} created successfully.",
                    category_name="DatabaseInfo",
                )

            cursor.execute(f"{table_exist_query_start}='{self.TABLE_PRICE_ALARMS}'")
            if not cursor.fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_PRICE_ALARMS} ("
                    + f"{self.PRICE_ALARM_ID} INTEGER PRIMARY KEY AUTO_INCREMENT, {self.PRICE_ALARM_TARGET_CHAT_ID} BIGINT NOT NULL, "
                    + f"{self.PRICE_ALARM_TARGET_TOKEN} VARCHAR(16) NOT NULL, {self.PRICE_ALARM_TARGET_PRICE} DOUBLE NOT NULL, "
                    + f"{self.PRICE_ALARM_MARKET} TINYINT(2), {self.PRICE_ALARM_CHANGE_DIRECTION} TINYINT(2), {self.PRICE_ALARM_PRICE_UNIT} CHAR(8) NOT NULL, "
                    + f"FOREIGN KEY({self.PRICE_ALARM_TARGET_CHAT_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID})) {tables_common_charset};"
                )

                cursor.execute(query)
                log(
                    f"Table {self.TABLE_PRICE_ALARMS} created successfully.",
                    category_name="DatabaseInfo",
                )

            cursor.execute(f"{table_exist_query_start}='{self.TABLE_TRASH}'")
            if not cursor.fetchone():
                query = (
                    f"CREATE TABLE {self.TABLE_TRASH} ("
                    + f"{self.TRASH_ID} INTEGER PRIMARY KEY AUTO_INCREMENT, {self.TRASH_TYPE} TINYINT NOT NULL, {self.TRASH_OWNER_ID} BIGINT NOT NULL, {self.TRASH_IDENTIFIER} BIGINT, {self.TRASH_DATA} JSON, "
                    + f"{self.TRASH_TRASHED_AT} DATETIME DEFAULT CURRENT_TIMESTAMP, {self.TRASH_DELETE_AT} BIGINT DEFAULT NULL, FOREIGN KEY({self.TRASH_OWNER_ID}) REFERENCES {self.TABLE_ACCOUNTS}({self.ACCOUNT_ID})) {tables_common_charset};"
                )

                cursor.execute(query)
                log(
                    f"Table {self.TABLE_TRASH} created successfully.",
                    category_name="DatabaseInfo",
                )

            log("OnlinePricer Database setup completed.", category_name="DatabaseInfo")

            cursor.close()
            conn.close()
        except Error as ex:
            log(
                "Failed setting up database, app cannot continue.",
                ex,
                category_name="FUX",
            )

    def add_account(self, account):
        if not account:
            raise Exception("You must provide an Account to save")
        try:
            columns = ", ".join(self.ACCOUNT_COLUMNS)
            query = (
                f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (%s{', %s' * (len(self.ACCOUNT_COLUMNS) - 1)})"
            )
            self.execute(
                False,
                query,
                account.chat_id,
                account.desired_currencies_as_str,
                account.desired_cryptos_as_str,
                account.calc_currencies_as_str,
                account.calc_cryptos_as_str,
                account.username,
                account.firstname,
                account.join_date or tz_today(),
                account.last_interaction,
                account.plus_start_date,
                account.plus_end_date,
                account.state.value,
                account.cache_as_str,
                account.mode.value,
                account.language,
            )
            log(
                f"New account: {account} saved into database successfully.",
                category_name="DatabaseInfo",
            )
        except Exception as ex:
            log(
                f"Cannot save this account:{account}",
                ex,
                category_name=f"DatabaseError",
            )
            raise ex  # custom ex needed here too

    def get_account(self, chat_id):
        accounts = self.execute(
            True,
            f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=%s LIMIT 1",
            chat_id,
        )
        return accounts[0] if accounts else None

    def get_all_accounts(self, by_column: str = ACCOUNT_ID) -> list:
        rows = self.execute(True, f"SELECT ({by_column}) FROM {self.TABLE_ACCOUNTS}")
        return [row[0] for row in rows]  # just return a list of ids

    def get_special_accounts(self, property_field: str = ACCOUNT_MODE, value: any = 1, limit: int | None = None) -> list:
        limit_exp = '' if not limit else f"LIMIT {limit}"
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {property_field}=%s {limit_exp}",
            value,
        )

    def get_premium_accounts(self, from_date: datetime | None = None) -> list:
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_PLUS_END_DATE} > %s",
            from_date or datetime.now(),
        )

    def get_possible_premium_accounts(self) -> list:
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL",
        )

    def update_account(self, account):
        conn = self.connection()
        cursor = conn.cursor()
        columns_to_set = ", ".join([f"{field}=%s" for field in self.ACCOUNT_COLUMNS[1:]])

        cursor.execute(
            f"UPDATE {self.TABLE_ACCOUNTS} SET {columns_to_set} WHERE {self.ACCOUNT_ID}=%s",
            (
                account.desired_currencies_as_str,
                account.desired_cryptos_as_str,
                account.calc_currencies_as_str,
                account.calc_cryptos_as_str,
                account.username,
                account.firstname,
                account.join_date,
                account.last_interaction,
                account.plus_start_date,
                account.plus_end_date,
                account.state.value,
                account.cache_as_str,
                account.mode.value,
                account.language,
                account.chat_id,
            ),
        )

        if not cursor.rowcount:
            cursor.execute(
                f"SELECT 1 FROM {self.TABLE_ACCOUNTS} WHERE {self.ACCOUNT_ID}=%s",
                (account.chat_id,),
            )
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return
            columns: str = ", ".join(self.ACCOUNT_COLUMNS)
            cursor.execute(
                f"INSERT INTO {self.TABLE_ACCOUNTS} ({columns}) VALUES (%s{', %s' * (len(self.ACCOUNT_COLUMNS) - 1)})",
                (
                    account.chat_id,
                    account.desired_currencies_as_str,
                    account.desired_cryptos_as_str,
                    account.calc_currencies_as_str,
                    account.calc_cryptos_as_str,
                    account.username,
                    account.firstname,
                    account.join_date,
                    account.last_interaction,
                    account.plus_start_date,
                    account.plus_end_date,
                    account.state.value,
                    account.cache_as_str,
                    account.mode.value,
                    account.language,
                ),
            )
        conn.commit()
        cursor.close()
        conn.close()

    def update_account_names(self, account):
        self.execute(
            False,
            f"UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_USERNAME}=%s, {self.ACCOUNT_FIRSTNAME}=%s WHERE {self.ACCOUNT_ID}=%s",
            account.username,
            account.firstname,
            account.chat_id,
        )

    def upgrade_account(self, account, duration_in_days: int):
        account.plus_start_date = tz_today()
        account.plus_end_date = n_days_later(duration_in_days)
        self.execute(
            False,
            f"UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_START_DATE}=%s, {self.ACCOUNT_PLUS_END_DATE}=%s WHERE {self.ACCOUNT_ID}=%s",
            account.plus_start_date,
            account.plus_end_date,
            account.chat_id,
        )
        log(f"Account with chat_id={account.chat_id} has extended its plus pre-villages until {account.plus_end_date}", category_name="VIP")

    def downgrade_account(self, account):
        account.plus_start_date = None
        account.plus_end_date = None
        self.execute(
            False,
            f"UPDATE {self.TABLE_ACCOUNTS} SET {self.ACCOUNT_PLUS_START_DATE}=NULL, {self.ACCOUNT_PLUS_END_DATE}=NULL WHERE {self.ACCOUNT_ID}=%s",
            account.chat_id,
        )
        log(
            f"Account with chat_id={account.chat_id} downgraded to free user.",
            category_name="Premiums",
        )

    def add_channel(self, channel):
        if not channel:
            raise Exception("You must provide an Group to add")
        try:
            columns = ", ".join(self.CHANNELS_COLUMNS)
            query = (
                f"INSERT INTO {self.TABLE_CHANNELS} ({columns}) VALUES (%s{', %s' * (len(self.CHANNELS_COLUMNS) - 1)})"
            )
            self.execute(
                False,
                query,
                channel.id,
                channel.name,
                channel.title,
                channel.interval,
                int(channel.is_active),
                channel.coins_as_str,
                channel.currencies_as_str,
                channel.message_header,
                channel.message_footnote,
                int(channel.message_show_date_tag),
                int(channel.message_show_market_tags),
                channel.owner.language,
                channel.last_post_time,
                channel.owner_id,
            )
            log(
                f"New channel: {channel} saved into database successfully.",
                category_name="DatabaseInfo",
            )
        except Exception as ex:
            log(f"Cannot save this channel:{channel}", ex, category_name="DatabaseError")
            raise ex  # custom ex needed here too

    def update_channel(self, channel, old_chat_id: int = None):
        channel_id = old_chat_id or channel.id
        conn = self.connection()
        cursor = conn.cursor()
        columns_to_set = ", ".join([f"{field}=%s" for field in self.CHANNELS_COLUMNS])
        cursor.execute(
            f"UPDATE {self.TABLE_CHANNELS} SET {columns_to_set} WHERE {self.CHANNEL_ID}=%s",
            (
                channel.id,
                channel.name,
                channel.title,
                channel.interval,
                int(channel.is_active),
                channel.coins_as_str,
                channel.currencies_as_str,
                channel.message_header,
                channel.message_footnote,
                int(channel.message_show_date_tag),
                int(channel.message_show_market_tags),
                channel.language,
                channel.last_post_time,
                channel.owner_id,
                channel_id,
            ),
        )

        if cursor.rowcount:
            log(
                f"Channel with the id of [{channel.id}, {channel.name}] has been RE-planned by: {channel.owner_id}",
                category_name="DatabaseInfo",
            )
        elif not old_chat_id:
            cursor.execute(
                f"SELECT 1 FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID}=%s",
                (channel.id,),
            )
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return
            columns = ", ".join(self.CHANNELS_COLUMNS)
            cursor.execute(
                f"INSERT INTO {self.TABLE_CHANNELS} ({columns}) VALUES (%s{', %s' * (len(self.CHANNELS_COLUMNS) - 1)})",
                (
                    channel.id,
                    channel.name,
                    channel.title,
                    channel.interval,
                    int(channel.is_active),
                    channel.coins_as_str,
                    channel.currencies_as_str,
                    channel.message_header,
                    channel.message_footnote,
                    int(channel.message_show_date_tag),
                    int(channel.message_show_market_tags),
                    channel.language,
                    channel.last_post_time,
                    channel.owner_id,
                ),
            )
            log(
                f"New channel with the id of [{channel.id}, {channel.name}] has been planned by: {channel.owner_id}",
                category_name="DatabaseInfo",
            )
        conn.commit()
        cursor.close()
        conn.close()

    def get_channel(self, channel_id: int):
        channels = self.execute(
            True,
            f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID}=%s LIMIT 1",
            channel_id,
        )
        return channels[0] if channels else None

    def get_user_channels(self, owner_chat_id: int, take: int | None = 1) -> list:
        """Get all channels owned by this account"""
        limitation = f"LIMIT {take}" if take else ""
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_OWNER_ID}=%s {limitation}",
            owner_chat_id,
        )

    def user_channels_count(self, owner_chat_id: int) -> int:
        """Get count of channels owned by this account"""
        result = self.execute(
            True,
            f"SELECT COUNT(id) as cnt FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_OWNER_ID}=%s",
            owner_chat_id,
        )
        count = result[0][0] if result and result[0] else 0
        return count

    def get_channels_by_interval(self, min_interval: int = 0) -> list:
        """Finds all the channels with plan interval > min_interval"""
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_INTERVAL} > %s",
            min_interval,
        )

    def get_all_channels(self) -> list:
        return self.execute(True, f"SELECT * FROM {self.TABLE_CHANNELS}")

    def get_all_active_channels(self) -> list:
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_IS_ACTIVE}=1 AND {self.CHANNEL_INTERVAL} > 0",
        )

    def set_channel_state(self, channel_id: int, is_active: bool = True):
        """Delete channel and its planning"""
        self.execute(
            False,
            f"UPDATE {self.TABLE_CHANNELS} SET {self.CHANNEL_IS_ACTIVE}=%s WHERE {self.CHANNEL_ID} = %s",
            int(is_active),
            channel_id,
        )

    def update_channels_last_post_times(self, id_list: List[int]):
        try:
            return self.execute(
                False,
                f"UPDATE {self.TABLE_CHANNELS} SET {self.CHANNEL_LAST_POST_TIME}=%s WHERE {self.CHANNEL_ID} IN ({','.join(['%s'] * len(id_list))})",
                now_in_minute(),
                *id_list,
            )
        except Exception:
            pass

    def update_user_channels_language(self, owner):
        return self.execute(
            False,
            f"UPDATE {self.TABLE_CHANNELS} SET {self.CHANNEL_LANGUAGE}=%s WHERE {self.CHANNEL_OWNER_ID}=%s",
            owner.language,
            owner.chat_id,
        )

    def delete_channel(self, channel_id: int):
        """Delete channel and its planning"""
        self.execute(
            False,
            f"DELETE FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_ID} = %s LIMIT 1",
            channel_id,
        )

    def add_group(self, group):
        if not group:
            raise Exception("You must provide an Group to add")
        try:
            columns = ", ".join(self.GROUPS_COLUMNS)
            query = f"INSERT INTO {self.TABLE_GROUPS} ({columns}) VALUES (%s{', %s' * (len(self.GROUPS_COLUMNS) - 1)})"
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
            log(
                f"New group: {group} saved into database successfully.",
                category_name="DatabaseInfo",
            )
        except Exception as ex:
            log(f"Cannot save this group:{group}", ex, category_name="DatabaseError")
            raise ex  # custom ex needed here too

    def update_group(self, group, old_chat_id: int = None):
        group_id = old_chat_id or group.id
        conn = self.connection()
        cursor = conn.cursor()

        columns_to_set = ", ".join([f"{field}=%s" for field in self.GROUPS_COLUMNS])

        cursor.execute(
            f"UPDATE {self.TABLE_GROUPS} SET {columns_to_set} WHERE {self.GROUP_ID}=%s",
            (
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
                group_id,
            ),
        )

        if not cursor.rowcount and not old_chat_id:
            cursor.execute(
                f"SELECT 1 FROM {self.TABLE_GROUPS} WHERE {self.GROUP_ID}=%s",
                (group.id,),
            )
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return
            columns: str = ", ".join(self.GROUPS_COLUMNS)
            cursor.execute(
                f"INSERT INTO {self.TABLE_GROUPS} ({columns}) VALUES (%s{', %s' * (len(self.GROUPS_COLUMNS) - 1)})",
                (
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
                ),
            )
            log(
                "New group started using this bot with id=: " + group.__str__(),
                category_name="DatabaseInfo",
            )
        conn.commit()
        cursor.close()
        conn.close()

    def get_group(self, group_id: int):
        groups = self.execute(
            True,
            f"SELECT * FROM {self.TABLE_GROUPS} WHERE {self.GROUP_ID}=%s LIMIT 1",
            group_id,
        )
        return groups[0] if groups else None

    def get_user_groups(self, owner_chat_id: int, take: int | None = 1) -> list:
        """Get all groups/supergroups owned by this account"""
        limitation = f"LIMIT {take}" if take else ""
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_GROUPS} WHERE {self.GROUP_OWNER_ID}=%s {limitation}",
            owner_chat_id,
        )

    def user_groups_count(self, owner_chat_id: int) -> int:
        """Get count of groups owned by this account"""
        result = self.execute(
            True,
            f"SELECT COUNT(id) as cnt FROM {self.TABLE_GROUPS} WHERE {self.GROUP_OWNER_ID}=%s",
            owner_chat_id,
        )
        count = result[0][0] if result and result[0] else 0
        return count

    def delete_group(self, group_id: int):
        """Delete group and its planning"""
        self.execute(
            False,
            f"DELETE FROM {self.TABLE_GROUPS} WHERE {self.GROUP_ID} = %s LIMIT 1",
            group_id,
        )

    def create_new_alarm(self, alarm):
        fields = ", ".join(
            self.PRICE_ALARMS_COLUMNS[1:]
        )  # in creation mode admin just defines persian title and description
        # if he wants to add english texts, he should go to edit menu
        return self.execute(
            False,
            f"INSERT INTO {self.TABLE_PRICE_ALARMS} ({fields}) VALUES (%s{', %s' * (len(self.PRICE_ALARMS_COLUMNS) - 2)})",
            alarm.chat_id,
            alarm.token,
            alarm.target_price,
            alarm.market.value,
            alarm.change_direction.value,
            alarm.target_unit,
        )

    def get_single_alarm(self, alarm_id: int):
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=%s",
            alarm_id,
        )

    def get_alarms(self, token: str | None = None, market: int | None = None):
        return (
            self.execute(True, f"SELECT * FROM {self.TABLE_PRICE_ALARMS}")
            if not token
            else self.execute(
                True,
                f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_TOKEN}=%s AND {self.PRICE_ALARM_MARKET}=%s",
                token,
                market,
            )
        )

    def get_alarms_by_tokens(self, tokens: List[str]):
        targets = "n".join([f"'{curr}'" for curr in tokens])
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_TOKEN} IN ({targets})",
        )

    def get_user_alarms(self, chat_id: int):
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_TARGET_CHAT_ID}={chat_id}",
        )

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

    def delete_alarm(self, alarm_id: int):
        self.execute(
            False,
            f"DELETE FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID}=%s LIMIT 1",
            alarm_id,
        )

    def batch_delete_alarms(self, id_list: List[int]):
        self.execute(
            False,
            f"DELETE FROM {self.TABLE_PRICE_ALARMS} WHERE {self.PRICE_ALARM_ID} IN ({','.join(['%s'] * len(id_list))})",
            *id_list,
        )

    def get_table_columns(self, table: str):
        columns_info = self.execute(True, f"PRAGMA table_info({table});")
        column_names = [column[1] for column in columns_info]
        return column_names

    def trash_sth(
        self,
        owner_id: int,
        trash_type: TrashType,
        trash_identifier: int,
        data: dict,
        delete_at: datetime | None = None,
    ):
        fields = ", ".join(
            self.TRASH_COLUMNS[1:-1]
        )  # in creation mode admin just defines persian title and description
        # if he wants to add english texts, he should go to edit menu

        # TODO: If there is a old trash from the same type and trash_ident, remove it
        return self.execute(
            False,
            f"INSERT INTO {self.TABLE_TRASH} ({fields}) VALUES (%s{', %s' * (len(self.TRASH_COLUMNS) - 3)})",
            trash_type.value,
            owner_id,
            trash_identifier,
            delete_at,
            json.dumps(data),
        )

    def get_trash(self, trash_id: int):
        rows = self.execute(
            True,
            f"SELECT * FROM {self.TABLE_TRASH} WHERE {self.TRASH_ID}=%s LIMIT 1",
            trash_id,
        )
        return rows[0] if rows else None

    def get_user_trash(self, owner_id: int):
        return self.execute(
            True,
            f"SELECT * FROM {self.TABLE_TRASH} WHERE {self.TRASH_OWNER_ID}=%s",
            owner_id,
        )

    def get_trash_by_identifier(self, trash_type: TrashType, identifier: int):
        rows = self.execute(
            True,
            f"SELECT * FROM {self.TABLE_TRASH} WHERE {self.TRASH_TYPE}=%s AND {self.TRASH_IDENTIFIER}=%s ORDER BY {self.TRASH_ID} DESC LIMIT 1",
            trash_type.value,
            identifier,
        )
        return rows[0] if rows else None

    def throw_trash_away(self, trash_id: int):
        return self.execute(
            False,
            f"DELETE FROM {self.TABLE_TRASH} WHERE {self.TRASH_ID}=%s LIMIT 1",
            trash_id,
        )

    def schedule_messages_for_removal(self, messages_data: List[Tuple[int, int, int, int]]):
        return self.bulk_query(
            f"INSERT INTO {self.TABLE_TRASH} ({self.TRASH_TYPE}, {self.TRASH_OWNER_ID}, {self.TRASH_IDENTIFIER}, {self.TRASH_DELETE_AT}) VALUES (%s, %s, %s, %s)",
            messages_data,
        )

    def get_messages_passed_their_due(self):
        return self.execute(
            True,
            f"SELECT ({self.TRASH_ID, self.TRASH_OWNER_ID, self.TRASH_IDENTIFIER}) FROM {self.TABLE_TRASH} WHERE {self.TRASH_TYPE}=%s AND {self.TRASH_DELETE_AT} >= %s",
            DatabaseInterface.TrashType.MESSAGE,
            now_in_minute(),
        )

    def throw_away_messages_passed_time(self, from_time: int):
        if not from_time:
            from_time = now_in_minute()
        return self.execute(
            False,
            f"DELETE FROM {self.TABLE_TRASH} WHERE {self.TRASH_TYPE}=%s AND {self.TRASH_DELETE_AT} >= %s",
            DatabaseInterface.TrashType.MESSAGE,
            from_time,
        )

    def count_query(self, table: str, where: str | None = None):
        res = self.execute(True, f"SELECT COUNT(*) FROM {table}" + f" WHERE {where}" if where else "")
        return res[0] if res else 0

    def set_timezone(
        self,
        tz: str = "+03:30",
        close_connection: bool = True,
        cursor_dictionary_param: bool = False,
    ):
        conn = self.connection()
        cursor = conn.cursor(dictionary=cursor_dictionary_param)
        cursor.execute(f"SET time_zone=%s;", (tz,))
        conn.commit()
        if close_connection:
            cursor.close()
            conn.close()
            return None
        return conn, cursor

    def get_user_stats(self):
        try:
            conn, cursor = self.set_timezone(close_connection=False, cursor_dictionary_param=True)
            cursor.execute(
                f"""SELECT 
                COUNT(*) as all_users,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NULL THEN 1 END) as free,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL THEN 1 END) as plus,

                COUNT(CASE WHEN DATE({self.ACCOUNT_JOIN_DATE})=DATE(NOW()) THEN 1 END) as all_join_today,
                COUNT(CASE WHEN DATE({self.ACCOUNT_JOIN_DATE}) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as all_join_yesterday,
                COUNT(CASE WHEN DATE({self.ACCOUNT_JOIN_DATE}) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as all_join_lastweek,
                COUNT(CASE WHEN DATE({self.ACCOUNT_JOIN_DATE}) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as all_join_lastmonth,

                COUNT(CASE WHEN DATE({self.ACCOUNT_PLUS_START_DATE})=DATE(NOW()) THEN 1 END) as plus_today,
                COUNT(CASE WHEN DATE({self.ACCOUNT_PLUS_START_DATE}) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as plus_yesterday,
                COUNT(CASE WHEN DATE({self.ACCOUNT_PLUS_START_DATE}) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as plus_lastweek,
                COUNT(CASE WHEN DATE({self.ACCOUNT_PLUS_START_DATE}) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as plus_lastmonth,
                
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NULL AND DATE(last_interaction)=DATE(NOW()) THEN 1 END) as free_int_today,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as free_int_yesterday,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as free_int_lastweek,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as free_int_lastmonth,
                
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL AND DATE(last_interaction)=DATE(NOW()) THEN 1 END) as plus_int_today,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 1 DAY AND DATE(NOW()) THEN 1 END) as plus_int_yesterday,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 7 DAY AND DATE(NOW()) THEN 1 END) as plus_int_lastweek,
                COUNT(CASE WHEN {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL AND DATE(last_interaction) BETWEEN DATE(NOW()) - INTERVAL 30 DAY AND DATE(NOW()) THEN 1 END) as plus_int_lastmonth
        FROM {self.TABLE_ACCOUNTS};"""
            )
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            return result[0] if result else None
        except:
            pass
        return None

    def get_active_channels_count(self):
        try:
            result = self.execute(
                True,
                f"SELECT COUNT(*) as all_channels FROM `{self.TABLE_CHANNELS}` WHERE {self.CHANNEL_IS_ACTIVE}=1;",
            )
            return result[0][0] if result and result[0] else 0
        except:
            pass
        return 0

    def get_all_groups_count(self):
        try:
            result = self.execute(True, f"SELECT COUNT(*) as all_groups FROM `{self.TABLE_GROUPS}`;")
            return result[0][0] if result and result[0] else 0
        except:
            pass
        return 0

    def get_premium_users_count(self):
        try:
            result = self.execute(
                True,
                f"SELECT COUNT(*) as premium_users FROM `{self.TABLE_ACCOUNTS}` WHERE {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL ;",
            )
            return result[0][0] if result and result[0] else 0
        except:
            pass
        return 0

    def select_accounts(self, limit: int = 20, offset: int = 0, only_premiums: bool = True):
        where: str = f"WHERE {self.ACCOUNT_PLUS_END_DATE} IS NOT NULL" if only_premiums else ""
        return self.execute(
            True,
            f"SELECT * FROM `{self.TABLE_ACCOUNTS}` {where} LIMIT {limit} OFFSET {offset}",
        )

    def select_groups_with_owner(self, limit: int = 10, offset: int = 0):
        return self.execute(
            True,
            f"SELECT * FROM `{self.TABLE_GROUPS}` JOIN {self.TABLE_ACCOUNTS} ON {self.TABLE_ACCOUNTS}.{self.ACCOUNT_ID} = {self.TABLE_GROUPS}.{self.GROUP_OWNER_ID} LIMIT {limit} OFFSET {offset}",
        )

    def select_active_channels_with_owner(self, limit: int = 10, offset: int = 0):
        return self.execute(
            True,
            f"SELECT * FROM `{self.TABLE_CHANNELS}` JOIN {self.TABLE_ACCOUNTS} ON {self.TABLE_ACCOUNTS}.{self.ACCOUNT_ID} = {self.TABLE_CHANNELS}.{self.CHANNEL_OWNER_ID} LIMIT {limit} OFFSET {offset}",
        )

    def delete_all_user_groups(self, user_id: int):
        """ *Warning: delete all groups owned by a user, all at once"""
        self.execute(
            False,
            f"DELETE FROM {self.TABLE_GROUPS} WHERE {self.GROUP_OWNER_ID} = %s",
            user_id,
        )
    
    def delete_all_user_channels(self, user_id: int):
        """*Warning: delete all channels owned by a user, all at once"""
        self.execute(
            False,
            f"DELETE FROM {self.TABLE_CHANNELS} WHERE {self.CHANNEL_OWNER_ID} = %s",
            user_id,
        )

    def backup(self, single_table_name: str = None, output_filename_suffix: str = "backup"):
        tables = (
            [single_table_name]
            if single_table_name
            else [self.TABLE_ACCOUNTS, self.TABLE_CHANNELS, self.TABLE_PRICE_ALARMS]
        )
        backup_folder_created = prepare_folder(self.BACKUP_FOLDER)

        filename_prefix = f"./{self.BACKUP_FOLDER}/" if backup_folder_created else "./"

        for table in tables:
            rows = self.execute(True, f"SELECT * FROM {table}")
            # add column names of a table as the first row
            rows.insert(0, self.get_table_columns(table))

            fwrite_from_scratch(
                f"{filename_prefix}{table}_{output_filename_suffix}.txt",
                "\n".join(rows),
            )

    def __init__(self, pool_size: int = 0, connection_timeout: int = 60):
        self.__host = config("DATABASE_HOST")
        self.__username = config("DATABASE_USERNAME")
        self.__password = config("DATABASE_PASSWORD")
        self.__name = config("DATABASE_NAME")
        self.__connection_pool = pooling.MySQLConnectionPool(
            pool_name="main_pool",
            pool_size=pool_size,
            pool_reset_session=True,
            connection_timeout=connection_timeout,
            host=self.__host,
            user=self.__username,
            password=self.__password,
            database=self.__name,
        )
        
        self.setup()
