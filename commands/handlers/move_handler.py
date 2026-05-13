from services.ptz_service import move_camera


def handle_move(cmd, cameras):

    cam = next(
        c for c in cameras
        if c["id"] == cmd.camera_id
    )

    return move_camera(
        cam,
        cmd.direction,
        cmd.angle
    )