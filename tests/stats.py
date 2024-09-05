from db.interface import DatabaseInterface

db = DatabaseInterface.get()

r = db.get_user_stats()
print(r)