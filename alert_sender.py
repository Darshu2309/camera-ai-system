import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = EMAIL_SENDER


def send_email_alert(image_path, camera_id):
    image_path = Path(image_path)

    msg = EmailMessage()
    msg["Subject"] = f"Alert - Camera {camera_id}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content(f"Motion detected on Camera {camera_id}")

    with image_path.open("rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="image",
            subtype="jpeg",
            filename=image_path.name,
        )

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("Email sent")
    except Exception as e:
        print("EMAIL ERROR:", e)
