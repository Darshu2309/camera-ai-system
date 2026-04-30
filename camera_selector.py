import math


def calculate_distance(cam_pos, target):
    dx = target["x"] - cam_pos["x"]
    dy = target["y"] - cam_pos["y"]
    return math.sqrt(dx * dx + dy * dy)


def calculate_angle(cam_pos, target):
    dx = target["x"] - cam_pos["x"]
    dy = target["y"] - cam_pos["y"]
    return math.degrees(math.atan2(dy, dx))


def angle_difference(a1, a2):
    diff = abs(a1 - a2) % 360
    return min(diff, 360 - diff)


def is_in_fov(camera, target_angle):
    cam_pan = camera["orientation"]["pan"]
    fov = camera.get("fov", 90)

    diff = angle_difference(cam_pan, target_angle)

    return diff <= (fov / 2)


def select_best_camera(cameras, target):
    best_camera = None
    best_score = float("inf")

    for cam in cameras:
        if cam.get("status", "active") != "active":
            continue

        cam_pos = cam.get("position", {"x": 0, "y": 0})

        distance = calculate_distance(cam_pos, target)
        angle = calculate_angle(cam_pos, target)

        # Check if target is inside FOV
        if not is_in_fov(cam, angle):
            continue

        # Score = distance + angle penalty
        cam_pan = cam["orientation"]["pan"]
        angle_diff = angle_difference(cam_pan, angle)

        score = distance + (angle_diff * 0.5)

        if score < best_score:
            best_score = score
            best_camera = cam

    # 🔥 Fallback: if no camera in FOV → choose nearest
    if best_camera is None:
        min_dist = float("inf")

        for cam in cameras:
            cam_pos = cam.get("position", {"x": 0, "y": 0})
            distance = calculate_distance(cam_pos, target)

            if distance < min_dist:
                min_dist = distance
                best_camera = cam

    if best_camera:
        print(f"[SELECTED CAMERA] {best_camera['id']} (score={round(best_score,2)})")

    return best_camera