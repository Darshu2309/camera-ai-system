import re

from models.command_models import ParsedCommand

from commands.command_engine import (

    normalize_command,

    detect_intent,

    extract_entities
)


def parse_command(command: str):

    # =================================================
    # NORMALIZATION
    # =================================================

    command = normalize_command(command)

    # =================================================
    # INTENT
    # =================================================

    intent = detect_intent(command)

    if not intent:

        raise Exception(

            "Intent not detected"
        )

    # =================================================
    # ENTITIES
    # =================================================

    entities = extract_entities(command)

    # =================================================
    # MOVE
    # =================================================

    if intent == "move":

        return ParsedCommand(

            action="move",

            camera_id=entities.get(
                "camera_id"
            ),

            direction=entities.get(
                "direction"
            ),

            angle=entities.get(
                "angle",
                5
            )
        )

    # =================================================
    # ZOOM
    # =================================================

    if intent == "zoom":

        return ParsedCommand(

            action="zoom",

            camera_id=entities.get(
                "camera_id"
            ),

            zoom=entities.get(
                "zoom",
                1
            ),

            zoom_direction="in"
        )

    # =================================================
    # STOP
    # =================================================

    if intent == "stop":

        return ParsedCommand(

            action="stop",

            camera_id=entities.get(
                "camera_id"
            )
        )

    # =================================================
    # TRACK
    # =================================================

    if intent == "track":

        # -----------------------------
        # TRACK NEAREST PERSON
        # -----------------------------

        if "nearest" in command:

            return ParsedCommand(

                action="track_nearest_person",

                camera_id=entities.get(
                    "camera_id"
                )
            )

        # -----------------------------
        # TRACK SUSPICIOUS
        # -----------------------------

        if "suspicious" in command:

            return ParsedCommand(

                action="track_suspicious",

                camera_id=entities.get(
                    "camera_id"
                )
            )

        # -----------------------------
        # NORMAL TRACK
        # -----------------------------

        return ParsedCommand(

            action="track",

            target=entities.get(
                "target"
            ),

            camera_id=entities.get(
                "camera_id"
            )
        )

    raise Exception("Invalid command")