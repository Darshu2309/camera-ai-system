import math


def haversine_distance(lat1, lon1, lat2, lon2):

    R = 6371

    d_lat = math.radians(lat2 - lat1)

    d_lon = math.radians(lon2 - lon1)

    a = (

        math.sin(d_lat / 2) ** 2 +

        math.cos(math.radians(lat1)) *

        math.cos(math.radians(lat2)) *

        math.sin(d_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return R * c


def calculate_bearing(lat1, lon1, lat2, lon2):

    d_lon = math.radians(lon2 - lon1)

    lat1 = math.radians(lat1)

    lat2 = math.radians(lat2)

    x = math.sin(d_lon) * math.cos(lat2)

    y = (

        math.cos(lat1) *

        math.sin(lat2)

        -

        math.sin(lat1) *

        math.cos(lat2) *

        math.cos(d_lon)
    )

    bearing = math.degrees(
        math.atan2(x, y)
    )

    return (bearing + 360) % 360