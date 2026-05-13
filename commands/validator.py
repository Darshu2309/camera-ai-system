def validate_command(cmd, cameras):

    if cmd.camera_id:

        cam = next(
            (
                c for c in cameras
                if c["id"] == cmd.camera_id
            ),
            None
        )

        if not cam:
            raise Exception("Camera not found")

    if cmd.angle:

        if cmd.angle < 0 or cmd.angle > 90:
            raise Exception("Invalid angle")

    return True