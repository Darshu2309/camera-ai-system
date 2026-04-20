from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from ptz_controller import PTZController
import asyncio
import asyncio
import base64
import math

MAX_CAMERAS = 12
PTZ_MODE = "simulation"   # change to "real" later

import cv2
import json
import os
import socket
import threading
import time
import numpy as np
from pathlib import Path
from urllib.parse import quote

from detector import detect_objects

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|max_delay;0"

BASE_DIR = Path(__file__).resolve().parent
CAMERAS_FILE = BASE_DIR / "cameras.json"

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

cameras = []
streams = {}
results = {}
state_lock = threading.Lock()


# ---------------- CAMERA STORE ----------------
def load_camera_store():
    if not CAMERAS_FILE.exists():
        CAMERAS_FILE.write_text("[]")
        return []
    return json.loads(CAMERAS_FILE.read_text())
    def init_camera_defaults():
        """Initialize default camera if store is empty"""

def save_camera_store(data):
    CAMERAS_FILE.write_text(json.dumps(data, indent=4))


def load_cameras():
    global cameras
    cameras = load_camera_store()

    # 🔥 Ensure all cameras have metadata
    for cam in cameras:
        if "position" not in cam:
            cam["position"] = {"x": 0, "y": 0, "z": 0}

        if "orientation" not in cam:
            cam["orientation"] = {"pan": 0, "tilt": 0, "zoom": 1}

        if "fov" not in cam:
            cam["fov"] = 90

    print(f"[INFO] Loaded {len(cameras)} cameras with metadata")


# ---------------- RTSP ----------------
def build_rtsp_url(cam):
    password = quote(cam.get("password", ""), safe="")
    username = quote(cam.get("username", ""), safe="")
    return f"rtsp://{username}:{password}@{cam['ip']}:554/cam/realmonitor?channel=1&subtype=1"


# ---------------- STREAM ----------------
class CameraStream:
    def __init__(self, cam):
        self.cam = cam
        self.cap = None
        self.frame = None        # processed frame (optional)
        self.raw_frame = None    # 🔥 NEW (for live stream)
        self.running = True
        self.connect()
        threading.Thread(target=self.update, daemon=True).start()

    def connect(self):
        if self.cap:
            self.cap.release()

        url = build_rtsp_url(self.cam)
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ok, frame = self.cap.read()
        if ok:
            self.cap = self.cap
            self.raw_frame = frame
            print(f"[INFO] Connected camera {self.cam['id']}")
        else:
            self.cap = None
            print(f"[WARN] No stream for camera {self.cam['id']}")

    def update(self):
        while self.running:
            if not self.cap:
                self.connect()
                time.sleep(1)
                continue

            self.cap.grab()

            ret, frame = self.cap.read()

            if ret:
                frame = cv2.resize(frame, (960, 540))
                self.raw_frame = frame
            else:
                self.connect()

        # 🔥 VERY FAST LOOP
            time.sleep(0.015)  # fast refresh

    def read(self):
        return None if self.raw_frame is None else self.raw_frame.copy()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

# ---------------- STREAM MANAGER ----------------
def init_streams():
    global streams

    old_streams = streams.copy()
    new_ids = {cam["id"] for cam in cameras}

    # stop removed
    for cam_id in list(old_streams.keys()):
        if cam_id not in new_ids:
            old_streams[cam_id].stop()
            del old_streams[cam_id]

    streams = old_streams

    # start new
    for cam in cameras:
        if cam["id"] not in streams:
            streams[cam["id"]] = CameraStream(cam)


# ---------------- AI ----------------
# ---------------- AI ----------------
def ai_worker():
    while True:
        for cam_id, stream in list(streams.items()):
            frame = stream.raw_frame

            if frame is None:
                continue

            # 🔥 UPDATED (added alert)
            processed_frame, detections, alert = detect_objects(frame, cam_id)

            with state_lock:
                results[cam_id] = {
                    "objects": detections,
                    "alert": alert
                }

        time.sleep(0.03)

