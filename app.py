import os
import traceback
import subprocess
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from PyPDF2 import PdfReader
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import openai
import speech_recognition as sr
from pydub import AudioSegment

# Cargar variables de entorno
load_dotenv()

# Configurar claves
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
SERVICE_ACCOUNT_FILE = "service_account.json"
CALENDAR_ID = os.getenv("CALENDAR_ID")

# Configurar OpenAI
openai.api_key = OPENAI_API_KEY

# Inicializar Flask
app = Flask(__name__)

# Configurar Google Calendar
SCOPES = ['https://www.googleapis.com/auth/calendar']
try:
    credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    calendar_service = build('calendar', 'v3', credentials=credentials)
except Exception as e:
    raise Exception(f"Error al configurar Google Calendar: {e}")

# Función para cargar el convenio del metal
def cargar_convenio(file_path):
    try:
        reader = PdfReader(file_path)
        texto_completo = ""
        for page in reader.pages:
            texto_completo += page.extract_text()
        return texto_completo
    except Exception as e:
        print(f"Error al cargar el convenio: {e}")
        return None

# Cargar el texto del Convenio
CONVENIO_METAL = cargar_convenio("convenio_metal_2023.pdf")
if not CONVENIO_METAL:
    print("Advertencia: No se pudo cargar el convenio. Verifica el archivo.")

# Bases de datos técnicas
NORMATIVA = {
    "sección de cable": "La sección mínima para una instalación doméstica es de 1.5 mm² para alumbrado y 2.5 mm² para enchufes según el REBT.",
    "protección diferencial": "El diferencial debe ser de 30mA para instalaciones domésticas.",
    "puesta a tierra": "La resistencia de la puesta a tierra debe ser inferior a 37 Ohms según el REBT.",
    "carga de vehículo eléctrico": "La instalación debe incluir un circuito exclusivo con una protección de 40A y un diferencial tipo A o tipo B.",
}

CARGADORES = {
    "wallbox": "Cargador Wallbox Pulsar Plus: Potencia de hasta 22kW, compatible con Tipo 2.",
    "schneider": "Cargador Schneider EVlink: Modelos de 7.4kW y 22kW, con opciones de conectividad avanzada.",
    "abb": "Cargador ABB Terra DC: Hasta 350kW para carga ultrarrápida.",
}

COCHES_ELECTRICOS = {
    "tesla model 3": "Batería de 60 kWh, autonomía de 491 km.",
    "renault zoe": "Batería de 52 kWh, autonomía de 395 km.",
    "kia e-niro": "Batería de 64 kWh, autonomía de 455 km.",
}

# Funciones de respuesta
def responder_tecnico(pregunta):
    for clave, respuesta in NORMATIVA.items():
        if clave in pregunta.lower():
            return respuesta
    return "No tengo información específica sobre eso. Por favor, consulta el REBT."

def responder_movilidad(pregunta):
    for clave, respuesta in {**CARGADORES, **COCHES_ELECTRICOS}.items():
        if clave in pregunta.lower():
            return respuesta
    return "No tengo información sobre ese cargador o coche. Por favor, revisa las especificaciones."

# Función para procesar audios
def procesar_audio(media_url):
    try:
        # Descargar el archivo de audio de WhatsApp
        audio_response = requests.get(media_url)
        with open("audio.ogg", "wb") as audio_file:
            audio_file.write(audio_response.content)

        # Convertir el audio a WAV
        audio = AudioSegment.from_file("audio.ogg", format="ogg")
        audio.export("audio.wav", format="wav")

        # Usar reconocimiento de voz
        recognizer = sr.Recognizer()
        with sr.AudioFile("audio.wav") as source:
            audio_data = recognizer.record(source)
            texto = recognizer.recognize_google(audio_data, language="es-ES")
        return texto

    except Exception as e:
        print(f"Error al procesar el audio: {e}")
        return None

# Webhook de WhatsApp
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    try:
        incoming_msg = request.form.get("Body", "").strip()
        media_url = request.form.get("MediaUrl0", None)
        response = MessagingResponse()
        message = response.message()

        # Procesar audios
        if media_url:
            texto_audio = procesar_audio(media_url)
            if texto_audio:
                incoming_msg = texto_audio
            else:
                message.body("❌ No pude entender el audio. Por favor, intenta nuevamente.")
                return str(response)

        # Consultar el convenio
        if "convenio" in incoming_msg.lower():
            respuesta = "Consulta general del convenio del metal: derechos laborales y permisos retribuidos."
            message.body(f"📜 {respuesta}")
            return str(response)

        # Responder preguntas técnicas
        if "cable" in incoming_msg.lower() or "protección" in incoming_msg.lower():
            respuesta = responder_tecnico(incoming_msg)
            message.body(f"🔧 Respuesta técnica: {respuesta}")
            return str(response)

        # Responder sobre movilidad eléctrica
        if "cargador" in incoming_msg.lower() or "coche" in incoming_msg.lower():
            respuesta = responder_movilidad(incoming_msg)
            message.body(f"🔋 Respuesta sobre movilidad eléctrica: {respuesta}")
            return str(response)

        # Mensaje predeterminado
        message.body("🤖 No estoy seguro de cómo responder. Intenta ser más específico.")
        return str(response)

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"Error procesando el webhook: {error_trace}")
        response = MessagingResponse()
        response.message(f"❌ Error: {e}")
        return str(response), 500

# Función para iniciar ngrok
def start_ngrok():
    try:
        subprocess.run(["ngrok", "authtoken", NGROK_AUTHTOKEN], check=True)
        ngrok_process = subprocess.Popen(["ngrok", "http", "5000"], stdout=subprocess.PIPE)
        print("ngrok iniciado...")
    except Exception as e:
        raise Exception(f"Error iniciando ngrok: {e}")

# Iniciar Flask y ngrok
if __name__ == "__main__":
    try:
        start_ngrok()
        app.run(debug=True, port=5000)
    except Exception as e:
        print(f"Error en el servidor principal: {e}")
