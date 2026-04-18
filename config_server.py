from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path

app = FastAPI(title="Camera Config Server")
FILE = Path(__file__).resolve().parent / "cameras.json"


class CameraPayload(BaseModel):
    ip: str
    username: str = ""
    password: str = ""
    name: str = ""
    rtsp_url: str = ""


class DeletePayload(BaseModel):
    id: int


def normalize(cam):
    return {
        "id": int(cam["id"]),
        "name": cam.get("name") or f"Camera {cam['id']}",
        "ip": cam["ip"],
        "username": cam.get("username", ""),
        "password": cam.get("password", ""),
        "rtsp_url": cam.get("rtsp_url", "")
    }


def load():
    if not FILE.exists():
        FILE.write_text("[]", encoding="utf-8")
        return []
    raw = json.loads(FILE.read_text(encoding="utf-8"))
    return [normalize(cam) for cam in raw]


def save(data):
    FILE.write_text(json.dumps([normalize(cam) for cam in data], indent=4), encoding="utf-8")


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
def get():
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
        "rtsp_url": payload.rtsp_url
    })

    save(cams)
    return {"status": "added", "id": new_id}


@app.post("/delete_camera")
async def delete(payload: DeletePayload):
    cams = [cam for cam in load() if cam["id"] != payload.id]
    save(cams)
    return {"status": "deleted"}
