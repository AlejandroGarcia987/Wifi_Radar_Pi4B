import subprocess
import time
from collections import deque
from datetime import datetime
import statistics
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ---------------- CONFIG ----------------
IFACE = "wlan0"
INTERVAL = 0.1              # Sampling interval (s)
WINDOW_SIZE = 30            # Sliding window (~3 s)

VAR_HIGH = 0.85             # Threshold to detect motion
VAR_LOW = 0.55              # Threshold to return to no-motion

SUSTAIN_TIME = 5            # Seconds to confirm sustained motion
END_TIME = 20               # Seconds without motion to close cycle

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# ----------------------------------------

STATE_IDLE = 0
STATE_MOVING = 1
STATE_MOVING_CONFIRMED = 2

state = STATE_IDLE

rssi_window = deque(maxlen=WINDOW_SIZE)

t_start_motion = None
t_last_motion = None


def send_telegram(message: str):
    """Send a message via Telegram bot."""
    if not BOT_TOKEN or not CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        requests.post(url, data=payload, timeout=3)
    except Exception:
        pass


def get_rssi():
    """Read RSSI value from WiFi interface."""
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


print("WiFi motion detector with Telegram notifications started")

while True:
    rssi = get_rssi()
    now = time.time()

    if rssi is not None:
        rssi_window.append(rssi)

        if len(rssi_window) >= 5:
            var = statistics.pvariance(rssi_window)
        else:
            var = 0.0

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ---------------- FSM ----------------
        if state == STATE_IDLE:
            if var > VAR_HIGH:
                state = STATE_MOVING
                t_start_motion = now
                t_last_motion = now

                send_telegram(
                    f"Motion detected!\n"
                    f"{timestamp}\n"
                    f"Variance: {var:.2f}"
                )

        elif state == STATE_MOVING:
            if var > VAR_LOW:
                t_last_motion = now

                if now - t_start_motion >= SUSTAIN_TIME:
                    state = STATE_MOVING_CONFIRMED
                    send_telegram(
                        f"Motion still detected\n"
                        f"{timestamp}\n"
                        f"Variance: {var:.2f}"
                    )

            elif now - t_last_motion >= END_TIME:
                state = STATE_IDLE
                send_telegram(
                    f"No motion detected\n"
                    f"{timestamp}"
                )

        elif state == STATE_MOVING_CONFIRMED:
            if var > VAR_LOW:
                t_last_motion = now

            elif now - t_last_motion >= END_TIME:
                state = STATE_IDLE
                send_telegram(
                    f"No motion detected\n"
                    f"{timestamp}"
                )
        # -------------------------------------

        print(f"{timestamp} VAR={var:.2f} STATE={state}")

    time.sleep(INTERVAL)