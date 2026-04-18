from ultralytics import YOLO
model = YOLO("yolo26l.pt")

def detect_objects(frame):
    results = model(frame, conf=0.4)

    detections = []

    for r in results:
        for box in r.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            label = model.names[cls]

            detections.append({
                "label": label,
                "bbox": [x1, y1, x2, y2]
            })

    return detections