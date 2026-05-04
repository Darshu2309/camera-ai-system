import math


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

    # 🔥 Default full visibility if missing
    fov = camera.get("fov", 360)

    diff = angle_difference(cam_pan, target_angle)

    return diff <= (fov / 2)

def initialize_camera_orientations(cameras):
    # 🔥 center of your room
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
# MAIN CAMERA SELECTION LOGIC
# -------------------------------

def select_best_camera(cameras, target):
    best_camera = None
    best_score = float("inf")

    for cam in cameras:

        # Skip inactive cameras
        if cam.get("status", "active") != "active":
            continue

        cam_pos = cam.get("position", {"x": 0, "y": 0, "z": 0})

        distance = calculate_distance(cam_pos, target)

        # 🔥 Skip unrealistic near-zero cases (optional but recommended)
        if distance < 0.01:
            distance = 0.01

        angle = calculate_angle(cam_pos, target)

        # 🔥 Safe FOV check
        try:
            if not is_in_fov(cam, angle):
                continue
        except Exception:
            # If any data missing → allow camera
            pass

        # 🔥 Safe orientation
        orientation = cam.get("orientation", {})
        cam_pan = orientation.get("pan", 0)

        angle_diff = angle_difference(cam_pan, angle)

        # 🔥 Improved scoring
        # Distance is priority, angle is secondary
        score = (distance * 0.7) + (angle_diff * 0.3)

        if score < best_score:
            best_score = score
            best_camera = cam

    # -------------------------------
    # FALLBACK → NEAREST CAMERA
    # -------------------------------
    if best_camera is None:
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