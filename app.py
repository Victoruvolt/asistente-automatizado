import os
import openai
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Cargar variables de entorno
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Webhook para manejar mensajes de WhatsApp."""
    body = request.form.get("Body")  # Mensaje recibido
    response = MessagingResponse()

    try:
        # Llamar al modelo GPT con la nueva API
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente de trabajo."},
                {"role": "user", "content": body}
            ]
        )
        respuesta_gpt = completion['choices'][0]['message']['content']
        response.message(f"Asistente: {respuesta_gpt}")
    except Exception as e:
        response.message(f"Error procesando la solicitud: {str(e)}")
    
    return str(response)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
