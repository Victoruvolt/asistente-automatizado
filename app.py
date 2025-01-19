import os
import openai
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Cargar las variables del entorno
load_dotenv()

# Configurar OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Inicializar Flask
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Procesa los mensajes entrantes desde WhatsApp."""
    try:
        # Obtener el mensaje de WhatsApp
        mensaje = request.form.get("Body")
        numero_remitente = request.form.get("From")

        # Log del mensaje recibido
        print(f"Mensaje recibido de {numero_remitente}: {mensaje}")

        # Generar respuesta usando la nueva API de OpenAI
        respuesta_openai = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente automatizado que organiza calendarios y responde solicitudes."},
                {"role": "user", "content": mensaje},
            ],
            temperature=0.7
        )

        # Extraer la respuesta de OpenAI
        respuesta_texto = respuesta_openai["choices"][0]["message"]["content"]
        print(f"Respuesta generada por OpenAI: {respuesta_texto}")

        # Crear una respuesta para Twilio
        respuesta = MessagingResponse()
        respuesta.message(respuesta_texto)
        return str(respuesta)

    except Exception as e:
        print(f"Error procesando la solicitud: {str(e)}")
        respuesta = MessagingResponse()
        respuesta.message(f"Error procesando la solicitud: {str(e)}")
        return str(respuesta), 500


if __name__ == "__main__":
    app.run(debug=True)
