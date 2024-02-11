import sqlite3
from datetime import datetime
from tools import manuwriter

class DatabaseInterface:
    _instance = None
    TABLE_ACCOUNTS = "accounts"
    ACCOUNT_ID = 'id'
    ACCOUNT_CURRENCIES = 'currencies'
    ACCOUNT_CRYPTOS = 'cryptos'
    ACCOUNT_LAST_INTERACTION = 'last_interaction'
    ACCOUNT_ALL_FIELDS = f'({ACCOUNT_ID}, {ACCOUNT_CURRENCIES}, {ACCOUNT_CRYPTOS}, {ACCOUNT_LAST_INTERACTION})'
    DATE_FORMAT = '%Y-%m-%d'
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
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{DatabaseInterface.TABLE_ACCOUNTS}'").fetchone():
                query = f"CREATE TABLE {DatabaseInterface.TABLE_ACCOUNTS} ({DatabaseInterface.ACCOUNT_ID} INTEGER PRIMARY KEY," +\
                    f"{DatabaseInterface.ACCOUNT_CURRENCIES} TEXT, {DatabaseInterface.ACCOUNT_CRYPTOS} TEXT, {DatabaseInterface.ACCOUNT_LAST_INTERACTION} DATE)"
                # create table account
                cursor.execute(query)
                manuwriter.log(f"{DatabaseInterface.TABLE_ACCOUNTS} table created successfuly.", category_name='info')

            # else: # TEMP-*****
            #     cursor.execute(f'ALTER TABLE {DatabaseInterface.TABLE_ACCOUNTS} ADD {DatabaseInterface.ACCOUNT_LAST_INTERACTION} DATE')
            #     connection.commit()
            manuwriter.log("Database setup completed.", category_name='info')
            cursor.close()
            connection.close()
        except Exception as ex:
            if connection:
                connection.close()
            raise ex  # create custom exception for this


    def add(self, account, log_category_prefix=''):
        connection = None
        if not account:
            raise Exception("You must provide an Account to save")
        try:
            query = f"INSERT INTO {DatabaseInterface.TABLE_ACCOUNTS} {DatabaseInterface.ACCOUNT_ALL_FIELDS} VALUES (?, ?, ?, ?)"
            connection = sqlite3.connect(self._name)
            cursor = connection.cursor()
            cursor.execute(query, (account.chat_id, account.str_desired_currencies(), account.str_desired_coins(), account.last_interaction.strftime(DatabaseInterface.DATE_FORMAT)))
            manuwriter.log(f"New account: {account} saved into database successfully.", category_name=f'{log_category_prefix}info')
            cursor.close()
            connection.commit()
            connection.close()
        except Exception as ex:
            manuwriter.log(f"Cannot save this account:{account}", ex, category_name=f'{log_category_prefix}database')
            if connection:
                connection.close()
            raise ex  # custom ex needed here too

    def get(self, chat_id):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {DatabaseInterface.TABLE_ACCOUNTS} WHERE {DatabaseInterface.ACCOUNT_ID}=? LIMIT 1", (chat_id, ))
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        return row

    def get_all(self, column: str=ACCOUNT_ID):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT ({column}) FROM {DatabaseInterface.TABLE_ACCOUNTS}")
        rows = cursor.fetchall()
        cursor.close()
        connection.close()
        if column == DatabaseInterface.ACCOUNT_LAST_INTERACTION:
            return [datetime.strptime(row[0], DatabaseInterface.DATE_FORMAT) if row[0] else None for row in rows]
        return [row[0] for row in rows] # just return a list of ids

    def update(self, account, log_category_prefix=''):
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

    def __init__(self, name="data.db"):
        self._name = name
        self.setup()
