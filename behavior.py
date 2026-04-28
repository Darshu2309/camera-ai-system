import time

track_history = {}

def check_loitering(obj_id, position):
    now = time.time()

    if obj_id not in track_history:
        track_history[obj_id] = {
            "start_time": now,
            "last_position": position
        }
        return False

    prev = track_history[obj_id]

    dx = abs(position[0] - prev["last_position"][0])
    dy = abs(position[1] - prev["last_position"][1])

    if dx < 0.5 and dy < 0.5:
        if now - prev["start_time"] > 10:
            return True
    else:
        track_history[obj_id] = {
            "start_time": now,
            "last_position": position
        }

    return False


def check_intrusion(position):
    x, y, _ = position

    # simple zone
    if 2 < x < 6 and 2 < y < 6:
        return True

    return False