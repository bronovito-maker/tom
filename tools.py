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

import imaplib
import email
from email.header import decode_header

def check_recent_emails(count: int = 5) -> str:
    """
    Accede alla casella Gmail di Nikita tramite IMAP e recupera un riassunto 
    delle ultime 'count' email ricevute (Mittente, Oggetto, Data).
    
    Args:
        count: Il numero di email recenti da recuperare (default 5).
    """
    username = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not username or not password:
        return "⚠️ Errore: Credenziali Gmail non configurate su Railway."

    try:
        # Connessione al server IMAP di Gmail
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(username, password)
        mail.select("inbox") # Leggiamo la posta in arrivo

        # Cerchiamo gli ID di tutte le email
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            return "Non sono riuscito a recuperare le email."

        mail_ids = messages[0].split()
        # Prendiamo gli ultimi 'count' ID (le email più recenti sono in fondo)
        recent_ids = mail_ids[-count:]
        recent_ids.reverse() # Ordiniamo dalla più recente alla meno recente

        risultato = f"📢 Ecco le ultime {len(recent_ids)} email ricevute:\n\n"

        for m_id in recent_ids:
            # Recuperiamo i dati dell'email per ogni ID
            status, msg_data = mail.fetch(m_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decodifichiamo l'Oggetto
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                    
                    # Decodifichiamo il Mittente
                    from_user, encoding = decode_header(msg["From"])[0]
                    if isinstance(from_user, bytes):
                        from_user = from_user.decode(encoding if encoding else "utf-8", errors="ignore")
                    
                    date_user = msg["Date"]
                    
                    risultato += f"👤 *Da:* {from_user}\n📌 *Oggetto:* {subject}\n📅 *Data:* {date_user}\n"
                    risultato += "─" * 20 + "\n"

        mail.logout()
        return risultato

    except Exception as e:
        return f"⚠️ Errore durante la lettura della casella postale: {str(e)}"

