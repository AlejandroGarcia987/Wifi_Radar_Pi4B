# WiFi Radar – Motion Detection with Raspberry Pi

Passive motion detection system based on WiFi signal dynamics, running on a Raspberry Pi.
The system detects **movement** (not static presence) by analyzing RSSI variance from a WiFi interface and sends structured notifications via Telegram.

This project does **not** require additional sensors, cameras, or router configuration changes.

---

## Project overview

The goal of this project is to explore whether meaningful motion detection can be achieved using only:

- A Raspberry Pi
- Its WiFi interface
- Statistical analysis of RSSI variations

The result is a lightweight, passive **WiFi-based motion detector** with:

- Real-time detection
- Noise rejection via hysteresis
- Event-based Telegram notifications
- No false positives during static presence

---

## How it works

### Key idea

WiFi signals are affected by **multipath propagation**.
When a person moves near the transmitter–receiver path, the signal paths change dynamically, causing measurable fluctuations in RSSI.

Important distinction:

- **Static presence** → RSSI stabilizes → low variance
- **Movement** → rapid multipath changes → high variance

This system detects **movement**, not people.

---

## Detection method

1. Periodically read RSSI from the WiFi interface (`iw dev wlan0 link`)
2. Maintain a sliding window of RSSI samples
3. Compute the **variance** of the window
4. Apply a finite state machine (FSM) with hysteresis

### Thresholds

- `VAR_HIGH`: transition to motion detected
- `VAR_LOW`: transition back to no motion

This avoids oscillations and false positives.

---

## State machine

The system operates as a three-state FSM:

- **IDLE**
  - No movement detected
- **MOVING**
  - Motion detected (initial trigger)
- **MOVING_CONFIRMED**
  - Sustained motion confirmed

### Timing logic

- Motion detected → immediate notification
- Motion persists for 5 seconds → “still detected” notification
- No motion for 20 seconds → “no motion detected” notification
- The cycle then resets

This design prevents notification spam and provides meaningful alerts.

---

## Telegram notifications

The system sends Telegram messages for:

- Motion detected
- Motion still detected
- No motion detected (end of cycle)

Each message includes:
- Timestamp
- RSSI variance value

### Telegram control commands

The bot initially started as a push-only notification mechanism for motion events.
Now it is possible to send several commands to get information about the status and arm/disarm the system as it follows:

- `/status`  
  Returns the current system state (ARMED / DISARMED) and the timestamp of the
  last detected motion event.

- `/arm`  
  Arms the detection system. Motion events will generate Telegram notifications
  and may trigger image capture when implemented.

- `/disarm`  
  Disarms the detection system. Motion is still internally detected, but no
  notifications or actions are triggered.

---

## Configuration

### Environment variables

Secrets are stored in a `.env` file (not tracked by git):

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

At the current stage, the system is intended to be executed **on a Raspberry Pi** with direct access to its WiFi interface.

The detector relies on native access to the WiFi stack (`iw dev wlan0 link`) and has been validated in a Raspberry Pi Linux environment.

---

## Execution model

The project is now **fully containerized using Docker**, allowing it to run as a background service without requiring an active terminal session.

The recommended execution model is:

- Run the detector inside a Docker container
- Use `docker-compose` to start and stop the service
- Provide configuration and secrets through environment variables (`.env`)
- Access logs using standard Docker tooling

This approach provides:
- Clean isolation of dependencies
- Easy start / stop control
- Reproducible deployment
- No impact on the host Python environment

The container is executed using **host networking** in order to access the WiFi interface directly.

---
## ESP32-CAM integration and network considerations (Work In Progress)

As an optional extension to the WiFi-based motion detector, an
event-driven image capture mechanism using an ESP32-CAM (AI Thinker, OV2640)
is currently being developed.

The firmware used is the standard **Arduino IDE** ESP32 example called
**CameraWebServer**, with minimal modifications that will be explained below.

The camera is not used for continuous monitoring. Instead, it acts as a
**reactive sensor**, triggered only when motion is detected by the WiFi RSSI
analysis running on the Raspberry Pi.

Although a vision-based motion detection system could be implemented,
the goal of this integration is to evaluate the viability and robustness
of combining WiFi-based detection with on-demand image capture.

### Network topology problem

In the current setup, the ESP32-CAM is connected to a 2.4 GHz WiFi repeater,
while the Raspberry Pi is connected to the main WiFi network.

