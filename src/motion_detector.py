import subprocess
import time
from collections import deque
from datetime import datetime
import statistics
import os

# ------------------ CONFIG ------------------
IFACE = "wlan0"
INTERVAL = 0.1            # 10 Hz
WINDOW_SIZE = 30          # ~3 s
VAR_HIGH = 0.85            # movement detected state
VAR_LOW = 0.55             # no movement detected state
COOLDOWN_SEC = 10         # time between events
# --------------------------------------------

DATA_DIR = "data"
EVENT_LOG = os.path.join(DATA_DIR, "motion_events.log")

STATE_QUIET = 0
STATE_MOVING = 1

state = STATE_QUIET
last_event_time = 0.0

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

print("Wifi motion sensor enabled (Ctrl+C to switch off)")

while True:
    rssi = get_rssi()
    now = time.time()

    if rssi is not None:
        rssi_window.append(rssi)

        if len(rssi_window) >= 5:
            var = statistics.pvariance(rssi_window)
        else:
            var = 0.0

        # ------------------ FSM ------------------
        if state == STATE_QUIET:
            if var > VAR_HIGH:
                if now - last_event_time > COOLDOWN_SEC:
                    ts = datetime.now().isoformat(timespec="seconds")
                    with open(EVENT_LOG, "a") as f:
                        f.write(f"{ts} MOVEMENT_DETECTED var={var:.2f}\n")

                    print(f"[{ts}] MOVEMENT_DETECTED (var={var:.2f})")
                    last_event_time = now

                state = STATE_MOVING

        elif state == STATE_MOVING:
            if var < VAR_LOW:
                state = STATE_QUIET
        # -----------------------------------------

        print(f"RSSI={rssi:4d} dBm  VAR={var:5.2f}  STATE={'MOV' if state else 'QUIET'}")

    time.sleep(INTERVAL)
