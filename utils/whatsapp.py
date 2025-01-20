from twilio.rest import Client
import os

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

def send_whatsapp_message(message):
    to = "whatsapp:+XXXXXXXXXXXX"  # Cambia al número de destino
    client.messages.create(
        from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
        to=to,
        body=message
    )

def process_whatsapp_message(data):
    # Aquí puedes procesar mensajes entrantes de WhatsApp
    return f"Mensaje recibido: {data}"
