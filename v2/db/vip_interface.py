from db.interface import DatabaseInterface
import sqlite3
from tools import manuwriter
from tools.mathematix import after_n_months

class VIPDatabaseInterface(DatabaseInterface):
    ACCOUNT_VIP_END_DATE= 'vip_end_date'  # verified as vip
    ACCOUNT_ALL_FIELDS = f'({DatabaseInterface.ACCOUNT_ID}, {DatabaseInterface.ACCOUNT_CURRENCIES}, {DatabaseInterface.ACCOUNT_CRYPTOS}, {DatabaseInterface.ACCOUNT_LAST_INTERACTION}, {ACCOUNT_VIP_END_DATE})'

    TABLE_CHANNELS = "channels"  # channels to be scheduled
    CHANNEL_ID = "id"
    CHANNEL_INTERVAL = "interval"
    CHANNEL_OWNER_ID = "owner_id"  # ref to account
    @staticmethod
    def Get():
        if not DatabaseInterface._instance:
            DatabaseInterface._instance = DatabaseInterface()
        return DatabaseInterface._instance

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
                query = f"CREATE TABLE {VIPDatabaseInterface.TABLE_ACCOUNTS} ({VIPDatabaseInterface.CHANNEL_ID} INTEGER PRIMARY KEY," +\
                    f"{VIPDatabaseInterface.CHANNEL_INTERVAL} INTEGER, {VIPDatabaseInterface.CHANNEL_OWNER_ID} INTEGER,  FOREIGN KEY({VIPDatabaseInterface.CHANNEL_OWNER_ID}) REFERENCES {VIPDatabaseInterface.TABLE_ACCOUNTS}({VIPDatabaseInterface.ACCOUNT_ID}))"
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

    def plan_channel(self, account, channel_id: int, interval: int):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {DatabaseInterface.TABLE_ACCOUNTS} WHERE {DatabaseInterface.ACCOUNT_ID}=? LIMIT 1", (account.chat_id, ))
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            FIELDS_TO_SET = f'{DatabaseInterface.ACCOUNT_CURRENCIES}=?, {DatabaseInterface.ACCOUNT_CRYPTOS}=?, {DatabaseInterface.ACCOUNT_LAST_INTERACTION}=?'
            cursor.execute(f'UPDATE {DatabaseInterface.TABLE_ACCOUNTS} SET {FIELDS_TO_SET} WHERE {DatabaseInterface.ACCOUNT_ID}=?', \
                (account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(DatabaseInterface.DATE_FORMAT) , account.chat_id))
        else:
            cursor.execute(f"INSERT INTO {DatabaseInterface.TABLE_ACCOUNTS} {DatabaseInterface.ACCOUNT_ALL_FIELDS} VALUES (?, ?, ?, ?)", \
                (account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(DatabaseInterface.DATE_FORMAT)))
            manuwriter.log("New account started using this bot with chat_id=: " + account.__str__(), category_name=f'{log_category_prefix}info')
        connection.commit()
        cursor.close()
        connection.close()


    def __init__(self, name="vip_data.db"):
        super().__init__(name)

