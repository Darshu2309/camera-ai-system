import smtplib
from email.message import EmailMessage
import os
import serial
import time

EMAIL_SENDER = "nsridarshan@gmail.com"
EMAIL_PASSWORD = "tjyc ujmu pfel vxeb"
EMAIL_RECEIVER = "nsridarshan@gmail.com"


def send_email_alert(image_path, camera_id):
    msg = EmailMessage()
    msg['Subject'] = f"🚨 Alert - Camera {camera_id}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    msg.set_content(f"Motion detected on Camera {camera_id}")

    # Attach image
    with open(image_path, 'rb') as f:
        img_data = f.read()
        msg.add_attachment(img_data, maintype='image', subtype='jpeg', filename=os.path.basename(image_path))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)
        print("📧 Email alert sent")
    except Exception as e:
        print("EMAIL ERROR:", e)