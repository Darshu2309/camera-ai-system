from ultralytics import YOLO
import cv2
import requests
import time
import supervision as sv

# ---------------- MODEL ----------------
model = YOLO("yolo26l.pt")

# ---------------- GLOBAL ----------------
trackers = {}
last_positions = {}
last_alert_time = {}
last_detections_cache = {}

ALERT_API = "http://localhost:9001/alert"
ALERT_COOLDOWN = 3
MOVE_THRESHOLD = 5


# ---------------- TRACKER ----------------
def get_tracker(camera_id):
    if camera_id not in trackers:
        trackers[camera_id] = sv.ByteTrack()
    return trackers[camera_id]


# ---------------- ALERT ----------------
def send_alert(camera_id, frame):
    _, img = cv2.imencode(".jpg", frame)

    try:
        requests.post(
            ALERT_API,
            files={"file": ("alert.jpg", img.tobytes(), "image/jpeg")},
            data={"camera_id": camera_id},
            timeout=2
        )
    except Exception as e:
        print("ALERT ERROR:", e)


# ---------------- MAIN ----------------
def detect_objects(frame, camera_id):

    tracker = get_tracker(camera_id)

    results = model(frame, conf=0.3)[0]
    detections = sv.Detections.from_ultralytics(results)

    # CACHE (prevents flicker)
    if len(detections) > 0:
        last_detections_cache[camera_id] = detections
    else:
        detections = last_detections_cache.get(camera_id, detections)

    detections = tracker.update_with_detections(detections)

    moving_ids = set()

    # ---------------- MOVEMENT ----------------
    for i in range(len(detections)):
        x1, y1, x2, y2 = detections.xyxy[i]
        class_id = detections.class_id[i]
        tracker_id = detections.tracker_id[i]

        if tracker_id is None:
            continue

        label = model.names[class_id]

        if label != "person":
            continue

        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)

        key = (camera_id, tracker_id)
        prev = last_positions.get(key)

        if prev:
            dx = abs(cx - prev[0])
            dy = abs(cy - prev[1])

            if dx > MOVE_THRESHOLD or dy > MOVE_THRESHOLD:
                moving_ids.add(tracker_id)

        last_positions[key] = (cx, cy)

    # ---------------- DRAW ----------------
    for i in range(len(detections)):
        x1, y1, x2, y2 = map(int, detections.xyxy[i])
        class_id = detections.class_id[i]
        tracker_id = detections.tracker_id[i] or 0

        label = model.names[class_id]

        color = (0, 255, 0)
        text = label.upper()

        if label == "person":
            if tracker_id in moving_ids:
                color = (0, 0, 255)
                text = "PERSON MOVING"
            else:
                color = (0, 255, 0)
                text = "PERSON"

        # BOX
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

        # LABEL BACKGROUND
        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w + 10, y1), color, -1)

        # LABEL TEXT
        cv2.putText(frame, text, (x1 + 5, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2)

    # ---------------- ALERT ----------------
    alert = None

    if len(moving_ids) > 0:
        alert = "PERSON MOVEMENT DETECTED"

        cv2.putText(frame,
                    alert,
                    (30, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.2,
                    (0, 0, 255),
                    4)

        cv2.rectangle(frame,
                      (0, 0),
                      (frame.shape[1], frame.shape[0]),
                      (0, 0, 255),
                      5)

    # ---------------- SEND ALERT ----------------
    last_time = last_alert_time.get(camera_id, 0)

    if alert and time.time() - last_time > ALERT_COOLDOWN:
        print(f"🚨 ALERT Camera {camera_id}")
        send_alert(camera_id, frame.copy())
        last_alert_time[camera_id] = time.time()

    return frame, [], alert