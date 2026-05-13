from commands.handlers.move_handler import handle_move
from commands.handlers.zoom_handler import handle_zoom
from commands.handlers.stop_handler import handle_stop
from commands.handlers.track_handler import handle_track

from commands.handlers.intelligent_track_handler import (
    handle_track_nearest,
    handle_track_suspicious
)


def dispatch_command(cmd, cameras):

    if cmd.action == "move":
        return handle_move(cmd, cameras)

    elif cmd.action == "zoom":
        return handle_zoom(cmd, cameras)

    elif cmd.action == "stop":
        return handle_stop(cmd, cameras)

    elif cmd.action == "track":
        return handle_track(cmd, cameras)

    elif cmd.action == "track_nearest_person":

        return handle_track_nearest(
            cmd,
            cameras
        )

    elif cmd.action == "track_suspicious":

        return handle_track_suspicious(
            cmd,
            cameras
        )

    raise Exception("Unknown action")