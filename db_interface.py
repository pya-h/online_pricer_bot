import sqlite3
import tools

TABLE_ACCOUNTS = "accounts"  # T_ as in TABLE

class DatabaseInterface:
    _instance = None

    @staticmethod
    def Get():
        if not DatabaseInterface._instance:
            DatabaseInterface._instance = DatabaseInterface()
        return DatabaseInterface._instance

    def setup(self):
        connection = None
        try:
            connection = sqlite3.connect(self._name)
            cursor = connection.cursor()

            # check if the table accounts was created
            if not cursor.execute(f"SELECT name from sqlite_master WHERE name='{TABLE_ACCOUNTS}'").fetchone():
                query = f"CREATE TABLE {TABLE_ACCOUNTS} (id INTEGER PRIMARY KEY, currencies TEXT, cryptos TEXT)"

                # create table account
                cursor.execute(query)

                tools.log(f"{TABLE_ACCOUNTS} table created successfuly.")

            tools.log("Database setup completed.")
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
            query = f"INSERT INTO {TABLE_ACCOUNTS} (id, currencies, cryptos) VALUES (?, ?, ?)"
            connection = sqlite3.connect(self._name)
            cursor = connection.cursor()
            cursor.execute(query, (account.chat_id, account.str_desired_currencies(), account.str_desired_coins()))
            tools.log(f"New account: {account} saved into database successfully.")
            cursor.close()
            connection.commit()
            connection.close()
        except Exception as ex:
            tools.log(f"Cannot save this account:{account}", ex)
            if connection:
                connection.close()
            raise ex  # custom ex needed here too

    def get(self, chat_id):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {TABLE_ACCOUNTS} WHERE id=?", (chat_id, ))
        row = cursor.fetchone()
        cursor.close()
        connection.close()
        return row

    def update(self, account):
        connection = sqlite3.connect(self._name)
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM {TABLE_ACCOUNTS} WHERE id=?", (account.chat_id, ))
        if cursor.fetchone(): # if account with his chat id has been saved before in the database
            cursor.execute(f'UPDATE {TABLE_ACCOUNTS} SET currencies=?, cryptos=? WHERE id=?', \
                (account.str_desired_currencies(), account.str_desired_coins(), account.chat_id))
        else:
            cursor.execute(f"INSERT INTO {TABLE_ACCOUNTS} (id, currencies, cryptos) VALUES (?, ?, ?)", \
                (account.chat_id, account.str_desired_currencies(), account.str_desired_coins()))
            tools.log("New account started using this bot with chat_id=: " + account)
        connection.commit()
        cursor.close()
        connection.close()

    def __init__(self, name="data.db"):
        self._name = name
        self.setup()
