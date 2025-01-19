import os
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.cloud import speech_v1p1beta1 as speech
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import openai
import requests
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
NGROK_URL = os.getenv("NGROK_URL")

# Configurar OpenAI
openai.api_key = OPENAI_API_KEY

# Iniciar Flask
app = Flask(__name__)

# Procesar audios con Google Speech-to-Text
def transcribir_audio(ruta_audio):
    client = speech.SpeechClient()
    with open(ruta_audio, "rb") as audio_file:
        content = audio_file.read()
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        language_code="es-ES",
    )
    response = client.recognize(config=config, audio=audio)
    return " ".join([result.alternatives[0].transcript for result in response.results])

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Manejar mensajes y audios entrantes de WhatsApp."""
    try:
        incoming_msg = request.form.get("Body").strip().lower()
        media_url = request.form.get("MediaUrl0")
        response = MessagingResponse()
        msg = response.message()

        # Si recibe un audio
        if media_url and "audio" in request.form.get("MediaContentType0", ""):
            ruta_audio = "/tmp/audio.ogg"
            audio_data = requests.get(media_url).content
            with open(ruta_audio, "wb") as f:
                f.write(audio_data)
            texto_transcrito = transcribir_audio(ruta_audio)
            respuesta_openai = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": texto_transcrito}],
            )
            respuesta = respuesta_openai["choices"][0]["message"]["content"]
            msg.body(f"Audio recibido. Transcripción: {texto_transcrito}\nRespuesta: {respuesta}")
        else:
            # Responder texto o manejar solicitudes
            if "crear evento" in incoming_msg:
                msg.body("Por favor, indícame la fecha, hora y descripción del evento.")
            elif "normativa" in incoming_msg:
                msg.body("¿Qué aspecto de la normativa necesitas consultar?")
            elif "materiales" in incoming_msg:
                msg.body("¿Qué tipo de materiales necesitas consultar?")
            elif "cargadores" in incoming_msg:
                msg.body("¿Qué tipo de cargadores o instalaciones necesitas consultar?")
            else:
                respuesta_openai = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": incoming_msg}],
                )
                respuesta = respuesta_openai["choices"][0]["message"]["content"]
                msg.body(f"Respuesta: {respuesta}")

        return str(response)
    except Exception as e:
        return f"Error procesando la solicitud: {e}", 500

# Run Flask
if __name__ == "__main__":
    app.run(debug=True)
