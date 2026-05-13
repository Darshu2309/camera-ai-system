from services.geo_service import (
    haversine_distance,
    calculate_bearing
)


def select_best_camera(cameras, target):

    best_camera = None

    best_score = float("inf")

    for cam in cameras:

        try:

            # =====================================
            # CAMERA ACTIVE CHECK
            # =====================================

            if not cam.get("active", True):
                continue

            # =====================================
            # POSITION CHECK
            # =====================================

            position = cam.get("position", {})

            if (
                "latitude" not in position
                or
                "longitude" not in position
            ):

                print(
                    f"[SKIPPED CAMERA] "
                    f"{cam.get('id')} "
                    f"missing lat/lon"
                )

                continue

            # =====================================
            # DISTANCE CALCULATION
            # =====================================

            distance = haversine_distance(

                position["latitude"],
                position["longitude"],

                target["latitude"],
                target["longitude"]
            )

            # =====================================
            # TARGET BEARING
            # =====================================

            target_bearing = calculate_bearing(

                position["latitude"],
                position["longitude"],

                target["latitude"],
                target["longitude"]
            )

            # =====================================
            # CURRENT CAMERA ORIENTATION
            # =====================================

            orientation = cam.get(
                "orientation",
                {}
            )

            cam_pan = orientation.get(
                "pan",
                0
            )

            # =====================================
            # ANGLE DIFFERENCE
            # =====================================

            angle_diff = abs(
                target_bearing - cam_pan
            )

            # =====================================
            # FINAL SCORE
            # PURE DISTANCE-BASED
            # =====================================

            score = distance

            # =====================================
            # DEBUG LOGGING
            # =====================================

            print(f"""

================================

CAMERA: {cam['id']}

TYPE: {cam.get('type', 'fixed')}

LATITUDE:
{position['latitude']}

LONGITUDE:
{position['longitude']}

DISTANCE:
{distance}

TARGET_BEARING:
{target_bearing}

ANGLE_DIFF:
{angle_diff}

FINAL_SCORE:
{score}

================================

""")

            # =====================================
            # BEST CAMERA SELECTION
            # =====================================

            if score < best_score:

                best_score = score

                best_camera = cam

        except Exception as e:

            print(
                "[CAM SELECT ERROR]",
                e
            )

    # =====================================
    # FINAL LOGGING
    # =====================================

    if best_camera:

        print(f"""

=============================
CAMERA SELECTED
=============================

ID:
{best_camera.get('id')}

TYPE:
{best_camera.get('type', 'fixed')}

POSITION:
{best_camera.get('position')}

BEST SCORE:
{round(best_score, 4)}

=============================

""")

    else:

        print(
            "[CAM SELECT] No suitable camera found"
        )

    return best_camera


def calculate_ptz(camera, target):

    try:

        position = camera.get(
            "position",
            {}
        )

        # =====================================
        # SAFETY CHECK
        # =====================================

        if (
            "latitude" not in position
            or
            "longitude" not in position
        ):

            return {

                "pan": 0,

                "tilt": 0
            }

        # =====================================
        # GEO BEARING
        # =====================================

        pan = calculate_bearing(

            position["latitude"],
            position["longitude"],

            target["latitude"],
            target["longitude"]
        )

        return {

            "pan": round(pan, 2),

            "tilt": 0
        }

    except Exception as e:

        print(
            "[PTZ CALC ERROR]",
            e
        )

        return {

            "pan": 0,

            "tilt": 0
        }


def initialize_camera_orientations(cameras):

    for cam in cameras:

        # =====================================
        # DEFAULT ORIENTATION
        # =====================================

        if "orientation" not in cam:

            cam["orientation"] = {

                "pan": 0,

                "tilt": 0,

                "zoom": 1
            }

        # =====================================
        # DEFAULT CAMERA TYPE
        # =====================================

        if "type" not in cam:

            cam["type"] = "fixed"

        # =====================================
        # DEFAULT ACTIVE STATE
        # =====================================

        if "active" not in cam:

            cam["active"] = True

    print(
        "[INIT] Camera orientations initialized"
    )