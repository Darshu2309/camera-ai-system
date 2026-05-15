from services.geo_service import (
    angular_distance,
    calculate_bearing,
    haversine_distance_meters,
    normalize_angle,
)


EARTH_RADIUS_METERS = 6371000
DEFAULT_HORIZONTAL_FOV = 90.0
DEFAULT_VERTICAL_FOV = 60.0
DEFAULT_RANGE_METERS = 150.0


def get_camera_fov(camera):
    fov = camera.get("fov", {})
    coverage = camera.get("coverage", {})

    if isinstance(fov, dict):
        horizontal = fov.get("horizontal", DEFAULT_HORIZONTAL_FOV)
        vertical = fov.get("vertical", DEFAULT_VERTICAL_FOV)
    else:
        horizontal = fov or coverage.get("fov_angle") or DEFAULT_HORIZONTAL_FOV
        vertical = coverage.get("vertical_fov", DEFAULT_VERTICAL_FOV)

    return {
        "horizontal": _bounded_float(horizontal, DEFAULT_HORIZONTAL_FOV, 1, 180),
        "vertical": _bounded_float(vertical, DEFAULT_VERTICAL_FOV, 1, 180),
    }


def get_camera_range(camera):
    coverage = camera.get("coverage", {})
    value = (
        coverage.get("max_range")
        or coverage.get("range_meters")
        or camera.get("max_range")
        or camera.get("range")
        or DEFAULT_RANGE_METERS
    )
    return _bounded_float(value, DEFAULT_RANGE_METERS, 1, 10000)


def get_pan_sweep(camera):
    coverage = camera.get("coverage", {})
    orientation = camera.get("orientation", {})
    pan = _bounded_float(orientation.get("pan", 0), 0, -360, 360)
    fov = get_camera_fov(camera)["horizontal"]
    half_fov = fov / 2

    if coverage.get("pan_min") is not None and coverage.get("pan_max") is not None:
        return (
            normalize_angle(float(coverage["pan_min"]) - half_fov),
            normalize_angle(float(coverage["pan_max"]) + half_fov),
        )

    if coverage.get("bearing_start") is not None and coverage.get("bearing_end") is not None:
        return (
            normalize_angle(float(coverage["bearing_start"])),
            normalize_angle(float(coverage["bearing_end"])),
        )

    return normalize_angle(pan - half_fov), normalize_angle(pan + half_fov)


def build_visibility_polygon(camera, segments=12):
    position = camera.get("position", {})
    lat = position.get("latitude")
    lon = position.get("longitude")
    if lat is None or lon is None:
        return []

    start, end = get_pan_sweep(camera)
    bearings = _sector_bearings(start, end, segments)
    polygon = [{"latitude": lat, "longitude": lon}]

    for bearing in bearings:
        point = destination_point(lat, lon, bearing, get_camera_range(camera))
        polygon.append(point)

    polygon.append({"latitude": lat, "longitude": lon})
    return polygon


def evaluate_visibility(camera, target):
    position = camera.get("position", {})
    lat = position.get("latitude")
    lon = position.get("longitude")

    if lat is None or lon is None:
        return {
            "visible": False,
            "reason": "camera_missing_position",
            "score": None,
        }

    distance = haversine_distance_meters(
        lat,
        lon,
        target["latitude"],
        target["longitude"],
    )
    bearing = calculate_bearing(
        lat,
        lon,
        target["latitude"],
        target["longitude"],
    )

    if distance > get_camera_range(camera):
        return _visibility_result(False, "target_out_of_range", distance, bearing)

    polygon = build_visibility_polygon(camera)
    if polygon and not point_in_polygon(target, polygon):
        return _visibility_result(False, "outside_visibility_polygon", distance, bearing)

    for zone in camera.get("blind_zones", []):
        if _target_in_blind_zone(target, zone):
            return _visibility_result(
                False,
                zone.get("reason", "blocked_by_occlusion"),
                distance,
                bearing,
            )

    pan = float(camera.get("orientation", {}).get("pan", 0))
    orientation_penalty = angular_distance(bearing, pan) * 0.25
    score = distance + orientation_penalty

    result = _visibility_result(True, "visible", distance, bearing)
    result["orientation_penalty"] = round(orientation_penalty, 2)
    result["score"] = round(score, 2)
    result["polygon"] = polygon
    return result


def point_in_polygon(point, polygon):
    x = point["longitude"]
    y = point["latitude"]
    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi = polygon[i]["longitude"]
        yi = polygon[i]["latitude"]
        xj = polygon[j]["longitude"]
        yj = polygon[j]["latitude"]

        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def destination_point(latitude, longitude, bearing_degrees, distance_meters):
    import math

    bearing = math.radians(bearing_degrees)
    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)
    angular_distance = distance_meters / EARTH_RADIUS_METERS

    lat2 = math.asin(
        math.sin(lat1) * math.cos(angular_distance)
        + math.cos(lat1) * math.sin(angular_distance) * math.cos(bearing)
    )
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular_distance) * math.cos(lat1),
        math.cos(angular_distance) - math.sin(lat1) * math.sin(lat2),
    )

    return {
        "latitude": round(math.degrees(lat2), 8),
        "longitude": round(math.degrees(lon2), 8),
    }


def _visibility_result(visible, reason, distance, bearing):
    return {
        "visible": visible,
        "reason": reason,
        "distance_meters": round(distance, 2),
        "target_bearing": round(bearing, 2),
        "score": None,
    }


def _target_in_blind_zone(target, zone):
    polygon = zone.get("polygon")
    if polygon:
        return point_in_polygon(target, polygon)

    return False


def _sector_bearings(start, end, segments):
    start = normalize_angle(start)
    end = normalize_angle(end)
    sweep = (end - start) % 360
    if sweep == 0:
        sweep = 360

    return [
        normalize_angle(start + (sweep * i / max(segments, 1)))
        for i in range(segments + 1)
    ]


def _bounded_float(value, default, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(parsed, maximum))
