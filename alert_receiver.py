from fastapi import FastAPI, UploadFile, File, Form
import shutil
import time
from drive_upload import upload_to_drive
from fastapi.staticfiles import StaticFiles
from alert_sender import send_whatsapp_alert

app = FastAPI()
app.mount("/images", StaticFiles(directory="."), name="images")

@app.post("/alert")
async def receive_alert(
    file: UploadFile = File(...),
    camera_id: int = Form(...)
):
    print("ALERT RECEIVED")

    timestamp = int(time.time())
    filename = f"alert_{camera_id}_{timestamp}.jpg"

    with open(filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    print(f"Saved: {filename}")
    send_whatsapp_alert(f"images/{filename}")

    # 🔥 Upload to Drive in camera folder
    upload_to_drive(filename, filename, camera_id)

    return {"status": "ok"}