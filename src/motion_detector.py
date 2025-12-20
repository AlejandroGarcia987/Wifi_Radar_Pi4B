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

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("BOT_TOKEN loaded:", bool(TELEGRAM_BOT_TOKEN))
print("CHAT_ID loaded:", bool(TELEGRAM_CHAT_ID))
# ----------------------------------------

# ------- FSM states and RSSI Window -----
STATE_IDLE = 0
STATE_MOVING = 1
STATE_MOVING_CONFIRMED = 2

state = STATE_IDLE

rssi_window = deque(maxlen=WINDOW_SIZE)

t_start_motion = None
t_last_motion = None
# ----------------------------------------

# ------- Telegram control states -------- 
SYSTEM_DISARMED = 0
SYSTEM_ARMED = 1

system_state = SYSTEM_DISARMED
last_motion_ts = None

TELEGRAM_POLL_INTERVAL = 3  # seconds
last_update_id = None
last_poll_time = 0
# ----------------------------------------

def poll_telegram_commands():
    """Poll Telegram for new commands and update system state."""
    global system_state, last_update_id

    if not TELEGRAM_BOT_TOKEN:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    params = {"timeout": 1}

    if last_update_id is not None:
        params["offset"] = last_update_id + 1

    try:
        response = requests.get(url, params=params, timeout=5).json()
    except Exception:
        return

    if not response.get("ok"):
        return

    for update in response.get("result", []):
        last_update_id = update["update_id"]

        message = update.get("message")
        if not message:
            continue

        chat_id = message["chat"]["id"]
        text = message.get("text", "").strip().lower()

        # Ignore messages from unknown chats
        if str(chat_id) != str(TELEGRAM_CHAT_ID):
            continue

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if text == "/arm":
            system_state = SYSTEM_ARMED
            send_telegram(
                f"System armed\n{timestamp}"
            )

        elif text == "/disarm":
            system_state = SYSTEM_DISARMED
            send_telegram(
                f"System disarmed\n{timestamp}"
            )

        elif text == "/status":
            state_str = "ARMED" if system_state == SYSTEM_ARMED else "DISARMED"
            last_motion_str = (
                last_motion_ts if last_motion_ts else "No motion yet"
            )

            send_telegram(
                f"Status: {state_str}\n"
                f"Last motion: {last_motion_str}\n"
                f"{timestamp}"
            )


def send_telegram(message: str):
    """Send a message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
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
    now_time = time.time()
    # Poll Telegram commands at defined intervals
    if now_time - last_poll_time >= TELEGRAM_POLL_INTERVAL:
        poll_telegram_commands()
        last_poll_time = now_time
    # -------------------------------------
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
                last_motion_ts = timestamp

                if system_state == SYSTEM_ARMED:
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
                    if system_state == SYSTEM_ARMED:
                        send_telegram(
                            f"Motion still detected\n"
                            f"{timestamp}\n"
                            f"Variance: {var:.2f}"
                        )

            elif now - t_last_motion >= END_TIME:
                state = STATE_IDLE
                if system_state == SYSTEM_ARMED:
                    send_telegram(
                        f"No motion detected\n"
                        f"{timestamp}"
                    )

        elif state == STATE_MOVING_CONFIRMED:
            if var > VAR_LOW:
                t_last_motion = now

            elif now - t_last_motion >= END_TIME:
                state = STATE_IDLE
                if system_state == SYSTEM_ARMED:
                    send_telegram(
                        f"No motion detected\n"
                        f"{timestamp}"
                    )
        # -------------------------------------

        print(f"{timestamp} VAR={var:.2f} STATE={state}")

    time.sleep(INTERVAL)