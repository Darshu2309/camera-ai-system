import math

def select_best_camera(cameras, target):
    best_cam = None
    best_score = float("inf")

    for cam in cameras:
        try:
            # 🔹 Camera position
            cx = cam["position"]["x"]
            cy = cam["position"]["y"]

            # 🔹 Camera orientation (default if missing)
            pan = cam.get("orientation", {}).get("pan", 0)
            fov = cam.get("fov", 90)

            # 🔹 Target difference
            dx = target["x"] - cx
            dy = target["y"] - cy

            distance = math.sqrt(dx**2 + dy**2)

            # 🔹 Angle to target
            target_angle = math.degrees(math.atan2(dy, dx))

            # 🔹 Angle difference
            angle_diff = abs(target_angle - pan)
            if angle_diff > 180:
                angle_diff = 360 - angle_diff

            # 🔹 Angle penalty (smaller is better)
            angle_penalty = angle_diff / 180  # normalize

            # 🔹 Visibility (inside FOV or not)
            if angle_diff <= fov / 2:
                visibility = 0   # good
            else:
                visibility = 5   # bad (penalty)

            # 🔹 Final score
            score = distance + angle_penalty * 5 + visibility

            if score < best_score:
                best_score = score
                best_cam = cam

        except Exception as e:
            print("Camera selection error:", e)

    return best_cam