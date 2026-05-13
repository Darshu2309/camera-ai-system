latest_detections = {}


def update_detections(camera_id, detections):

    latest_detections[camera_id] = detections


def get_detections(camera_id):

    return latest_detections.get(camera_id, [])


def find_target(camera_id, target_name):

    detections = latest_detections.get(
        camera_id,
        []
    )

    for det in detections:

        label = det.get(
            "label",
            ""
        ).lower()

        if target_name.lower() in label:

            return det

    return None


def find_nearest_person(camera_id):

    detections = latest_detections.get(
        camera_id,
        []
    )

    persons = [

        d for d in detections

        if d.get("label") == "person"
    ]

    if not persons:
        return None

    largest = max(

        persons,

        key=lambda p:
        p.get("area", 0)
    )

    return largest


def find_suspicious_target(camera_id):

    detections = latest_detections.get(
        camera_id,
        []
    )

    suspicious_labels = [

        "knife",

        "gun",

        "weapon"
    ]

    for det in detections:

        if det["label"] in suspicious_labels:

            return det

    return None