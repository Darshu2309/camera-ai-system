import time

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

    time.sleep(0.01)

    return {
        "status": "ok",
        "camera_state": camera_state.copy()
    }