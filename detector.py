from ultralytics import YOLO
import cv2
import requests
import time

from geometry import calculate_angles
from camera_api import get_camera_by_id

# 🔥 Load model
model = YOLO("yolo26l.pt")

# APIs
MOVE_API = "http://localhost:8000/move_to"
ALERT_API = "http://localhost:9001/alert"

# Memory
locked_targets = {}
last_positions = {}
last_alert_time = {}

# Config
LOCK_TIMEOUT = 2
ALERT_COOLDOWN = 5

# Dangerous objects list (extend later)
DANGER_OBJECTS = ["knife", "scissors", "gun"]


# ---------------- PTZ CONTROL ----------------
def send_move(camera_id, x, y):
    try:
        requests.post(MOVE_API, json={
            "camera_id": camera_id,
            "target": {"x": float(x), "y": float(y), "z": 0}
        }, timeout=0.2)
    except:
        pass


# ---------------- ALERT SYSTEM ----------------
def send_alert(camera_id, frame):
    _, img_encoded = cv2.imencode('.jpg', frame)

    try:
        requests.post(
            ALERT_API,
            files={"file": ("alert.jpg", img_encoded.tobytes(), "image/jpeg")},
            data={"camera_id": camera_id},
            timeout=2
        )
    except Exception as e:
        print("ALERT ERROR:", e)


# ---------------- MAIN DETECTOR ----------------
def detect_objects(frame, camera_id=1):

    small = cv2.resize(frame, (640, 360))
    results = model(small, conf=0.3)

    detections = []

    h, w = frame.shape[:2]
    scale_x = w / 640
    scale_y = h / 360

    current_time = time.time()
    alert = False

    # ---------------- DETECTION ----------------
    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)

            cls = int(box.cls[0])
            label = model.names[cls]

            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2

            detections.append({
                "label": label,
                "bbox": [x1, y1, x2, y2],
                "center": [cx, cy]
            })

    # ---------------- CLASSIFY OBJECTS ----------------
    persons = []
    threats = []

    for d in detections:
        if d["label"] == "person":
            persons.append(d)

        if d["label"] in DANGER_OBJECTS:
            threats.append(d)

    # ---------------- PERSON TRACKING ----------------
    moving_person = None
    locked = locked_targets.get(camera_id)

    if persons:
        if locked:
            lx, ly = locked["center"]

            def dist(p):
                cx, cy = p["center"]
                return ((cx - lx)**2 + (cy - ly)**2) ** 0.5

            candidate = min(persons, key=dist)

            if dist(candidate) < 100:
                moving_person = candidate

        if moving_person is None:
            moving_person = max(
                persons,
                key=lambda p: (p["bbox"][2] - p["bbox"][0]) *
                              (p["bbox"][3] - p["bbox"][1])
            )

        locked_targets[camera_id] = {
            "center": moving_person["center"],
            "last_seen": current_time
        }

    else:
        if locked and current_time - locked["last_seen"] > LOCK_TIMEOUT:
            locked_targets.pop(camera_id, None)

    # ---------------- MOTION DETECTION ----------------
    if moving_person:
        cx, cy = moving_person["center"]

        prev = last_positions.get(camera_id)

        if prev:
            dx = abs(cx - prev[0])
            dy = abs(cy - prev[1])

            if dx > 5 or dy > 5:
                alert = True

        last_positions[camera_id] = (cx, cy)

        # ---------------- GEOMETRY ----------------
        cam = get_camera_by_id(camera_id)
        if cam:
            new_pan, new_tilt = calculate_angles(cx, cy, w, h, cam)
            print(f"🎯 Camera {camera_id} → PAN: {new_pan:.2f}, TILT: {new_tilt:.2f}")

    # ---------------- DRAWING ----------------
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        label = d["label"]

        color = (0, 255, 0)  # default green

        # Moving person
        if moving_person and d == moving_person:
            color = (0, 0, 255) if alert else (255, 0, 0)

        # Dangerous object
        if label in DANGER_OBJECTS:
            color = (0, 0, 255)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        cv2.putText(
            frame,
            label.upper(),
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )

    # ---------------- ALERT TEXT ----------------
    if alert:
        cv2.putText(
            frame,
            "🚨 PERSON MOVEMENT DETECTED",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

    if threats:
        cv2.putText(
            frame,
            "⚠️ DANGEROUS OBJECT DETECTED",
            (50, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 0, 255),
            3
        )

    # ---------------- ALERT TRIGGER ----------------
    last_time = last_alert_time.get(camera_id, 0)

    if (alert or threats) and (time.time() - last_time > ALERT_COOLDOWN):
        print("🚨 ALERT TRIGGERED")
        send_alert(camera_id, frame.copy())
        last_alert_time[camera_id] = time.time()

    return frame, detections, alert