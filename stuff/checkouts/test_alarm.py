from db.interface import DatabaseInterface

db = DatabaseInterface.get()

print(db.get_number_of_user_alarms(1)[0])
from models.alarms import PriceAlarm

pa = PriceAlarm(12345, "btc", 2000, 1, id=3)
pa.disable()
print([p.__str__() for p in PriceAlarm.get(["btc"])])
