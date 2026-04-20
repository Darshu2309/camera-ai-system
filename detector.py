from ultralytics import YOLO
import cv2
import requests
import time

model = YOLO("yolo26l.pt")

MOVE_API = "http://localhost:8000/move_to"

last_positions = {}
last_sent = 0


def send_move(camera_id, x, y):
    global last_sent

    # 🔥 limit PTZ spam (important)
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


def detect_objects(frame, camera_id=1):
    # 🔥 speed optimization
    small = cv2.resize(frame, (640, 360))
    results = model(small, conf=0.3, imgsz=640)

    detections = []

    h, w = frame.shape[:2]
    sh, sw = small.shape[:2]

    scale_x = w / sw
    scale_y = h / sh

    alert = False
    best_person = None
    max_area = 0

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # scale back
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

            # 🔥 choose BEST PERSON (largest)
            if label == "person":
                area = (x2 - x1) * (y2 - y1)
                if area > max_area:
                    max_area = area
                    best_person = (cx, cy)

    # 🚨 movement detection
    if best_person:
        prev = last_positions.get(camera_id)

        if prev:
            dx = abs(best_person[0] - prev[0])
            dy = abs(best_person[1] - prev[1])

            if dx > 2 or dy > 2:
                alert = True
            else:
                alert = False

        last_positions[camera_id] = best_person

        # 🎯 PTZ ONLY FOR BEST PERSON
        send_move(camera_id, best_person[0], best_person[1])

    return frame, detections, alert