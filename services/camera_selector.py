from services.geo_service import calculate_bearing
from services.visibility_engine import (
    build_visibility_polygon,
    evaluate_visibility,
    get_camera_fov,
    get_camera_range,
    get_pan_sweep,
)


DEFAULT_VIEW_RANGE_METERS = 150.0


def get_camera_label(camera):
    return camera.get("description") or camera.get("name") or f"Camera {camera.get('id')}"


def _get_fov(camera):
    return get_camera_fov(camera)["horizontal"]


def _get_range_meters(camera):
    return get_camera_range(camera)


def get_visible_sector(camera):
    return get_pan_sweep(camera)


def describe_camera_coverage(camera):
    start, end = get_visible_sector(camera)
    return {
        "bearing_start": round(start, 2),
        "bearing_end": round(end, 2),
        "range_meters": round(_get_range_meters(camera), 2),
        "fov_angle": round(_get_fov(camera), 2),
        "fov": get_camera_fov(camera),
        "visibility_polygon": build_visibility_polygon(camera),
    }


def target_is_visible(camera, target, target_bearing, distance_meters):
    visibility = evaluate_visibility(camera, target)
    return visibility["visible"], visibility["reason"]


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
            visibility = evaluate_visibility(cam, target)

            if not visibility["visible"]:
                print(
                    "[SKIPPED CAMERA] "
                    f"{get_camera_label(cam)} "
                    f"cannot see target: {visibility['reason']}"
                )
                continue

            # FINAL SCORE
            # Distance remains important, but only after range/FOV/occlusion checks.
            # =====================================

            score = visibility["score"]

            # =====================================
            # DEBUG LOGGING
            # =====================================

            print(f"""

================================

CAMERA:
{get_camera_label(cam)}

ID:
{cam['id']}

TYPE: {cam.get('type', 'fixed')}

LATITUDE:
{position['latitude']}

LONGITUDE:
{position['longitude']}

DISTANCE:
{visibility['distance_meters']} meters

TARGET_BEARING:
{visibility['target_bearing']}

VISIBILITY:
{visibility['reason']}

FINAL_SCORE:
{round(score, 2)}

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

DESCRIPTION:
{get_camera_label(best_camera)}

TYPE:
{best_camera.get('type', 'fixed')}

POSITION:
{best_camera.get('position')}

BEST SCORE:
{round(best_score, 2)}

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