For reasons that are not fully understood (likely related to hardware or
driver limitations), the ESP32-CAM fails to connect reliably to the main router.
This was verified through several configuration attempts.

Since this router is shared in a household environment, extensive changes
to its configuration were intentionally avoided.

As a consequence, the following issues arise:

- The Raspberry Pi cannot reliably access the ESP32-CAM HTTP endpoint (`/capture`)
- Connectivity depends on repeater-specific routing behavior
- The system becomes tightly coupled to the network topology

### Design decision: camera-initiated image push

To decouple the system from network constraints, the architecture was reversed:

- The ESP32-CAM actively pushes images to the Raspberry Pi
- The Raspberry Pi exposes a lightweight HTTP image receiver service
- Images are sent only when explicitly requested by the detector logic

This approach removes any dependency on:

- Direct Pi → camera connectivity
- Repeater routing behavior
- Static IP assumptions for the ESP32-CAM
  
### Implementation overview

- The Raspberry Pi runs a minimal HTTP server (`image_server.py`)
- The server listens for `POST /upload` requests
- Incoming JPEG frames are stored locally with timestamped filenames
- The ESP32-CAM sends the captured frame directly to the Pi after each capture

To support this approach, minor modifications were introduced in the
**CameraWebServer** firmware.

In **CameraWebServer.ino**, a new function was added:

```cpp
void sendImageToPi(camera_fb_t *fb) {
  if (!fb || fb->len == 0) return;

  HTTPClient http;
  WiFiClient client;

  // Raspberry Pi IP address and port
  const char *pi_url = "http://xxx.xxx.x.xx:xxxx/upload"; 
  // Port 8081 in my case, as defined in image_server.py

  http.begin(client, pi_url);
  http.addHeader("Content-Type", "image/jpeg");

  int httpResponseCode = http.POST(fb->buf, fb->len);

  Serial.print("POST image to Pi -> ");
  Serial.println(httpResponseCode);

  http.end();
}
```
This function is then invoked inside
static esp_err_t capture_handler(httpd_req_t *req)
in app_httpd.cpp, immediately after a successful frame capture:

```cpp
if (!fb) {
  log_e("Camera capture failed");
  httpd_resp_send_500(req);
  return ESP_FAIL;
}

sendImageToPi(fb); // Push image to Raspberry Pi

httpd_resp_set_type(req, "image/jpeg");
```
### Architectural advantages

This approach provides several benefits:

- Network-agnostic: works across subnets and repeaters
- Decoupled components: camera and detector are loosely coupled
- Event-driven: images are captured only when motion is detected
- Low bandwidth usage: no continuous streaming

As mentioned above, this feature is still a work in progress.
At this stage, the network limitations have been resolved and the initial
architecture for testing has been implemented.

The next step is to fully integrate this mechanism into the detector FSM
and align image capture with the motion detection lifecycle.

---

### Current project status

At the time of writing, the project provides:

- A working WiFi-based motion detector
- A finite state machine with hysteresis to avoid false positives
- Telegram notifications with a complete motion lifecycle
- Secure handling of secrets via environment variables
- An experimental event-driven image capture pipeline (ESP32-CAM → Raspberry Pi)

The following features are **currently implemented**:

- WiFi-based motion detection using RSSI variance
- Finite state machine with hysteresis to avoid false positives
- Telegram notifications covering the full motion lifecycle
- Secure handling of secrets via environment variables
- Docker-based deployment using docker-compose
- Background execution as a containerized service
- Push-based image upload from an ESP32-CAM to the Raspberry Pi (experimental)

The following features are **intentionally not implemented yet**:

- Baseline auto-calibration
- Full integration of image capture into the detector FSM
- Vision-based motion detection or image processing

These features are planned as future improvements once the detection logic and thresholds are considered stable.

---

## Containerized deployment

The detector can be started and stopped using Docker Compose:

```bash
docker compose up -d
docker compose down
```

Logs can be inspected using:
```bash
docker compose logs -f
```

## Example Telegram notifications

The following image shows a small demonstration of the notification flow during motion events.
The timestamps and variance values shown correspond to real motion events detected during testing.

<img width="500" height="700" alt="motion_detector_bot" src="https://github.com/user-attachments/assets/cd0689d0-a6b5-4809-af5c-9d6f1eafea36" />



