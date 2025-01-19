from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from PyPDF2 import PdfReader
import os
import openai
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Manejar mensajes y archivos recibidos de WhatsApp."""
    incoming_msg = request.form.get("Body")
    media_url = request.form.get("MediaUrl0")
    media_type = request.form.get("MediaContentType0")
    response = MessagingResponse()
    message = response.message()

    try:
        if media_url and media_type == "application/pdf":
            # Descargar y procesar el PDF
            pdf_response = requests.get(media_url)
            pdf_path = "/tmp/archivo_recibido.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_response.content)

            reader = PdfReader(pdf_path)
            contenido_pdf = ""
            for page in reader.pages:
                contenido_pdf += page.extract_text()

            # Usar OpenAI para analizar el PDF
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": contenido_pdf}],
            )
            respuesta = completion.choices[0].message.content
            message.body(f"Resumen del PDF: {respuesta}")
        elif media_url and media_type.startswith("audio/"):
            # Descargar y transcribir el audio
            audio_response = requests.get(media_url)
            audio_path = "/tmp/audio_recibido.mp3"
            with open(audio_path, "wb") as f:
                f.write(audio_response.content)

            audio_file = open(audio_path, "rb")
            transcript = openai.Audio.transcribe("whisper-1", audio_file)
            message.body(f"Transcripción del audio: {transcript['text']}")
        else:
            # Procesar texto entrante
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": incoming_msg}],
            )
            respuesta = completion.choices[0].message.content
            message.body(respuesta)
    except Exception as e:
        message.body(f"Error procesando la solicitud: {e}")
    return str(response)

if __name__ == "__main__":
    app.run(debug=True)
