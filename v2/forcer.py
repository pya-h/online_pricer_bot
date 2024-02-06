import subprocess
import time
import tools

print("Starting server ...")

while True:
    try:
        subprocess.call(["python3", "online_pricer.py"])
    except Exception as ex:
        tools.log("online_pricer.py crash:", ex)
        print("Subprocess fucked; Restarting server ...")
    time.sleep(5)