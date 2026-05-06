import math
import time
import threading
import requests
from camera_health import camera_health, HEALTH_TIMEOUT
last_point_time = {}
POINT_COOLDOWN = 2.0

# -------------------------------
# BASIC GEOMETRY FUNCTIONS
# -------------------------------

def calculate_distance(cam_pos, target):
    dx = target["x"] - cam_pos.get("x", 0)
    dy = target["y"] - cam_pos.get("y", 0)
    return math.sqrt(dx * dx + dy * dy)


def calculate_angle(cam_pos, target):
    dx = target["x"] - cam_pos.get("x", 0)
    dy = target["y"] - cam_pos.get("y", 0)
    return math.degrees(math.atan2(dy, dx))


def angle_difference(a1, a2):
    diff = abs(a1 - a2) % 360
    return min(diff, 360 - diff)


# -------------------------------
# FOV CHECK (SAFE)
# -------------------------------

def is_in_fov(camera, target_angle):
    orientation = camera.get("orientation", {})
    cam_pan = orientation.get("pan", 0)

    # default full visibility
    fov = camera.get("fov", 360)

    diff = angle_difference(cam_pan, target_angle)
    return diff <= (fov / 2)


def initialize_camera_orientations(cameras):
    center = {"x": 10, "y": 7.5}

    for cam in cameras:
        pos = cam.get("position", {"x": 0, "y": 0})

        dx = center["x"] - pos["x"]
        dy = center["y"] - pos["y"]

        angle = math.degrees(math.atan2(dy, dx)) % 360

        cam["orientation"] = {
            "pan": angle,
            "tilt": 0,
            "zoom": 1
        }

        cam["fov"] = cam.get("fov", 90)

        print(f"[INIT] Camera {cam['id']} → pan={round(angle,2)}°")


# -------------------------------
# HEALTH CHECK FUNCTION
# -------------------------------

def is_camera_active(cam_id):
    health = camera_health.get(cam_id)

    if not health:
        return False

    last_seen = health.get("last_seen", 0)

    if time.time() - last_seen > HEALTH_TIMEOUT:
        return False

    return True

def safe_point_call(cam_id, payload):
    global last_point_time

    now = time.time()

    if cam_id not in last_point_time:
        last_point_time[cam_id] = 0

    # ⛔ COOLDOWN CHECK
    if now - last_point_time[cam_id] < POINT_COOLDOWN:
        return

    last_point_time[cam_id] = now

    # 🚀 BACKGROUND THREAD (NON-BLOCKING)
    def call():
        try:
            requests.post(
                "http://127.0.0.1:8000/point",
                json=payload,
                timeout=1
            )
        except Exception as e:
            print("[POINT ERROR]", e)

    threading.Thread(target=call, daemon=True).start()


# -------------------------------
# MAIN CAMERA SELECTION LOGIC
# -------------------------------

def select_best_camera(cameras, target):
    best_camera = None
    best_score = float("inf")

    for cam in cameras:

        cam_id = cam["id"]

        # 🔥 RUNTIME HEALTH CHECK (CRITICAL FIX)
        if not is_camera_active(cam_id):
            continue

        cam_pos = cam.get("position", {"x": 0, "y": 0, "z": 0})

        distance = calculate_distance(cam_pos, target)

        if distance < 0.01:
            distance = 0.01

        angle = calculate_angle(cam_pos, target)

        # FOV check
        try:
            if not is_in_fov(cam, angle):
                continue
        except Exception:
            pass

        orientation = cam.get("orientation", {})
        cam_pan = orientation.get("pan", 0)

        angle_diff = angle_difference(cam_pan, angle)

        score = (distance * 0.7) + (angle_diff * 0.3)

        if score < best_score:
            best_score = score
            best_camera = cam

    # -------------------------------
    # FALLBACK → ONLY ACTIVE CAMERAS
    # -------------------------------
    if best_camera is None:
        min_dist = float("inf")

        for cam in cameras:
            if not is_camera_active(cam["id"]):
                continue

            cam_pos = cam.get("position", {"x": 0, "y": 0, "z": 0})
            distance = calculate_distance(cam_pos, target)

            if distance < min_dist:
                min_dist = distance
                best_camera = cam

    # -------------------------------
    # FINAL FALLBACK → ANY CAMERA
    # -------------------------------
    if best_camera is None:
        print("[WARN] No active cameras, selecting ANY camera")

        min_dist = float("inf")

        for cam in cameras:
            cam_pos = cam.get("position", {"x": 0, "y": 0, "z": 0})
            distance = calculate_distance(cam_pos, target)

            if distance < min_dist:
                min_dist = distance
                best_camera = cam

    # -------------------------------
    # LOGGING
    # -------------------------------
    if best_camera:
        print(
            f"[SELECTED CAMERA] {best_camera['id']} "
            f"(score={round(best_score, 2)})"
        )
    else:
        print("[ERROR] No camera selected")

    return best_camera