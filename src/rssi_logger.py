import subprocess
import time
from collections import deque
from datetime import datetime
import statistics
import os

IFACE = "wlan0"
INTERVAL = 0.1          # 10 Hz
WINDOW_SIZE = 30        # samples (~3 s)

DATA_DIR = "data"
CSV_FILE = os.path.join(DATA_DIR, "session_001.csv")

rssi_window = deque(maxlen=WINDOW_SIZE)

def get_rssi():
    try:
        result = subprocess.check_output(
            ["iw", "dev", IFACE, "link"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        for line in result.splitlines():
            if "signal:" in line:
                return int(line.split("signal:")[1].split(" ")[1])
    except Exception:
        return None

os.makedirs(DATA_DIR, exist_ok=True)

with open(CSV_FILE, "w") as f:
    f.write("timestamp,rssi,var\n")

print("Obtaining RSSI... Ctrl+C for finishing")

while True:
    rssi = get_rssi()
    ts = datetime.now().isoformat(timespec="milliseconds")

    if rssi is not None:
        rssi_window.append(rssi)

        if len(rssi_window) >= 5:
            var = statistics.pvariance(rssi_window)
        else:
            var = 0.0

        with open(CSV_FILE, "a") as f:
            f.write(f"{ts},{rssi},{var:.3f}\n")

        print(f"{ts} RSSI={rssi:4d} dBm  VAR={var:6.3f}")

    time.sleep(INTERVAL)