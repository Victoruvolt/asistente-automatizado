import os
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.cloud import speech_v1p1beta1 as speech
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import openai
import requests

# Cargar variables de entorno
load_dotenv()

# Variables de entorno necesarias
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BILLAGE_API_KEY = os.getenv("BILLAGE_API_KEY")
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
NGROK_URL = os.getenv("NGROK_URL")

# Configurar OpenAI
openai.api_key = OPENAI_API_KEY

# Inicializar Flask
app = Flask(__name__)

# Rutas y lógica del asistente
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Manejar mensajes de WhatsApp."""
    try:
        body = request.form.get("Body")
        media_url = request.form.get("MediaUrl0")
        from_number = request.form.get("From")

        response_text = ""

        # Si hay un archivo de audio
        if media_url:
            audio_response = requests.get(media_url)
            audio_file_path = "/tmp/audio.ogg"

            with open(audio_file_path, "wb") as f:
                f.write(audio_response.content)

            response_text = transcribir_audio(audio_file_path)
        elif body:
            response_text = procesar_mensaje_texto(body)
        else:
            response_text = "Lo siento, no entendí tu mensaje."

        # Responder al usuario
        twilio_response = MessagingResponse()
        twilio_response.message(response_text)
        return str(twilio_response)

    except Exception as e:
        return f"Error procesando la solicitud: {str(e)}", 500

def procesar_mensaje_texto(mensaje):
    """Procesar mensajes de texto y generar respuestas con OpenAI."""
    try:
        completions = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": mensaje}],
        )
        return completions.choices[0].message.content
    except Exception as e:
        return f"Error al procesar el mensaje: {str(e)}"

def transcribir_audio(archivo_audio):
    """Transcribir un archivo de audio usando Google Cloud Speech-to-Text."""
    client = speech.SpeechClient()

    with open(archivo_audio, "rb") as audio_file:
        audio_content = audio_file.read()

    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        sample_rate_hertz=16000,
        language_code="es-ES",
    )

    response = client.recognize(config=config, audio=audio)
    for result in response.results:
        return result.alternatives[0].transcript

    return "No se pudo transcribir el audio."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
