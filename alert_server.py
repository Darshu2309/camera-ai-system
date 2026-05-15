from pathlib import Path
import time
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile

from database import get_all_images, init_db, insert_image, insert_media_event


app = FastAPI()

# ---------------- INIT DATABASE ----------------
DB_READY = False


def try_init_db():
    global DB_READY
    try:
        init_db()
        DB_READY = True
        return True
    except Exception as e:
        DB_READY = False
        print("DB INIT WARNING:", e)
        return False


try_init_db()

# ---------------- CONFIG ----------------
BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "images" / ".alerts"
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def image_row_to_dict(row):
    return {
        "id": row[0],
        "camera_id": row[1],
        "timestamp": str(row[2]),
        "file_path": row[3],
        "labels": row[4],
        "count": row[5],
        "latitude": row[6] if len(row) > 6 else None,
        "longitude": row[7] if len(row) > 7 else None,
    }


# ---------------- ALERT RECEIVER ----------------
@app.post("/alert")
async def receive_alert(
    file: UploadFile = File(...),
    camera_id: int = Form(...),
    latitude: Optional[float] = Form(default=None),
    longitude: Optional[float] = Form(default=None),
):
    try:
        print(f"\n- ALERT RECEIVED from Camera {camera_id}")

        # Raw captures stay outside the public static tree. Operators should
        # search by DB metadata such as timestamp, camera, and map location.
        cam_folder = SAVE_DIR / f"camera_{camera_id}"
        cam_folder.mkdir(parents=True, exist_ok=True)

        filename = f"alert_{camera_id}_{int(time.time())}.jpg"
        file_path = cam_folder / filename

        with file_path.open("wb") as f:
            f.write(await file.read())

        print(f"- Saved: {file_path}")

        labels = "person"
        count = 1

        db_status = "stored"
        if not DB_READY:
            try_init_db()

        if DB_READY:
            try:
                insert_image(
                    camera_id,
                    file_path,
                    labels,
                    count,
                    latitude=latitude,
                    longitude=longitude,
                )
                insert_media_event(
                    camera_id=camera_id,
                    camera_name=f"Camera {camera_id}",
                    event_type="motion",
                    file_path=file_path,
                    latitude=latitude,
                    longitude=longitude,
                    confidence=None,
                    labels=labels,
                )
                print("- Stored in PostgreSQL")
            except Exception as e:
                db_status = "db_unavailable"
                print("DB STORE WARNING:", e)
        else:
            db_status = "db_unavailable"

        return {
            "status": "saved",
            "camera_id": camera_id,
            "file_path": str(file_path),
            "latitude": latitude,
            "longitude": longitude,
            "db_status": db_status,
        }

    except Exception as e:
        print("ERROR:", e)
        return {"error": str(e)}


# ---------------- FETCH ALL ALERTS ----------------
@app.get("/images")
def get_images():
    try:
        if not DB_READY:
            try_init_db()

        if not DB_READY:
            return {
                "total": 0,
                "data": [],
                "db_status": "db_unavailable",
            }

        rows = get_all_images()
        data = [image_row_to_dict(row) for row in rows]

        return {
            "total": len(data),
            "data": data,
            "db_status": "ok",
        }

    except Exception as e:
        print("FETCH ERROR:", e)
        return {"error": str(e)}


# ---------------- FETCH BY CAMERA ----------------
@app.get("/images/{camera_id}")
def get_images_by_camera(camera_id: int):
    try:
        if not DB_READY:
            try_init_db()

        if not DB_READY:
            return {
                "camera_id": camera_id,
                "total": 0,
                "data": [],
                "db_status": "db_unavailable",
            }

        rows = get_all_images()
        filtered = [
            image_row_to_dict(row)
            for row in rows
            if row[1] == camera_id
        ]

        return {
            "camera_id": camera_id,
            "total": len(filtered),
            "data": filtered,
            "db_status": "ok",
        }

    except Exception as e:
        print("FILTER ERROR:", e)
        return {"error": str(e)}


# ---------------- HEALTH CHECK ----------------
@app.get("/")
def health_check():
    return {
        "status": "alert server running",
        "db_status": "ok" if DB_READY else "db_unavailable",
    }
