from db.interface import DatabaseInterface

from models.alarms import PriceAlarm

pa = PriceAlarm(12345, 'btc', 2000, 1, id=3)
pa.disable()
print([p.__str__() for p in PriceAlarm.Get(['btc'])])