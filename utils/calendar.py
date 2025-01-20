from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_event():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': 'Reunión de prueba',
        'start': {'dateTime': '2025-01-20T10:00:00', 'timeZone': 'Europe/Madrid'},
        'end': {'dateTime': '2025-01-20T11:00:00', 'timeZone': 'Europe/Madrid'},
    }

    service.events().insert(calendarId='primary', body=event).execute()
    return "Evento creado con éxito"

def list_events():
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    service = build('calendar', 'v3', credentials=creds)

    events = service.events().list(calendarId='primary').execute()
    return events.get('items', [])

