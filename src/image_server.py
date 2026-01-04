from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = PROJECT_ROOT / "data" / "images"
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

HOST = "0.0.0.0"
PORT = 8081

class ImageHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/upload":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        image_data = self.rfile.read(content_length)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        image_path = IMAGE_DIR / f"esp32_{timestamp}.jpg"

        with open(image_path, "wb") as f:
            f.write(image_data)

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

        print(f"[IMG] Saved {image_path.name}")

def run():
    server = HTTPServer((HOST, PORT), ImageHandler)
    print(f"Image server listening on {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run()
