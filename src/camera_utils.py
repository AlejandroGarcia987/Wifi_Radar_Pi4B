# Capture camera utilities

import os
import time
import requests
from pathlib import Path

# Absolute path to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "data" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

CAMERA_URL = "http://192.168.10.100/capture"
MAX_IMAGES = 6 # Maximum number of images to keep
REQUEST_TIMEOUT = 5  # seconds

def capture_image():
    """
    Capture an image from the ESP32-CAM, store it locally and
    keep only the latest MAX_IMAGES files.
    Returns the path to the saved image or None on failure.
    """
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    image_path = IMAGE_DIR / f"capture_{timestamp}.jpg"

    try:
        response = requests.get(CAMERA_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        with open(image_path, "wb") as f:
            f.write(response.content)

    except Exception as e:
        print(f"Camera capture failed: {e}")
        return None

    _rotate_images()
    return image_path


def _rotate_images():
    images = sorted(IMAGE_DIR.glob("*.jpg"), key=os.path.getmtime)

    while len(images) > MAX_IMAGES:
        oldest = images.pop(0)
        try:
            oldest.unlink()
        except Exception:
            pass
