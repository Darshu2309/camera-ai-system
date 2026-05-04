import time
from database import get_conn

camera_state = {
    "pan": 0,
    "tilt": 0,
    "zoom": 1
}

def execute_camera_action(action_data):
    move = action_data.get("move", "idle")

    if move == "left":
        camera_state["pan"] -= 5
    elif move == "right":
        camera_state["pan"] += 5
    elif move == "center":
        camera_state["pan"] = 0

    time.sleep(0.1)

    return {
        "status": "ok",
        "camera_state": camera_state.copy()
    }

def get_camera_by_id(camera_id):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM cameras WHERE id=%s", (camera_id,))
    r = cursor.fetchone()
    conn.close()

    if not r:
        return None

    return {
        "id": r[0],
        "name": r[1],
        "ip": r[2],
        "x": r[3],
        "y": r[4],
        "z": r[5],
        "pan": r[6],
        "tilt": r[7],
        "zoom": r[8],
        "fov": r[9]
    }