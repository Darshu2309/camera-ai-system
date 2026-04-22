import math

def calculate_angles(cx, cy, frame_w, frame_h, cam):
    """
    cam = {
        x, y, z, pan, tilt, fov
    }
    """

    # Normalize
    nx = (cx / frame_w) - 0.5
    ny = (cy / frame_h) - 0.5

    # Convert to angle offsets
    pan_offset = nx * cam["fov"]
    tilt_offset = ny * cam["fov"]

    # Final angles
    new_pan = cam["pan"] + pan_offset
    new_tilt = cam["tilt"] + tilt_offset

    return new_pan, new_tilt