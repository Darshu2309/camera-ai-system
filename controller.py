def decide_action(objects, frame_width):
    if not objects:
        return {"move": "idle", "zoom": "none"}

    persons = [o for o in objects if o["label"] == "person"]

    if not persons:
        return {"move": "idle", "zoom": "none"}

    x1, y1, x2, y2 = persons[0]["bbox"]
    center_x = (x1 + x2) // 2

    frame_center = frame_width // 2

    if center_x < frame_center - 50:
        move = "left"
    elif center_x > frame_center + 50:
        move = "right"
    else:
        move = "center"

    return {"move": move, "zoom": "none"}