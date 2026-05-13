from services.tracking_service import stop_tracking
from services.ptz_service import stop_camera


def handle_stop(cmd, cameras):

    camera_id = cmd.camera_id

    if camera_id is None:
        raise Exception("Camera ID required")

    cam = next(
        c for c in cameras
        if c["id"] == camera_id
    )

    stop_tracking(cam["id"])

    return stop_camera(cam)