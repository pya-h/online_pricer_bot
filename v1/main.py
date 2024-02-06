import subprocess
import time

while True:
    print("Restarting server ...")
    subprocess.call(["python3", "server.py"])
    time.sleep(5)
