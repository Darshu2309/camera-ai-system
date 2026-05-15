import re

from commands.aliases import ALIASES

from commands.intents import *


# =====================================================
# NORMALIZATION
# =====================================================

def normalize_command(command):

    command = command.lower().strip()

    words = command.split()

    normalized = []

    for word in words:

        normalized.append(

            ALIASES.get(word, word)
        )

    return " ".join(normalized)


# =====================================================
# DETECT INTENT
# =====================================================

def detect_intent(command):

    words = command.split()

    for word in words:

        if word in MOVE_WORDS:
            return "move"

        if word in TRACK_WORDS:
            return "track"

        if word in ZOOM_WORDS:
            return "zoom"

        if word in STOP_WORDS:
            return "stop"

    return None


# =====================================================
# ENTITY EXTRACTION
# =====================================================

def extract_entities(command):

    entities = {}

    # CAMERA ID

    cam_match = re.search(

        r"camera (\\d+)",

        command
    )

    if cam_match:

        entities["camera_id"] = int(

            cam_match.group(1)
        )

    # DIRECTION

    for direction in [

        "left",
        "right",
        "up",
        "down"
    ]:

        if direction in command:

            entities["direction"] = direction

    # ANGLE

    angle_match = re.search(

        r"(\\d+) degrees",

        command
    )

    if angle_match:

        entities["angle"] = float(

            angle_match.group(1)
        )

    # ZOOM

    zoom_match = re.search(

        r"(\\d+)x",

        command
    )

    if zoom_match:

        entities["zoom"] = float(

            zoom_match.group(1)
        )

    # TARGETS

    for target in [

        "person",
        "vehicle",
        "car",
        "intruder"
    ]:

        if target in command:

            entities["target"] = target

    # LOCATIONS

    for location in [

        "gate",
        "parking",
        "warehouse",
        "entrance"
    ]:

        if location in command:

            entities["location"] = location

    return entities