<<<<<<< HEAD
import os
from flask import Flask, request, jsonify
from twilio.rest import Client
from PyPDF2 import PdfReader
from google.cloud import speech
import openai

# Inicialización de la app Flask
app = Flask(__name__)

# Variables de entorno
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NGROK_URL = os.getenv("NGROK_URL")

# Configuración de Twilio y OpenAI
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
openai.api_key = OPENAI_API_KEY

# Función para enviar mensajes de WhatsApp
def enviar_mensaje_whatsapp(destinatario, mensaje):
    try:
        twilio_client.messages.create(
            from_=f"whatsapp:{TWILIO_WHATSAPP_NUMBER}",
            to=f"whatsapp:{destinatario}",
            body=mensaje
        )
    except Exception as e:
        print(f"Error enviando mensaje: {str(e)}")

# Leer PDF
def leer_pdf(ruta_pdf):
    try:
        reader = PdfReader(ruta_pdf)
        texto = "".join(page.extract_text() for page in reader.pages)
        return texto
    except Exception as e:
        return f"Error leyendo el PDF: {str(e)}"

# Procesar audio
def procesar_audio(ruta_audio):
    client = speech.SpeechClient()
    try:
        with open(ruta_audio, "rb") as audio_file:
            audio_content = audio_file.read()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="es-ES",
        )

        response = client.recognize(config=config, audio=audio)
        return "\n".join(result.alternatives[0].transcript for result in response.results)
    except Exception as e:
        return f"Error procesando audio: {str(e)}"

# Webhook de WhatsApp
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        mensaje = request.values.get("Body", "").lower()
        remitente = request.values.get("From", "")

        if "pdf" in mensaje:
            respuesta = "Por favor envía un archivo PDF."
        elif "audio" in mensaje:
            respuesta = "Por favor envía un archivo de audio."
        else:
            respuesta = "No entendí tu mensaje. Intenta con 'pdf' o 'audio'."

        enviar_mensaje_whatsapp(remitente, respuesta)
        return "OK", 200
    except Exception as e:
        return f"Error en el webhook: {str(e)}", 500

# Ruta de prueba
@app.route("/prueba", methods=["GET"])
def prueba():
    return jsonify({"status": "funcionando correctamente"})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
=======
from flask import Flask, request, jsonify
from utils.whatsapp import send_whatsapp_message, process_whatsapp_message
from utils.pdf_processing import read_pdf
from utils.calendar import create_event, list_events
from utils.email_manager import send_email, read_email
from utils.normativa import get_laboral_guidelines
from utils.mobility import recommend_chargers, vehicle_info
import os

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        message = data.get("Body", "").strip().lower()

        if "pdf" in message:
            response = read_pdf("example.pdf")  # Cambia esto con la ruta del PDF
        elif "calendario" in message:
            response = list_events()
        elif "correo" in message:
            response = read_email()
        elif "normativa" in message:
            response = get_laboral_guidelines()
        elif "movilidad" in message:
            response = recommend_chargers("ejemplo")
        else:
            response = "¡Hola! ¿En qué puedo ayudarte? Escribe 'ayuda' para ver las opciones disponibles."

        # Enviar respuesta por WhatsApp
        send_whatsapp_message(response)
        return jsonify({"status": "success", "response": response})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

if __name__ == "__main__":
    app.run(debug=True)
>>>>>>> 8227ead (Asistente completo y funcional)
