from subprocess import call
import time
from tools.manuwriter import log

print("Starting server ...")

while True:
    try:
        call(["python3", "online_pricer.py"])
    except Exception as ex:
        log("online_pricer.py crash:", ex, 'FATAL')
        print("Subprocess fucked; Restarting server ...")
    time.sleep(5)
