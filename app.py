# app.py - Asistente Integral
import os
import openai
import imaplib
import email
from flask import Flask, request, jsonify
from PyPDF2 import PdfReader
from twilio.twiml.messaging_response import MessagingResponse
import requests  # Para manejar la conexión con el CRM Billage

# Configuración de claves API y entorno
openai.api_key = os.getenv("OPENAI_API_KEY")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
billage_api_key = os.getenv("BILLAGE_API_KEY")

# Inicializar aplicación Flask
app = Flask(__name__)

# Clase para manejar el CRM Billage
class CRM:
    def __init__(self, api_key):
        self.api_url = "https://api.billage.com/v1/"  # Sustituye por la URL correcta de la API de Billage
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def crear_factura(self, cliente, concepto, cantidad):
        try:
            data = {
                "cliente": cliente,
                "concepto": concepto,
                "cantidad": cantidad
            }
            response = requests.post(
                f"{self.api_url}facturas", json=data, headers=self.headers
            )
            if response.status_code == 201:
                return "Factura creada correctamente."
            else:
                return f"Error al crear factura: {response.text}"
        except Exception as e:
            return f"Error al crear factura: {str(e)}"

crm = CRM(billage_api_key)

# Función para leer contenido de un PDF
def leer_pdf(ruta_pdf):
    try:
        reader = PdfReader(ruta_pdf)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text()
        return texto
    except Exception as e:
        return f"Error al leer el PDF: {str(e)}"

# Función para gestionar correos
def leer_correos():
    try:
        imap_server = os.getenv("IMAP_SERVER")
        imap_user = os.getenv("IMAP_USER")
        imap_password = os.getenv("IMAP_PASSWORD")

        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(imap_user, imap_password)
        mail.select("inbox")

        status, mensajes = mail.search(None, "ALL")
        correo_ids = mensajes[0].split()

        ultimos_correos = []
        for correo_id in correo_ids[-5:]:
            status, datos = mail.fetch(correo_id, "(RFC822)")
            for respuesta in datos:
                if isinstance(respuesta, tuple):
                    mensaje = email.message_from_bytes(respuesta[1])
                    ultimos_correos.append({
                        "de": mensaje["from"],
                        "asunto": mensaje["subject"]
                    })
        mail.logout()
        return ultimos_correos
    except Exception as e:
        return f"Error al leer correos: {str(e)}"

# Webhook de WhatsApp
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Obtener mensaje entrante
        mensaje_entrante = request.form.get("Body", "")
        respuesta = procesar_mensaje(mensaje_entrante)

        # Responder vía Twilio
        respuesta_twilio = MessagingResponse()
        respuesta_twilio.message(respuesta)
        return str(respuesta_twilio)
    except Exception as e:
        return f"Error procesando la solicitud: {str(e)}", 500

# Procesar mensaje recibido
def procesar_mensaje(mensaje):
    try:
        if mensaje.lower().startswith("crear factura"):
            _, cliente, concepto, cantidad = mensaje.split(",")
            return crm.crear_factura(cliente.strip(), concepto.strip(), float(cantidad.strip()))

        elif mensaje.lower().startswith("leer correos"):
            correos = leer_correos()
            return "\n".join([f"De: {c['de']} | Asunto: {c['asunto']}" for c in correos])

        elif mensaje.lower().startswith("leer pdf"):
            _, ruta_pdf = mensaje.split(",")
            return leer_pdf(ruta_pdf.strip())

        else:
            # Interactuar con OpenAI
            prompt = [
                {"role": "system", "content": "Eres un asistente experto en normativa, vehículos eléctricos y convenios laborales en España."},
                {"role": "user", "content": mensaje}
            ]
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                max_tokens=500,
                temperature=0.7
            )
            return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error al procesar el mensaje: {str(e)}"

# Punto de entrada
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
