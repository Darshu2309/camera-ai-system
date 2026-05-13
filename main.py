import requests
import asyncio
import base64
import math
import cv2
cv2.setNumThreads(1)
import json
import os
import socket
import threading
import time
import numpy as np;


from pathlib import Path
from urllib.parse import quote
from datetime import datetime, timezone, timedelta


from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ptz_controller import PTZController
from database import init_db
from detector import detect_objects
from command_controller import parse_command, execute_command
# from lidar_service import read_lidar
# from lidar_processing import cluster_lidar
# from fusion_engine import fuse
from services.camera_selector import select_best_camera, initialize_camera_orientations
from behavior import check_loitering, check_intrusion
from commands.parser import parse_command
from commands.validator import validate_command
from commands.dispatcher import dispatch_command
from services.tracking_service import tracking_sessions
from services.geo_service import calculate_bearing
from camera_health import camera_health, HEALTH_TIMEOUT
streams = {}
PTZ_MODE = "simulation"
PTZ_LIMITS = {
    "pan": (-90, 90),
    "tilt": (-45, 45),
    "zoom": (0, 10)
}


os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp|max_delay;0"

BASE_DIR = Path(__file__).resolve().parent
CAMERAS_FILE = BASE_DIR / "cameras.json"

app = FastAPI()
app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static"
)
print("STATIC PATH:", os.path.abspath("static"))

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

    # 🔥 Safety check (VERY IMPORTANT)
    if not cameras:
        print("[WARN] No cameras found, initializing empty list")
        cameras = []

    # 🔥 Ensure all cameras have required metadata
    for cam in cameras:
        if "position" not in cam:
            cam["position"] = {"x": 0.0, "y": 0.0, "z": 0.0}

        if "orientation" not in cam:
            cam["orientation"] = {"pan": 0.0, "tilt": 0.0, "zoom": 1.0}

        if "fov" not in cam:
            cam["fov"] = 90.0

        if "status" not in cam:
            cam["status"] = "active"

    print(f"[INFO] Loaded {len(cameras)} cameras with metadata")

    # 🔥 CRITICAL FIX → RETURN
    return cameras

cameras = load_cameras()

initialize_camera_orientations(cameras)
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

        self.frame = None
        self.raw_frame = None

        self.running = True
        self.lock = threading.Lock()

        # 🔥 Recording settings
        self.recording = True
        self.writer = None
        self.current_file = None
        self.last_rotation = time.time()
        self.last_frame_time = time.time()

        self.record_duration = 600  # 🔥 change to 10 for testing

        self.width = 960
        self.height = 540

        self.connect()
        self.start_new_recording()

        threading.Thread(target=self.update, daemon=True).start()

    # =========================
    # CONNECT CAMERA
    # =========================
    def connect(self):
        if self.cap:
            self.cap.release()

        url = build_rtsp_url(self.cam)
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ok, frame = self.cap.read()

        if ok:
            self.height, self.width = frame.shape[:2]
            self.raw_frame = frame
            print(f"[INFO] Connected camera {self.cam['id']} ({self.width}x{self.height})")
        else:
            self.cap = None
            print(f"[ERROR] Failed to connect camera {self.cam['id']} → {url}")

        print(f"[RTSP] {url}")

        if ok:
            camera_health[self.cam["id"]] = {
                "last_seen": time.time(),
                "status": "active"
            }
        else:
            camera_health[self.cam["id"]] = {
                "status": "inactive",
                "reason": "Connection failed"
            }

    # =========================
    # START RECORDING FILE
    # =========================
    def start_new_recording(self):
        try:
            folder = f"recordings/cam_{self.cam['id']}"
            os.makedirs(folder, exist_ok=True)

            filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.avi")
            path = os.path.join(folder, filename)

            fourcc = cv2.VideoWriter_fourcc(*'XVID')

            self.writer = cv2.VideoWriter(
                path,
                fourcc,
                20.0,
                (self.width, self.height)
            )

            if not self.writer.isOpened():
                print("[ERROR] VideoWriter failed")
                self.writer = None
                return

            self.current_file = path
            self.last_rotation = time.time()

            print(f"[REC] Recording started: {path}")

        except Exception as e:
            print("[REC ERROR]", e)
            self.writer = None
    # =========================
    # UPDATE LOOP
    # =========================
    def update(self):
        while self.running:
            if not self.running:
                break
            if not self.cap or not self.cap.isOpened():
                self.connect()
                time.sleep(0.5)
                continue

            try:
                self.cap.grab()
                ret, frame = self.cap.read()
            except Exception as e:
                print(f"[STREAM ERROR] Camera {self.cam['id']}:", e)
                self.connect()
                continue

            if ret:
                frame = cv2.resize(frame, (self.width, self.height))
                self.raw_frame = frame
                self.last_frame_time = time.time()

                camera_health[self.cam["id"]] = {
                    "last_seen": time.time(),
                    "status": "active"
                }

                # 🔥 WRITE FRAME
                if self.recording and self.writer:
                    try:
                        self.writer.write(frame)
                    except Exception as e:
                        print("[WRITE ERROR]", e)

                # 🔥 ROTATE FILE
                if self.recording:
                    if time.time() - self.last_rotation > self.record_duration:
                        self.start_new_recording()

            else:
                camera_health[self.cam["id"]] = {
                    "last_seen": camera_health.get(self.cam["id"], {}).get("last_seen", 0),
                    "status": "inactive",
                    "reason": "Frame read failed"
                }

                self.connect()

            time.sleep(0.03)

    # =========================
    # READ FRAME
    # =========================
    def read(self):
        return None if self.raw_frame is None else self.raw_frame.copy()

    # =========================
    # STOP STREAM
    # =========================
    def stop(self):
        print(f"[STOP] Camera {self.cam['id']} stopping...")

        self.running = False

        time.sleep(0.2)

        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
        except Exception as e:
            print("[STOP ERROR]", e)

        try:
            if self.writer:
                self.writer.release()
        except Exception:
            pass

        self.cap = None

        print(f"[INFO] Camera {self.cam['id']} stopped")
