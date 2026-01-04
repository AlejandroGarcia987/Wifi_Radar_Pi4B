'''
Small sofware to test Telegram photo sending functionality.
'''

from camera_utils import capture_image
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
print("BOT_TOKEN repr:", repr(BOT_TOKEN))
print("CHAT_ID repr:", repr(CHAT_ID))


def send_photo(image_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as img:
        r = requests.post(
            url,
            files={"photo": img},
            data={"chat_id": CHAT_ID, "caption": "Test image"}
        )
    print("Status code:", r.status_code)
    print("Response:", r.text)

img = capture_image()
send_photo(img)
