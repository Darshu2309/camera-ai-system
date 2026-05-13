import re

from models.command_models import ParsedCommand


def parse_command(command: str):

    command = command.lower()

    # -----------------------------
    # TRACK NEAREST PERSON
    # -----------------------------

    if "track nearest person" in command:

        cam_match = re.search(
            r"camera (\d+)",
            command
        )

        camera_id = None

        if cam_match:
            camera_id = int(
                cam_match.group(1)
            )

        return ParsedCommand(

            action="track_nearest_person",

            camera_id=camera_id
        )

    # -----------------------------
    # TRACK SUSPICIOUS
    # -----------------------------

    if "track suspicious" in command:

        cam_match = re.search(
            r"camera (\d+)",
            command
        )

        camera_id = None

        if cam_match:
            camera_id = int(
                cam_match.group(1)
            )

        return ParsedCommand(

            action="track_suspicious",

            camera_id=camera_id
        )

    # -----------------------------
    # MOVE
    # -----------------------------

    move_match = re.search(
        r"move camera (\d+) (left|right|up|down) (\d+) degrees",
        command
    )

    if move_match:

        camera_id = move_match.group(1)

        direction = move_match.group(2)

        angle = move_match.group(3)

        return ParsedCommand(

            action="move",

            camera_id=int(camera_id),

            angle=float(angle),

            direction=direction
        )

    # -----------------------------
    # ZOOM
    # -----------------------------

    zoom_match = re.search(
        r"zoom (in|out)( (\d+)x)?( continuously)?( camera (\d+))?",
        command
    )

    if zoom_match:

        direction = zoom_match.group(1)

        zoom_level = zoom_match.group(3)

        continuous = zoom_match.group(4)

        camera_id = zoom_match.group(6)

        return ParsedCommand(

            action="zoom",

            camera_id=int(camera_id) if camera_id else None,

            zoom=float(zoom_level) if zoom_level else 1,

            zoom_direction=direction,

            continuous=True if continuous else False
        )

    # -----------------------------
    # STOP
    # -----------------------------

    stop_match = re.search(
        r"stop( camera (\d+))?",
        command
    )

    if stop_match:

        camera_id = stop_match.group(2)

        return ParsedCommand(

            action="stop",

            camera_id=int(camera_id) if camera_id else None
        )

    # -----------------------------
    # TRACK
    # -----------------------------

    track_match = re.search(
        r"(track|follow) (.+?) camera (\d+)",
        command
    )

    if track_match:

        target = track_match.group(2)

        camera_id = track_match.group(3)

        return ParsedCommand(

            action="track",

            target=target,

            camera_id=int(camera_id)
        )

    raise Exception("Invalid command")