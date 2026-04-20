from twilio.rest import Client

# 🔑 Your Twilio credentials
ACCOUNT_SID = "AC547574ec1d28d11674e3b230ddb8898d"
AUTH_TOKEN = "6cec0813afbd6871c343feabdfa60a45"

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def send_whatsapp_alert(image_path, message="🚨 Person detected!"):
    try:
        msg = client.messages.create(
            from_='whatsapp:+14155238886',  # Twilio sandbox number
            body=message,
            to='whatsapp:+919398685917',    # YOUR number
            media_url=[f"https://abc123.ngrok.io/images/{image_path}"]
        )
        print("WhatsApp alert sent:", msg.sid)
    except Exception as e:
        print("WhatsApp error:", e)