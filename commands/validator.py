def validate_command(cmd, cameras):

    # =================================================
    # CAMERA VALIDATION
    # =================================================

    if cmd.camera_id:

        cam = next(

            (

                c for c in cameras

                if c["id"] == cmd.camera_id
            ),

            None
        )

        if not cam:

            raise Exception(

                "Camera not found"
            )

    # =================================================
    # ANGLE VALIDATION
    # =================================================

    if hasattr(cmd, "angle"):

        if cmd.angle is not None:

            if cmd.angle < 0 or cmd.angle > 180:

                raise Exception(

                    "Invalid angle"
                )

    # =================================================
    # ZOOM VALIDATION
    # =================================================

    if hasattr(cmd, "zoom"):

        if cmd.zoom is not None:

            if cmd.zoom < 1 or cmd.zoom > 40:

                raise Exception(

                    "Invalid zoom"
                )

    # =================================================
    # TRACK VALIDATION
    # =================================================

    if cmd.action == "track":

        if not cmd.target:

            raise Exception(

                "Tracking target missing"
            )

    return True