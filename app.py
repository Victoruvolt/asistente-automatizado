import imaplib
import email
from email.header import decode_header
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.cloud import speech_v1p1beta1 as speech
from dotenv import load_dotenv
import requests
import openai
import os
from datetime import datetime, timedelta

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuración de Twilio
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Configuración de Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'service_account.json'
CALENDAR_ID = 'victoruvolt@gmail.com'

# Configuración de la API de Billage
BILLAGE_API_URL = "https://api.billage.net/v1/opportunities"
BILLAGE_API_KEY = os.getenv("BILLAGE_API_KEY")

# Configuración de IMAP para correos
IMAP_SERVER = os.getenv("IMAP_SERVER")
IMAP_USER = os.getenv("IMAP_USER")
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD")

# Inicializar Flask
app = Flask(__name__)

# Función para crear eventos en Google Calendar
def crear_evento(titulo, descripcion, fecha_inicio, fecha_fin):
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    evento = {
        'summary': titulo,
        'description': descripcion,
        'start': {
            'dateTime': fecha_inicio,
            'timeZone': 'Europe/Madrid',
        },
        'end': {
            'dateTime': fecha_fin,
            'timeZone': 'Europe/Madrid',
        },
    }

    try:
        evento_resultado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
        return evento_resultado.get('htmlLink')
    except Exception as e:
        return f"Error al crear el evento: {e}"

# Función para transcribir audios de WhatsApp
def transcribir_audio(audio_url):
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
        for result in response.results:
            return result.alternatives[0].transcript
    except Exception as e:
        return f"Error al transcribir el audio: {e}"

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Webhook para manejar mensajes de WhatsApp."""
    mensaje = request.form.get("Body")
    audio_url = request.form.get("MediaUrl0")
    sender = request.form.get("From")

    print(f"Mensaje recibido de {sender}: {mensaje or '[Audio recibido]'}")

    if audio_url:
        mensaje = transcribir_audio(audio_url)
        print(f"Transcripción del audio: {mensaje}")

    try:
        respuesta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que ayuda a gestionar tareas, agenda y correos."},
                {"role": "user", "content": mensaje}
            ]
        )
        interpretacion = respuesta['choices'][0]['message']['content']
        print(f"Interpretación de OpenAI: {interpretacion}")
    except Exception as e:
        interpretacion = f"Error al procesar la solicitud: {e}"

    response = MessagingResponse()

    if "crear evento" in interpretacion.lower():
        titulo = "Evento desde WhatsApp"
        descripcion = interpretacion
        ahora = datetime.now()
        fecha_inicio = ahora.strftime("%Y-%m-%dT%H:%M:%S+01:00")
        fecha_fin = (ahora + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+01:00")
        enlace = crear_evento(titulo, descripcion, fecha_inicio, fecha_fin)
        response.message(f"Evento creado con éxito: {enlace}")
    elif "agenda" in interpretacion.lower() or "qué tengo" in interpretacion.lower():
        response.message("Hoy tienes varios eventos programados. ¿Quieres que te los enumere?")
    else:
        response.message(f"No estoy seguro de lo que me pides. Esto fue lo que entendí: {interpretacion}")

    return str(response)

def leer_correos():
    """Conecta al servidor IMAP y lee correos no leídos."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, '(UNSEEN)')
        correos_ids = messages[0].split()

        for correo_id in correos_ids:
            status, data = mail.fetch(correo_id, "(RFC822)")
            for respuesta in data:
                if isinstance(respuesta, tuple):
                    mensaje = email.message_from_bytes(respuesta[1])
                    asunto = decode_header(mensaje["Subject"])[0][0]
                    if isinstance(asunto, bytes):
                        asunto = asunto.decode()
                    remitente = mensaje.get("From")
                    if mensaje.is_multipart():
                        for parte in mensaje.walk():
                            tipo_contenido = parte.get_content_type()
                            if tipo_contenido == "text/plain":
                                cuerpo = parte.get_payload(decode=True).decode()
                                procesar_solicitud(asunto, remitente, cuerpo)
                    else:
                        cuerpo = mensaje.get_payload(decode=True).decode()
                        procesar_solicitud(asunto, remitente, cuerpo)

        mail.logout()
    except Exception as e:
        print(f"Error al leer correos: {e}")

def procesar_solicitud(asunto, remitente, cuerpo):
    """Procesa la solicitud y crea una oportunidad en Billage."""
    if "presupuesto" in asunto.lower():
        crear_oportunidad(asunto, remitente, cuerpo)

def crear_oportunidad(asunto, remitente, descripcion):
    """Crea una oportunidad en Cegid Billage."""
    headers = {
        "Authorization": f"Bearer {BILLAGE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": f"Oportunidad: {asunto}",
        "description": descripcion,
        "client_email": remitente
    }

    try:
        response = requests.post(BILLAGE_API_URL, json=payload, headers=headers)
        if response.status_code == 201:
            print("Oportunidad creada con éxito en Billage.")
        else:
            print(f"Error al crear oportunidad: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error al conectar con Billage: {e}")

if __name__ == "__main__":
    app.run(port=5000, debug=True)
