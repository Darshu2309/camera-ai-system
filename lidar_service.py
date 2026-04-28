import math
import random

def read_lidar():
    points = []

    for angle in range(0, 360, 5):
        if 30 < angle < 90:
            distance = random.uniform(3, 5)
        else:
            distance = random.uniform(6, 10)

        x = distance * math.cos(math.radians(angle))
        y = distance * math.sin(math.radians(angle))

        points.append({"x": x, "y": y})

    return points