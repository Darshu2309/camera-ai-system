from ultralytics import YOLO
import cv2
import requests
import time
import threading

# 🔥 Load model
model = YOLO("yolo26l.pt")

# 🔧 APIs
MOVE_API = "http://localhost:8000/move_to"
ALERT_API = "http://localhost:9001/alert"

# 🔒 Memory
last_positions = {}
last_sent = 0
last_alert_time = {}

# ⏱ Config
ALERT_COOLDOWN = 5


# ---------------- PTZ CONTROL ----------------
def send_move(camera_id, x, y):
    global last_sent

    if time.time() - last_sent < 0.3:
        return

    last_sent = time.time()

    try:
        requests.post(MOVE_API, json={
            "camera_id": camera_id,
            "target": {"x": float(x), "y": float(y), "z": 0}
        }, timeout=0.2)
    except:
        pass


# ---------------- ALERT SYSTEM ----------------
def send_alert(camera_id, frame):
    def task():
        _, img_encoded = cv2.imencode('.jpg', frame)

        files = {
            'file': ('alert.jpg', img_encoded.tobytes(), 'image/jpeg')
        }

        data = {
            'camera_id': camera_id
        }

        try:
            requests.post(ALERT_API, files=files, data=data, timeout=10)
        except Exception as e:
            print("ALERT ERROR:", e)

    threading.Thread(target=task).start()


# ---------------- MAIN DETECTOR ----------------
def detect_objects(frame, camera_id=1):
    small = cv2.resize(frame, (640, 360))
    results = model(small, conf=0.3, imgsz=640)

    h, w = frame.shape[:2]
    sh, sw = small.shape[:2]

    scale_x = w / sw
    scale_y = h / sh

    timestamp = time.strftime("%d-%m-%Y %H:%M:%S")

    moving_objects = []
    alert = False
    person_count = 0

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

            # 🔑 Unique key for movement tracking
            key = f"{camera_id}_{label}_{cx//50}_{cy//50}"

            prev = last_positions.get(key)
            is_moving = False

            if prev:
                dx = abs(cx - prev[0])
                dy = abs(cy - prev[1])

                # 🔥 Movement sensitivity (tune here)
                if dx > 2 or dy > 2:
                    is_moving = True
            else:
                is_moving = True  # first time

            last_positions[key] = (cx, cy)

            if is_moving:
                moving_objects.append({
                    "label": label,
                    "bbox": [x1, y1, x2, y2],
                    "center": [cx, cy]
                })

    # ---------------- DRAW ONLY MOVING ----------------
    for obj in moving_objects:
        x1, y1, x2, y2 = obj["bbox"]
        label = obj["label"]
        cx, cy = obj["center"]

        if label == "person":
            person_count += 1

        # 🟩 Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # 🏷 Label
        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (0, 255, 0), 2)

        # 🎯 Center
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

    # ---------------- PERSON MOVEMENT ALERT ----------------
    moving_persons = [o for o in moving_objects if o["label"] == "person"]

    if moving_persons:
        best_person = moving_persons[0]
        cx, cy = best_person["center"]

        send_move(camera_id, cx, cy)
        alert = True

    # ---------------- ALERT TRIGGER ----------------
    last_time = last_alert_time.get(camera_id, 0)

    if alert and time.time() - last_time > ALERT_COOLDOWN:
        send_alert(camera_id, frame.copy())
        last_alert_time[camera_id] = time.time()

    # ---------------- UI ----------------

    # 👥 Person count
    cv2.putText(frame, f"Persons: {person_count}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0), 2)

    # 📅 Timestamp
    cv2.putText(frame, timestamp,
                (w - 280, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0), 2)

    # 🚨 Alert text
    if alert:
        cv2.putText(frame, "PERSON MOVEMENT DETECTED",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255), 2)

    return frame, moving_objects, alert