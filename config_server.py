from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path

app = FastAPI(title="Camera Config Server")

FILE = Path(__file__).resolve().parent / "cameras.json"


# =========================
# MODELS
# =========================

class CameraPayload(BaseModel):
    ip: str
    username: str = ""
    password: str = ""
    name: str = ""
    rtsp_url: str = ""

    # 🔥 NEW FIELDS
    position: dict = {"x": 0.0, "y": 0.0, "z": 2.0}
    orientation: dict = {"pan": 0.0, "tilt": 0.0, "zoom": 1.0}
    fov: float = 90.0
    type: str = "fixed"
    status: str = "active"


class DeletePayload(BaseModel):
    id: int


# =========================
# NORMALIZE DATA
# =========================

def normalize(cam):
    return {
        "id": int(cam["id"]),
        "name": cam.get("name") or f"Camera {cam['id']}",
        "ip": cam["ip"],
        "username": cam.get("username", ""),
        "password": cam.get("password", ""),
        "rtsp_url": cam.get("rtsp_url", ""),

        # 🔥 REQUIRED FOR YOUR SYSTEM
        "position": cam.get("position", {"x": 0.0, "y": 0.0, "z": 2.0}),
        "orientation": cam.get("orientation", {"pan": 0.0, "tilt": 0.0, "zoom": 1.0}),
        "fov": cam.get("fov", 90.0),
        "type": cam.get("type", "fixed"),
        "status": cam.get("status", "active")
    }


# =========================
# FILE OPERATIONS
# =========================

def load():
    if not FILE.exists():
        FILE.write_text("[]", encoding="utf-8")
        return []

    raw = json.loads(FILE.read_text(encoding="utf-8"))
    return [normalize(cam) for cam in raw]


def save(data):
    FILE.write_text(
        json.dumps([normalize(cam) for cam in data], indent=4),
        encoding="utf-8"
    )


# =========================
# ROUTES
# =========================

@app.get("/")
def root():
    return {
        "message": "Camera config server is running.",
        "endpoints": ["/cameras", "/add_camera", "/delete_camera", "/docs"]
    }


@app.get("/health")
def health():
    cams = load()
    return {"camera_count": len(cams)}


@app.get("/cameras")
def get_cameras():
    return load()


@app.post("/add_camera")
async def add(payload: CameraPayload):
    cams = load()

    for cam in cams:
        if cam["ip"] == payload.ip:
            raise HTTPException(status_code=400, detail="Camera already exists")

    new_id = max([cam["id"] for cam in cams], default=0) + 1

    cams.append({
        "id": new_id,
        "name": payload.name or f"Camera {new_id}",
        "ip": payload.ip,
        "username": payload.username,
        "password": payload.password,
        "rtsp_url": payload.rtsp_url,

        # 🔥 NEW DATA
        "position": payload.position,
        "orientation": payload.orientation,
        "fov": payload.fov,
        "type": payload.type,
        "status": payload.status
    })

    save(cams)

    return {"status": "added", "id": new_id}


@app.post("/delete_camera")
async def delete(payload: DeletePayload):
    cams = [cam for cam in load() if cam["id"] != payload.id]
    save(cams)
    return {"status": "deleted"}