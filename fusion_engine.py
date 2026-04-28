def fuse(detections, lidar_objects):
    fused = []

    if not lidar_objects:
        return []

    for obj in lidar_objects:
        lx, ly = obj["position"]

        label = "unknown"

        if detections:
            label = "person"

        fused.append({
            "type": label,
            "position": [lx, ly, 0],
            "confidence": 0.8
        })

    return fused