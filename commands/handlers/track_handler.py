from services.tracking_service import start_tracking


def handle_track(cmd, cameras):

    camera_id = cmd.camera_id

    if camera_id is None:
        raise Exception("Camera ID required")

    cam = next(
        c for c in cameras
        if c["id"] == camera_id
    )

    result = start_tracking(
        cam["id"],
        cmd.target
    )

    return {
        "status": "tracking_started",
        "camera_id": cam["id"],
        "target": cmd.target,
        "session": result
    }