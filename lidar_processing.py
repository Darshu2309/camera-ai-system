from sklearn.cluster import DBSCAN
import numpy as np

def cluster_lidar(points):
    if not points:
        return []

    coords = np.array([[p["x"], p["y"]] for p in points])

    clustering = DBSCAN(eps=0.8, min_samples=4).fit(coords)

    objects = []

    for label in set(clustering.labels_):
        if label == -1:
            continue

        cluster_points = coords[clustering.labels_ == label]
        center = cluster_points.mean(axis=0)

        objects.append({
            "position": center.tolist()
        })

    return objects