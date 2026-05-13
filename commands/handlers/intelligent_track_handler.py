from services.ai_service import (
    find_nearest_person,
    find_suspicious_target
)

from services.tracking_service import (
    start_tracking
)


def handle_track_nearest(
    cmd,
    cameras
):

    target = find_nearest_person(
        cmd.camera_id
    )

    if not target:

        return {

            "status":
            "no_person_found"
        }

    session = start_tracking(

        cmd.camera_id,

        "person"
    )

    return {

        "status":
        "tracking_started",

        "camera_id":
        cmd.camera_id,

        "target":
        target,

        "session":
        session
    }


def handle_track_suspicious(
    cmd,
    cameras
):

    target = find_suspicious_target(
        cmd.camera_id
    )

    if not target:

        return {

            "status":
            "no_suspicious_target"
        }

    session = start_tracking(

        cmd.camera_id,

        target["label"]
    )

    return {

        "status":
        "tracking_started",

        "camera_id":
        cmd.camera_id,

        "target":
        target,

        "session":
        session
    }