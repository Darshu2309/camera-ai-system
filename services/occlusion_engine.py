from shapely.geometry import LineString

def is_line_of_sight_clear(
    camera_point,
    target_point,
    obstacles
):
    line = LineString([
        camera_point,
        target_point
    ])

    for obstacle in obstacles:
        if line.intersects(obstacle):
            return False

    return True