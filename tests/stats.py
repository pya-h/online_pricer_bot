from db.interface import DatabaseInterface

db = DatabaseInterface.get()

r = db.get_account_stats()
print(r)