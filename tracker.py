import numpy as np

tracks = {}
track_id = 0

def assign_tracks(detections):
    global track_id

    updated = []

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        center = ((x1 + x2)//2, (y1 + y2)//2)

        best_match = None
        best_dist = 9999

        for tid, t in tracks.items():
            prev_center = t["center"]
            dist = np.linalg.norm(np.array(center) - np.array(prev_center))

            if dist < best_dist and dist < 60:
                best_dist = dist
                best_match = tid

        if best_match is not None:
            tracks[best_match]["center"] = center
            updated.append({**det, "track_id": best_match})
        else:
            tracks[track_id] = {"center": center}
            updated.append({**det, "track_id": track_id})
            track_id += 1

    return updated