import re
from camera_selector import select_best_camera


def parse_command(text):
    text = text.lower()

    cam_match = re.search(r"camera\s*(\d+)", text)
    camera_id = int(cam_match.group(1)) if cam_match else None

    if "person" in text:
        target = "person"
    elif "chair" in text:
        target = "chair"
    elif "plant" in text:
        target = "plant"
    else:
        target = "any"

    return {
        "camera_id": camera_id,
        "target": target
    }


def execute_command(command, camera_streams, cameras=None, results=None, mode="auto"):
    cam_id = command["camera_id"]
    target_label = command["target"]

    if not camera_streams:
        return {"error": "No camera streams available"}

    if cam_id is None:
        return {"error": "No camera specified"}

    if cam_id not in camera_streams:
        return {"error": f"Camera {cam_id} not found"}

    if not results or cam_id not in results:
        return {"error": f"No AI results for camera {cam_id}"}

    detections = results[cam_id].get("objects", [])

    print(f"[COMMAND DEBUG] cam {cam_id} detections:", detections)

    target = None

    for det in detections:
        if det.get("label") == target_label:
            x1, y1, x2, y2 = det["bbox"]

            cx = int((x1 + x2) / 2)
            cy = int((y1 + y2) / 2)

            target = {
                "x": cx,
                "y": cy,
                "z": 0
            }
            break

    if not target:
        return {"error": f"No {target_label} detected in camera {cam_id}"}

    return {
        "status": "focused",
        "camera_id": cam_id,   # 🔥 FORCE SAME CAMERA
        "target": target_label,
        "target_coords": target,
        "mode": mode
    }