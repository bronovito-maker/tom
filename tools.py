import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Define Google Calendar scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'gen-lang-client-0592360914-f5f267dab54d.json'

def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = ""):
    """
    Crea un nuovo evento o appuntamento nel calendario di Google di Nikita.
    
    Args:
        summary: Il titolo dell'evento (es. "Sopralluogo Marcello", "Call con Francesco").
        start_time: Data e ora di inizio in formato ISO (es. "2026-06-15T15:00:00").
        end_time: Data e ora di fine in formato ISO (es. "2026-06-15T16:00:00").
        description: Dettagli opzionali o note sull'appuntamento.
    """
    try:
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            return {
                "status": "error",
                "message": f"Service Account file {SERVICE_ACCOUNT_FILE} not found."
            }

        # Load credentials from service account JSON file
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        
        # Build Calendar service
        service = build('calendar', 'v3', credentials=creds)
        
        # Define the event resource
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Rome',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Rome',
            },
        }
        
        # Insert the event into 'primary' calendar
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created successfully: {created_event.get('htmlLink')}")
        return {
            "status": "success",
            "event_link": created_event.get('htmlLink'),
            "summary": summary,
            "start": start_time
        }
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return {
            "status": "error",
            "message": str(e)
        }