# ---------------- STREAM MANAGER ----------------
def init_streams():
    global streams

    old_streams = streams.copy()
    new_ids = {cam["id"] for cam in cameras}

    # stop removed
    for cam_id in list(old_streams.keys()):
        if cam_id not in new_ids:
            if hasattr(old_streams[cam_id], "stop"):
                old_streams[cam_id].stop()
                del old_streams[cam_id]

    streams = old_streams

    # start new
    for cam in cameras:
        if cam["id"] not in streams:
            streams[cam["id"]] = CameraStream(cam)

def validate_camera_connection(cam):
    url = build_rtsp_url(cam)

    print(f"[VALIDATE RTSP] {url}")

    # -------------------------------
    # 1. CHECK IP REACHABILITY
    # -------------------------------
    try:
        socket.create_connection((cam["ip"], 554), timeout=2)
    except Exception:
        return False, "Camera not reachable (wrong IP or offline)"

    # -------------------------------
    # 2. TRY RTSP CONNECTION
    # -------------------------------
    try:
        cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return False, "Invalid username or password"

        return True, "OK"

    except Exception as e:
        msg = str(e)

        if "401" in msg:
            return False, "Unauthorized (wrong username or password)"
        if "403" in msg:
            return False, "Access denied by camera"

        return False, "RTSP connection failed"

# ---------------- AI ----------------
def ai_worker():
    while True:
        for cam_id, stream in list(streams.items()):
            frame = stream.raw_frame

            if frame is None:
                continue

            # =========================
            # 1. DETECTION
            # =========================
            try:
                processed_frame, detections, alert = detect_objects(frame, cam_id)
            except Exception as e:
                print("[AI ERROR]", e)
                continue

            # =========================
            # 2. FILTER PERSONS (SAFE)
            # =========================
            persons = []

            for det in detections:
                try:
                    if det.get("label") == "person":
                        persons.append(det)
                except Exception:
                    continue

            # =========================
            # 3. GET TARGET
            # =========================
            target = None

            if persons:
                try:
                    x1, y1, x2, y2 = persons[0]["bbox"]

                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2

                    target = {
                        "x": cx / 100,
                        "y": cy / 100,
                        "z": 0
                    }
                except Exception as e:
                    print("[TARGET ERROR]", e)

            # =========================
            # 4. BEHAVIOR LOGIC
            # =========================
            final_alert = alert

            if target:
                try:
                    if check_intrusion([target["x"], target["y"], 0]):
                        final_alert = "🚨 INTRUSION DETECTED"

                    if check_loitering(cam_id, [target["x"], target["y"], 0]):
                        final_alert = "⚠️ LOITERING DETECTED"
                except Exception as e:
                    print("[BEHAVIOR ERROR]", e)

            # =========================
            # 5. STORE RESULTS
            # =========================
            with state_lock:
                results[cam_id] = {
                    "objects": detections,
                    "alert": final_alert,
                    "frame": processed_frame
                }

        time.sleep(0.01)