# ---------------- FRAME ----------------
# ---------------- FRAME ----------------
def render_frame(cam_id):
    stream = streams.get(cam_id)

    if not stream or stream.raw_frame is None:
        blank = np.ones((360, 640, 3), dtype=np.uint8) * 255
        cv2.putText(blank, "NO SIGNAL", (180, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, buffer = cv2.imencode(".jpg", blank)
        return buffer.tobytes()

    frame = stream.raw_frame.copy()

    with state_lock:
        data = results.get(cam_id, {"objects": [], "alert": False})
        objs = data["objects"]
        alert = data["alert"]

    # ✅ DRAW OBJECTS (FIXED — ADD BOX)
    for obj in objs:
        x1, y1, x2, y2 = obj["bbox"]
        label = obj["label"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    # 🚨 ALERT DISPLAY
    if alert:
        cv2.putText(frame, "🚨 PERSON MOVING",
                    (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    3)

        cv2.rectangle(frame, (0, 0),
                      (frame.shape[1], frame.shape[0]),
                      (0, 0, 255), 4)

    _, buffer = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), 60]
    )

    return buffer.tobytes()

def calculate_ptz(camera, target):
    cam_pos = camera["position"]

    dx = target["x"] - cam_pos["x"]
    dy = target["y"] - cam_pos["y"]
    dz = target["z"] - cam_pos["z"]

    distance_xy = math.sqrt(dx**2 + dy**2)

    pan = math.degrees(math.atan2(dy, dx))
    tilt = math.degrees(math.atan2(dz, distance_xy))

    return {
        "pan": round(pan, 2),
        "tilt": round(tilt, 2),
        "distance": round(distance_xy, 2)
    }

class Position(BaseModel):
    x: float
    y: float
    z: float

class Orientation(BaseModel):
    pan: float
    tilt: float
    zoom: float

class CameraCreate(BaseModel):
    ip: str
    username: str
    password: str
    name: str
    position: Position
    orientation: Orientation
    fov: float

class MoveRequest(BaseModel):
    camera_id: int
    target: Position

class DeleteRequest(BaseModel):
    id: int

# 🔥 SINGLE FRAME
@app.get("/frame/{cam_id}")
def frame(cam_id: int):
    return StreamingResponse(iter([render_frame(cam_id)]),
                             media_type="image/jpeg")


# 🔥 CONTINUOUS STREAM (FIX FOR YOUR ISSUE)
@app.get("/video/{cam_id}")
def video(cam_id: int):
    def generate():
        while True:
            frame = render_frame(cam_id)

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                frame +
                b"\r\n"
            )

            time.sleep(0.08)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ---------------- APIs ----------------
@app.get("/cameras")
def get_cameras():
    return cameras


@app.get("/status")
def status():
    return {"status": "running"}


@app.post("/add_camera")
async def add_camera(req: CameraCreate):
    cams = load_camera_store()

    for cam in cams:
        if cam["ip"] == req.ip:
            raise HTTPException(400, "Camera already exists")

    new_id = max([c["id"] for c in cams], default=0) + 1

    cam = {
        "id": new_id,
        "name": req.name,
        "ip": req.ip,
        "username": req.username,
        "password": req.password,

        # 🔥 NEW METADATA
        "position": {
            "x": req.position.x,
            "y": req.position.y,
            "z": req.position.z,
        },
        "orientation": {
            "pan": req.orientation.pan,
            "tilt": req.orientation.tilt,
            "zoom": req.orientation.zoom
        },
        "fov": req.fov
    }

    cams.append(cam)
    save_camera_store(cams)

    cameras.append(cam)
    init_streams()

    return {"status": "added", "camera": cam}


