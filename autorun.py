from subprocess import call
import time
from tools.manuwriter import log

print("Starting server ...")

while True:
    try:
        log("[Re]Started the bot server ...", category_name="info")
        call(["python3", "online_pricer_bot.py"])
    except Exception as ex:
        log("online_pricer_bot.py crash:", ex, "FATALITY")
        print("Subprocess fucked; Restarting server ...")
    time.sleep(5)
