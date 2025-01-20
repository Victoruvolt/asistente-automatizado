import os
from flask import Flask, request, jsonify
from twilio.rest import Client
from PyPDF2 import PdfReader
from google.cloud import speech
import openai
import requests

# Inicialización de la app Flask
app = Flask(__name__)

# Cargar variables de entorno
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BILLAGE_API_KEY = os.getenv("BILLAGE_API_KEY")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
NGROK_URL = os.getenv("NGROK_URL")

# Inicializar clientes
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
openai.api_key = OPENAI_API_KEY

# Función para enviar mensajes de WhatsApp
def enviar_mensaje_whatsapp(destinatario, mensaje):
    try:
        message = twilio_client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:{destinatario}",
            body=mensaje
        )
        print(f"Mensaje enviado: SID {message.sid}")
    except Exception as e:
        print(f"Error enviando mensaje de WhatsApp: {str(e)}")

# Procesar PDF
def leer_pdf(ruta_pdf):
    try:
        reader = PdfReader(ruta_pdf)
        texto = "".join(page.extract_text() for page in reader.pages)
        return texto
    except Exception as e:
        return f"Error al leer el PDF: {str(e)}"

# Webhook de WhatsApp
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        body = request.values.get("Body", "").lower()
        from_number = request.values.get("From", "")
        if "pdf" in body:
            respuesta = "Por favor envía un archivo PDF y lo procesaremos."
        elif "audio" in body:
            respuesta = "Por favor envía un archivo de audio y lo transcribiremos."
        else:
            respuesta = "No entendí tu mensaje. Intenta con 'pdf' o 'audio'."
        enviar_mensaje_whatsapp(from_number, respuesta)
        return "Mensaje recibido", 200
    except Exception as e:
        print(f"Error en el webhook: {str(e)}")
        return "Error procesando solicitud", 500

# Ruta de prueba
@app.route("/prueba", methods=["GET"])
def prueba():
    return jsonify({"status": "Asistente funcionando correctamente."})

# Inicio del servidor
if __name__ == "__main__":
    app.run(debug=True, port=5000)
