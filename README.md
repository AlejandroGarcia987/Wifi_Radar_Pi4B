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

This is a **push-only** bot (no incoming commands). Therefore, Telegram Bot TOKEN and CHAT ID are required. 

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

### Current project status

At the time of writing, the project provides:

- A working WiFi-based motion detector
- A finite state machine with hysteresis to avoid false positives
- Telegram notifications with a complete motion lifecycle
- Secure handling of secrets via environment variables

The following features are **intentionally not implemented yet**:

- Docker-based deployment
- Automatic startup (systemd service)
- Remote arming / disarming
- Baseline auto-calibration

These features are planned as future improvements once the detection logic is considered stable.

---

## Example Telegram notifications

The following image shows a small demonstration of the notification flow during motion events.
The timestamps and variance values shown correspond to real motion events detected during testing.

<img width="500" height="700" alt="motion_detector_bot" src="https://github.com/user-attachments/assets/cd0689d0-a6b5-4809-af5c-9d6f1eafea36" />