@app.post("/delete_camera")
async def delete_camera(req: DeleteRequest):
    cam_id = req.id

    cams = [c for c in load_camera_store() if c["id"] != cam_id]
    save_camera_store(cams)

    global cameras
    cameras = cams
    init_streams()

    return {"status": "deleted"}

@app.post("/move_to")
async def move_to(data: MoveRequest):
    try:
        cam_id = data.camera_id
        target = data.target.dict()

        cam = next((c for c in cameras if c["id"] == cam_id), None)

        if not cam:
            raise HTTPException(404, "Camera not found")

        ptz = calculate_ptz(cam, target)

        pan = max(min(ptz["pan"] / 180, 1), -1)
        tilt = max(min(ptz["tilt"] / 90, 1), -1)

        # =============================
        # 🔵 SIMULATION MODE
        # =============================
        if PTZ_MODE == "simulation":
            print(f"""
===== PTZ SIMULATION =====
Camera: {cam_id}
Target: {target}

Pan: {ptz['pan']}°
Tilt: {ptz['tilt']}°

Normalized:
Pan: {pan}
Tilt: {tilt}
=========================
""")

            return {
                "status": "simulated",
                "ptz": ptz
            }

        # =============================
        # 🔴 REAL PTZ MODE
        # =============================
        elif PTZ_MODE == "real":
            controller = PTZController(
                cam["ip"],
                cam["username"],
                cam["password"]
            )

            controller.move(pan, tilt, 0)
            await asyncio.sleep(0.7)
            controller.stop()

            print("✅ REAL CAMERA MOVED")

            return {
                "status": "moved",
                "ptz": ptz
            }

    except Exception as e:
        print("PTZ ERROR:", e)
        raise HTTPException(500, str(e))

# 🔥 FIXED HOME
@app.get("/", response_class=HTMLResponse)
def home():
    try:
        file_path = BASE_DIR / "static" / "index.html"

        if not file_path.exists():
            return HTMLResponse("<h1>index.html not found</h1>", status_code=500)

        return HTMLResponse(file_path.read_text(encoding="utf-8"))

    except Exception as e:
        return HTMLResponse(f"<h1>Error</h1><p>{str(e)}</p>", status_code=500)


# ---------------- START ----------------
@app.on_event("startup")
async def startup():
    load_cameras()
    init_streams()
    threading.Thread(target=ai_worker, daemon=True).start()

@app.websocket("/ws/{cam_id}")
async def websocket_stream(websocket: WebSocket, cam_id: int):
    await websocket.accept()

    try:
        while True:
            stream = streams.get(cam_id)

            if not stream or stream.raw_frame is None:
                await asyncio.sleep(0.1)
                continue

            frame = stream.raw_frame.copy()

            h, w = frame.shape[:2]
            cam_center = (w // 2, h // 2)

            cv2.circle(frame, cam_center, 5, (0, 255, 0), -1)

            with state_lock:
                data = results.get(cam_id, {"objects": [], "alert": False})
                objs = data["objects"]
                alert = data["alert"]

            # ✅ DRAW OBJECTS (CLEAN)
            for obj in objs:
                x1, y1, x2, y2 = obj["bbox"]
                label = obj["label"]

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                cv2.putText(frame, label,
                            (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 0),
                            2)

            # 🚨 ALERT
            if alert:
                cv2.putText(frame, "PERSON MOVEMENT DETECTED",
                            (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 0, 255),
                            3)

                cv2.rectangle(frame, (0, 0),
                              (frame.shape[1], frame.shape[0]),
                              (0, 0, 255), 4)

            _, buffer = cv2.imencode(".jpg", frame,
                                    [int(cv2.IMWRITE_JPEG_QUALITY), 90])

            jpg_as_text = base64.b64encode(buffer).decode("utf-8")

            await websocket.send_text(jpg_as_text)

            await asyncio.sleep(0.03)

    except WebSocketDisconnect:
        print(f"[INFO] WebSocket disconnected for camera {cam_id}")