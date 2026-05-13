from services.ptz_service import zoom_camera


def handle_zoom(cmd, cameras):

    camera_id = cmd.camera_id

    if camera_id is None:
        camera_id = cameras[0]["id"]

    cam = next(
        c for c in cameras
        if c["id"] == camera_id
    )

    return zoom_camera(
        cam,
        cmd.zoom,
        cmd.zoom_direction,
        cmd.continuous
    )