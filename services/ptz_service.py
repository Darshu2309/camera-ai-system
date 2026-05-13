def move_camera(camera, direction, angle):

    print(f"""
=========================
MOVING CAMERA

Camera: {camera['id']}

Direction: {direction}

Angle: {angle}
=========================
""")

    # FUTURE:
    # ONVIF movement here

    return {
        "status": "moved",
        "camera_id": camera["id"],
        "direction": direction,
        "angle": angle
    }

def zoom_camera(
    camera,
    zoom_level,
    zoom_direction,
    continuous=False
):

    mode = "continuous"

    if not continuous:
        mode = "fixed"

    print(f"""
=========================
ZOOM CAMERA

Camera: {camera['id']}

Direction: {zoom_direction}

Zoom Level: {zoom_level}

Mode: {mode}
=========================
""")

    return {
        "status": f"zoom_{zoom_direction}",
        "camera_id": camera["id"],
        "zoom": zoom_level,
        "continuous": continuous
    }

def stop_camera(camera):

    print(f"""
=========================
STOP CAMERA

Camera: {camera['id']}
=========================
""")

    # FUTURE:
    # ONVIF stop command

    return {
        "status": "stopped",
        "camera_id": camera["id"]
    }