# def lidar_worker():
#    global lidar_objects

#    while True:
#        try:
#            points = read_lidar()
#            lidar_objects = cluster_lidar(points)
#        except Exception as e:
#            print("[LIDAR ERROR]", e)

#       time.sleep(0.1) 
        
# ---------------- FRAME ----------------
def render_frame(cam_id):
    stream = streams.get(cam_id)

    if not stream or stream.raw_frame is None:
        blank = np.ones((360, 640, 3), dtype=np.uint8) * 255
        cv2.putText(blank, "NO SIGNAL", (180, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        _, buffer = cv2.imencode(".jpg", blank)
        return buffer.tobytes()

    with state_lock:
        data = results.get(cam_id)

    if data and "frame" in data:
        frame = data["frame"]
    else:
        frame = stream.raw_frame.copy() if stream.raw_frame is not None else None

    _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    return buffer.tobytes()

def to_ist(timestamp):
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone(ist).strftime("%Y-%m-%d %H:%M:%S")

def classify_camera_health():
    active = []
    inactive = []

    now = time.time()

    for cam in cameras:
        cam_id = cam["id"]

        health = camera_health.get(cam_id)

        if not health:
            inactive.append({
                "camera_id": cam_id,
                "status": "inactive",
                "reason": "No data yet"
            })
            continue

        last_seen = health.get("last_seen", 0)

        if now - last_seen <= HEALTH_TIMEOUT:
            active.append({
                "camera_id": cam_id,
                "status": "active",
                "last_seen_ist": to_ist(last_seen)
            })
        else:
            inactive.append({
                "camera_id": cam_id,
                "status": "inactive",
                "reason": "Timeout"
            })

    return active, inactive

def calculate_ptz(camera, target):

    position = camera["position"]

    pan = calculate_bearing(

        position["latitude"],
        position["longitude"],

        target["latitude"],
        target["longitude"]
    )

    return {

        "pan": round(pan, 2),

        "tilt": 0
    }

class Position(BaseModel):

    latitude: float

    longitude: float

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

class PointRequest(BaseModel):

    latitude: float

    longitude: float

class CommandRequest(BaseModel):
    command: str
    mode: str = "auto"

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

@app.get("/camera-health")
def camera_health_api():
    active, inactive = classify_camera_health()

    return {
        "total_cameras": len(cameras),
        "active_count": len(active),
        "inactive_count": len(inactive),
        "active_cameras": active,
        "inactive_cameras": inactive
    }


@app.post("/add_camera")
async def add_camera(req: CameraCreate):
    cams = load_camera_store()

    # -------------------------------
    # DUPLICATE CHECK
    # -------------------------------
    for cam in cams:
        if cam["ip"] == req.ip:
            raise HTTPException(status_code=400, detail="Camera already exists")

    # -------------------------------
    # TEMP CAMERA FOR VALIDATION
    # -------------------------------
    temp_cam = {
        "id": -1,
        "ip": req.ip,
        "username": req.username,
        "password": req.password,
        "rtsp_url": getattr(req, "rtsp_url", "")
    }

    # -------------------------------
    # VALIDATE CONNECTION (CRITICAL)
    # -------------------------------
    is_valid, message = validate_camera_connection(temp_cam)

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=message
        )

    # -------------------------------
    # CREATE CAMERA
    # -------------------------------
    new_id = max([c["id"] for c in cams], default=0) + 1

    cam = {
        "id": new_id,
        "name": req.name,
        "ip": req.ip,
        "username": req.username,
        "password": req.password,

        # 🔥 OPTIONAL RTSP SUPPORT
        "rtsp_url": getattr(req, "rtsp_url", ""),

        # 🔥 METADATA
        "position": {

            "latitude":
            req.position.latitude,
            "longitude":
            req.position.longitude
        },
        "orientation": {
            "pan": req.orientation.pan,
            "tilt": req.orientation.tilt,
            "zoom": req.orientation.zoom
        },
        "fov": req.fov
    }

    # -------------------------------
    # SAVE
    # -------------------------------
    cams.append(cam)
    save_camera_store(cams)

    cameras.append(cam)

    try:
        init_streams()
    except Exception as e:
        print("[STREAM INIT ERROR]", e)

    return {
        "status": "added",
        "camera": cam
    }


@app.post("/delete_camera")
async def delete_camera(req: DeleteRequest):
    cam_id = req.id

    cams = [c for c in load_camera_store() if c["id"] != cam_id]
    save_camera_store(cams)

    global cameras
    cameras = cams
    init_streams()

    return {"status": "deleted"}

@app.get("/history/{camera_id}")
def get_history(camera_id: int):
    folder = f"recordings/cam_{camera_id}"

    if not os.path.exists(folder):
        return []

    files = sorted(os.listdir(folder), reverse=True)

    return files

@app.get("/history/{camera_id}/{filename}")
def get_video(camera_id: int, filename: str):
    path = f"recordings/cam_{camera_id}/{filename}"

    if not os.path.exists(path):
        raise HTTPException(404, "File not found")

    return FileResponse(path, media_type="video/avi")

@app.post("/point")
async def point_api(data: PointRequest):

    try:

        target = {

            "latitude": data.latitude,

            "longitude": data.longitude
        }

        # -----------------------------
        # VALIDATION
        # -----------------------------

        if not cameras:

            raise HTTPException(

                status_code=400,

                detail="No cameras available"
            )

        # -----------------------------
        # AUTO CAMERA SELECTION
        # -----------------------------

        selected_cam = select_best_camera(

            cameras,

            target
        )

        if not selected_cam:

            raise HTTPException(

                status_code=404,

                detail="No suitable camera found"
            )

        # -----------------------------
        # PTZ CALCULATION
        # -----------------------------

        ptz = calculate_ptz(

            selected_cam,

            target
        )

        print(f"""

===== GIS CAMERA SELECTION =====

Selected Camera:
{selected_cam['id']}

Target:
{target}

Pan:
{ptz['pan']}°

Tilt:
{ptz['tilt']}°

================================

""")

        return {

            "status": "camera_selected",

            "camera_id":
            selected_cam["id"],

            "camera_name":
            selected_cam.get("name"),

            "stream_url":
            selected_cam.get(
                "stream_url"
            ),

            "ptz": ptz,

            "target": target
        }

    except Exception as e:

        print("[ERROR /point]", e)

        raise HTTPException(

            status_code=500,

            detail=str(e)
        )

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
    
@app.get("/tracking")
def get_tracking():

    return tracking_sessions

@app.post("/command")
async def command_api(req: CommandRequest):

    try:

        parsed = parse_command(req.command)

        validate_command(parsed, cameras)

        result = dispatch_command(
            parsed,
            cameras
        )

        return result

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
    
@app.post("/discover-cameras")
def discover():
    from camera_discovery import auto_discover_and_register
    auto_discover_and_register()
    return {"status": "discovery completed"}

@app.post("/athena/ptztest")
async def ptz_test(data: dict):
    try:
        camera_id = data.get("camera_id")
        pan = data.get("pan", 0)
        tilt = data.get("tilt", 0)
        zoom = data.get("zoom", 1)

        # 🔍 Find camera
        cam = next((c for c in cameras if c["id"] == camera_id), None)

        if not cam:
            raise HTTPException(404, "Camera not found")

        cam_type = cam.get("type", "fixed")

        # =========================
        # VALIDATION
        # =========================
        if not (PTZ_LIMITS["pan"][0] <= pan <= PTZ_LIMITS["pan"][1]):
            raise HTTPException(400, "Pan out of range (-90 to 90)")

        if not (PTZ_LIMITS["tilt"][0] <= tilt <= PTZ_LIMITS["tilt"][1]):
            raise HTTPException(400, "Tilt out of range (-45 to 45)")

        if not (PTZ_LIMITS["zoom"][0] <= zoom <= PTZ_LIMITS["zoom"][1]):
            raise HTTPException(400, "Zoom out of range (0 to 10)")

        # =========================
        # FIXED CAMERA BEHAVIOR
        # =========================
        if cam_type == "fixed":
            return {
                "camera_id": camera_id,
                "status": "fixed_camera",
                "message": "PTZ not supported",
                "ptz": cam.get("orientation", {"pan": 0, "tilt": 0, "zoom": 1}),
                "limits": PTZ_LIMITS
            }

        # =========================
        # PTZ CAMERA (FUTURE)
        # =========================
        else:
            # 🔥 Update internal state
            cam["orientation"]["pan"] = pan
            cam["orientation"]["tilt"] = tilt
            cam["orientation"]["zoom"] = zoom

            # 🔥 (Future) send ONVIF command here

            return {
                "camera_id": camera_id,
                "status": "moved",
                "ptz": {
                    "pan": pan,
                    "tilt": tilt,
                    "zoom": zoom
                },
                "limits": PTZ_LIMITS
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# 🔥 FIXED HOME
@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

# ---------------- START ----------------
@app.on_event("startup")
async def startup():
    load_cameras()
    init_streams()

    threading.Thread(target=ai_worker, daemon=True).start()
    #threading.Thread(target=lidar_worker, daemon=True).start()

@app.websocket("/ws/{cam_id}")
async def websocket_stream(websocket: WebSocket, cam_id: int):
    try:
        await websocket.accept()
    except Exception:
        return  # 🔥 prevents crash if already closed

    try:
        while True:
            stream = streams.get(cam_id)

            if not stream or stream.raw_frame is None:
                await asyncio.sleep(0.1)
                continue

            frame = stream.raw_frame.copy()

            with state_lock:
                data = results.get(cam_id, {"objects": [], "alert": False})
                objs = data.get("objects", [])
                alert = data.get("alert", False)

            for obj in objs:
                try:
                    x1, y1, x2, y2 = obj["bbox"]
                    label = obj.get("label", "obj")

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                (0, 255, 0), 2)
                except:
                    continue

            if alert:
                cv2.putText(frame, "PERSON MOVEMENT DETECTED",
                            (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1,
                            (0, 0, 255),
                            3)

            success, buffer = cv2.imencode(
                ".jpg", frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 75]
            )

            if not success:
                continue

            jpg = base64.b64encode(buffer).decode("utf-8")

            try:
                await websocket.send_text(jpg)
            except Exception:
                break  # 🔥 exit loop cleanly

            await asyncio.sleep(0.08)  # 🔥 reduce load (~12 FPS)

    except WebSocketDisconnect:
        print(f"[INFO] WS disconnected cam {cam_id}")

    except Exception as e:
        print(f"[WS ERROR] cam {cam_id}:", e)


async def handle_focus_command(command):
    import re

    target_type = None
    camera_id = None

    if "person" in command:
        target_type = "person"

    match = re.search(r"camera\s*(\d+)", command)
    if match:
        camera_id = int(match.group(1))

    if not target_type:
        return {"status": "error", "message": "No target specified"}

    if camera_id is None:
        return {"status": "error", "message": "No camera specified"}

    # 🔥 GET STREAM
    stream = streams.get(camera_id)

    if not stream:
        return {"status": "error", "message": f"Camera {camera_id} not active"}

    frame = stream.read()

    if frame is None:
        return {"status": "error", "message": "No frame from camera"}

    # 🔥 DETECTION
    try:
        from detector import detect_objects
        detections = detect_objects(frame, camera_id, return_targets=True)
    except Exception as e:
        return {"status": "error", "message": f"Detection failed: {str(e)}"}

    if not detections:
        return {"status": "no target found"}

    target = detections[0]

    from services.camera_selector import select_best_camera
    selected_cam = select_best_camera(cameras, target)

    if not selected_cam:
        return {"status": "error", "message": "No suitable camera found"}

    return {
        "status": "focused",
        "camera_id": selected_cam["id"],
        "target": target
    }