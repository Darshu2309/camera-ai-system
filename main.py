from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import base64

MAX_CAMERAS = 12

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


def save_camera_store(data):
    CAMERAS_FILE.write_text(json.dumps(data, indent=4))


def load_cameras():
    global cameras
    cameras = load_camera_store()
    print(f"[INFO] Loaded {len(cameras)} cameras")


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
                frame = cv2.resize(frame, (640, 360))
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
def ai_worker():
    while True:
        for cam_id, stream in list(streams.items()):
            frame = stream.raw_frame   # 🔥 DIRECT ACCESS (NO DELAY)

            if frame is None:
                continue

            # 🔥 small frame for faster AI
            small = cv2.resize(frame, (416, 240))

            detections = detect_objects(small)

            # scale back
            scaled = []
            for obj in detections:
                x1, y1, x2, y2 = obj["bbox"]

                x_scale = 640 / 416
                y_scale = 360 / 240

                scaled.append({
                    "label": obj["label"],
                    "bbox": [
                        int(x1 * x_scale),
                        int(y1 * y_scale),
                        int(x2 * x_scale),
                        int(y2 * y_scale),
                    ]
                })

            with state_lock:
                results[cam_id] = scaled

        time.sleep(0.03)


# ---------------- FRAME ----------------
def render_frame(cam_id):
    stream = streams.get(cam_id)

    if not stream or stream.raw_frame is None:
        blank = np.ones((360, 640, 3), dtype=np.uint8) * 255
        cv2.putText(blank, "NO SIGNAL", (180, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, buffer = cv2.imencode(".jpg", blank)
        return buffer.tobytes()

    frame = stream.raw_frame.copy()   # 🔥 ALWAYS LATEST FRAME

    with state_lock:
        objs = results.get(cam_id, [])

    for obj in objs:
        x1, y1, x2, y2 = obj["bbox"]
        label = obj["label"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    _, buffer = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), 60]
    )

    return buffer.tobytes()

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
async def add_camera(req: Request):
    data = await req.json()
    cams = load_camera_store()

    for cam in cams:
        if cam["ip"] == data["ip"]:
            raise HTTPException(400, "Camera already exists")

    new_id = max([c["id"] for c in cams], default=0) + 1

    cam = {
        "id": new_id,
        "name": data.get("name", f"Camera {new_id}"),
        "ip": data["ip"],
        "username": data.get("username", ""),
        "password": data.get("password", ""),
    }

    cams.append(cam)
    save_camera_store(cams)

    cameras.append(cam)
    init_streams()

    return {"status": "added"}


@app.post("/delete_camera")
async def delete_camera(req: Request):
    data = await req.json()
    cam_id = int(data["id"])

    cams = [c for c in load_camera_store() if c["id"] != cam_id]
    save_camera_store(cams)

    global cameras
    cameras = cams
    init_streams()

    return {"status": "deleted"}


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

            # draw detections
            with state_lock:
                objs = results.get(cam_id, [])

            for obj in objs:
                x1, y1, x2, y2 = obj["bbox"]
                label = obj["label"]

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
                cv2.putText(frame, label, (x1, y1-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

            _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

            # 🔥 SEND BASE64 FRAME
            jpg_as_text = base64.b64encode(buffer).decode("utf-8")

            await websocket.send_text(jpg_as_text)

            await asyncio.sleep(0.005)  # ~30 FPS

    except WebSocketDisconnect:
        print(f"[INFO] WebSocket disconnected for camera {cam_id}")