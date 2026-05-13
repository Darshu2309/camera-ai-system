from fastapi import FastAPI, UploadFile, File, Form
import os
import time
from database import insert_image, init_db, get_all_images

app = FastAPI()

# ---------------- INIT DATABASE ----------------
init_db()

# ---------------- CONFIG ----------------
SAVE_DIR = "images"
os.makedirs(SAVE_DIR, exist_ok=True)


# ---------------- ALERT RECEIVER ----------------
@app.post("/alert")
async def receive_alert(
    file: UploadFile = File(...),
    camera_id: int = Form(...)
):
    try:
        print(f"\n- ALERT RECEIVED from Camera {camera_id}")

        # 📁 Create camera folder
        cam_folder = os.path.join(SAVE_DIR, f"camera_{camera_id}")
        os.makedirs(cam_folder, exist_ok=True)

        # 📄 File name
        filename = f"alert_{camera_id}_{int(time.time())}.jpg"
        file_path = os.path.join(cam_folder, filename)

        # 💾 Save image
        with open(file_path, "wb") as f:
            f.write(await file.read())

        print(f"- Saved: {file_path}")

        # ---------------- BASIC METADATA ----------------
        labels = "person"   # 🔥 later dynamic from detector
        count = 1

        # ---------------- SAVE TO DATABASE ----------------
        insert_image(camera_id, file_path, labels, count)

        print("- Stored in PostgreSQL")

        return {
            "status": "saved",
            "camera_id": camera_id,
            "file_path": file_path
        }

    except Exception as e:
        print("❌ ERROR:", e)
        return {"error": str(e)}


# ---------------- FETCH ALL ALERTS ----------------
@app.get("/images")
def get_images():
    try:
        rows = get_all_images()

        data = []
        for r in rows:
            data.append({
                "id": r[0],
                "camera_id": r[1],
                "timestamp": str(r[2]),
                "file_path": r[3],
                "labels": r[4],
                "count": r[5]
            })

        return {
            "total": len(data),
            "data": data
        }

    except Exception as e:
        print("❌ FETCH ERROR:", e)
        return {"error": str(e)}


# ---------------- FETCH BY CAMERA ----------------
@app.get("/images/{camera_id}")
def get_images_by_camera(camera_id: int):
    try:
        rows = get_all_images()

        filtered = [
            {
                "id": r[0],
                "camera_id": r[1],
                "timestamp": str(r[2]),
                "file_path": r[3],
                "labels": r[4],
                "count": r[5]
            }
            for r in rows if r[1] == camera_id
        ]

        return {
            "camera_id": camera_id,
            "total": len(filtered),
            "data": filtered
        }

    except Exception as e:
        print("❌ FILTER ERROR:", e)
        return {"error": str(e)}


# ---------------- HEALTH CHECK ----------------
@app.get("/")
def health_check():
    return {"status": "alert server running"}