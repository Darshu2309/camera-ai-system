from fastapi import FastAPI, UploadFile, File, Form
import os
import time
from database import insert_image, init_db, get_all_images
from alert_sender import send_email_alert
import threading

app = FastAPI()

# init DB
init_db()

SAVE_DIR = "images"
os.makedirs(SAVE_DIR, exist_ok=True)


@app.post("/alert")
async def receive_alert(
    file: UploadFile = File(...),
    camera_id: int = Form(...)
):
    try:
        print("ALERT RECEIVED")

        # 📁 camera folder
        cam_folder = os.path.join(SAVE_DIR, f"camera_{camera_id}")
        os.makedirs(cam_folder, exist_ok=True)

        filename = f"alert_{camera_id}_{int(time.time())}.jpg"
        file_path = os.path.join(cam_folder, filename)

        # 💾 save image
        with open(file_path, "wb") as f:
            f.write(await file.read())

        print(f"Saved: {file_path}")
        threading.Thread(
            target=send_email_alert,
            args=(file_path, camera_id)
        ).start()

        # 🧠 basic info
        labels = "person"
        count = 1

        # 🗃️ save to PostgreSQL
        insert_image(camera_id, file_path, labels, count)

        return {"status": "saved"}

    except Exception as e:
        print("ERROR:", e)
        return {"error": str(e)}


# 🔍 fetch images
@app.get("/images")
def get_images():
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

    return {"data": data}