import os
import imaplib
import email
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.cloud import speech_v1p1beta1 as speech
from dotenv import load_dotenv
import openai
import requests
from datetime import datetime, timedelta

# Función para limpiar claves ofuscadas
def limpiar_clave(clave):
    if "prefix_" in clave and "_suffix" in clave:
        return clave.replace("prefix_", "").replace("_suffix", "")
    return clave

# Cargar variables de entorno y limpiar claves
load_dotenv()
OPENAI_API_KEY = limpiar_clave(os.getenv("OPENAI_API_KEY"))
BILLAGE_API_KEY = limpiar_clave(os.getenv("BILLAGE_API_KEY"))
IMAP_SERVER = limpiar_clave(os.getenv("IMAP_SERVER"))
IMAP_USER = limpiar_clave(os.getenv("IMAP_USER"))
IMAP_PASSWORD = limpiar_clave(os.getenv("IMAP_PASSWORD"))
TWILIO_WHATSAPP_NUMBER = limpiar_clave(os.getenv("TWILIO_WHATSAPP_NUMBER"))
TWILIO_ACCOUNT_SID = limpiar_clave(os.getenv("TWILIO_ACCOUNT_SID"))
TWILIO_AUTH_TOKEN = limpiar_clave(os.getenv("TWILIO_AUTH_TOKEN"))

# Configurar OpenAI
openai.api_key = OPENAI_API_KEY

# Configuración de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'service_account.json'
CALENDAR_ID = 'victoruvolt@gmail.com'

# Inicializar Flask
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Webhook para manejar mensajes de WhatsApp."""
    mensaje = request.form.get("Body")
    audio_url = request.form.get("MediaUrl0")
    sender = request.form.get("From")
    print(f"Mensaje recibido de {sender}: {mensaje or '[Audio recibido]'}")

    # Procesar audio si existe
    if audio_url:
        mensaje = transcribir_audio(audio_url)
        print(f"Transcripción del audio: {mensaje}")

    # Procesar solicitud con OpenAI
    respuesta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que ayuda a gestionar tareas, correos y eventos."},
            {"role": "user", "content": mensaje}
        ]
    )
    interpretacion = respuesta['choices'][0]['message']['content']
    print(f"Interpretación: {interpretacion}")

    # Responder con Twilio
    response = MessagingResponse()
    if "crear evento" in interpretacion.lower():
        titulo = "Evento desde WhatsApp"
        ahora = datetime.now()
        fecha_inicio = ahora.strftime("%Y-%m-%dT%H:%M:%S+01:00")
        fecha_fin = (ahora + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+01:00")
        enlace = crear_evento(titulo, interpretacion, fecha_inicio, fecha_fin)
        response.message(f"Evento creado: {enlace}")
    elif "presupuesto" in interpretacion.lower():
        crear_oportunidad(interpretacion, sender)
        response.message("Oportunidad creada en Billage.")
    else:
        response.message(f"No entendí completamente, esto fue lo que interpreté: {interpretacion}")
    return str(response)

def transcribir_audio(audio_url):
    """Transcribe un mensaje de voz recibido desde WhatsApp."""
    try:
        response = requests.get(audio_url)
        audio_content = response.content
        client = speech.SpeechClient()
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
            sample_rate_hertz=16000,
            language_code="es-ES",
        )
        response = client.recognize(config=config, audio=audio)
        return response.results[0].alternatives[0].transcript
    except Exception as e:
        return f"Error al transcribir el audio: {e}"

def crear_evento(titulo, descripcion, fecha_inicio, fecha_fin):
    """Crea un evento en Google Calendar."""
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    evento = {
        'summary': titulo,
        'description': descripcion,
        'start': {'dateTime': fecha_inicio, 'timeZone': 'Europe/Madrid'},
        'end': {'dateTime': fecha_fin, 'timeZone': 'Europe/Madrid'},
    }
    evento_resultado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
    return evento_resultado.get('htmlLink')

def crear_oportunidad(descripcion, remitente):
    """Crea una oportunidad en Billage."""
    headers = {"Authorization": f"Bearer {BILLAGE_API_KEY}"}
    payload = {"name": "Nueva oportunidad", "description": descripcion, "client_email": remitente}
    response = requests.post("https://api.billage.net/v1/opportunities", json=payload, headers=headers)
    return response.status_code == 201

if __name__ == "__main__":
    app.run(port=5000, debug=True)
