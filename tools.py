import os
import requests
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
    import json
    try:
        # Try loading from local file first, then fallback to env variable containing JSON string
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        elif os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
            service_account_info = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"))
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
        else:
            return {
                "status": "error",
                "message": f"Service Account file {SERVICE_ACCOUNT_FILE} not found and GOOGLE_SERVICE_ACCOUNT_JSON env variable is not set."
            }
        
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


from datetime import datetime
from slack_sdk import WebClient

def search_channel_history(query: str, channel_id: str, limit: int = 100) -> str:
    """
    Scansiona la cronologia profonda del canale Slack corrente (fino a 'limit' messaggi) 
    per cercare informazioni, decisioni o dati passati che contengono una specifica parola chiave.
    
    Args:
        query: La parola chiave o frase da cercare nella cronologia (es. "Marcello", "preventivo", "bug").
        channel_id: L'ID del canale corrente in cui effettuare la ricerca (fornito automaticamente).
        limit: Il numero di messaggi passati da scansionare (default 100).
    """
    # Inizializziamo il client Slack interno al tool usando lo stesso token del server
    slack_client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))
    
    try:
        print(f"🔍 Ricerca storica avviata nel canale {channel_id} per la query: '{query}'")
        
        # Recuperiamo la cronologia estesa
        response = slack_client.conversations_history(channel=channel_id, limit=limit)
        messages = response.get("messages", [])
        
        if not messages:
            return "Non ho trovato nessun messaggio nella cronologia di questo canale."
            
        risultati = []
        query_lower = query.lower()
        
        # Analizziamo i messaggi dal più vecchio al più recente
        for msg in reversed(messages):
            text = msg.get("text", "")
            
            # Filtriamo per la query inserita dall'utente
            if query_lower in text.lower():
                # Convertiamo il timestamp di Slack (es. 1718221790.0002) in una data leggibile
                ts = float(msg.get("ts", 0))
                data_ora = datetime.fromtimestamp(ts).strftime('%d/%m/%Y %H:%M:%S')
                
                autore = "Tom (Tu)" if "bot_id" in msg else f"Utente ({msg.get('user', 'Sconosciuto')})"
                
                risultati.append(f"📅 [{data_ora}] {autore}: {text}")
        
        if not risultati:
            return f"Ho scansionato gli ultimi {limit} messaggi ma non ho trovato nessuna corrispondenza per '{query}'."
            
        # Uniamo i risultati in un unico blocco di testo che Gemini analizzerà
        output = f"Ho trovato {len(risultati)} messaggi rilevanti nella cronologia recente per '{query}':\n\n"
        output += "\n\n".join(risultati)
        return output
        
    except Exception as e:
        return f"⚠️ Errore durante la scansione della cronologia di Slack: {str(e)}"


def check_vercel_status(limit: int = 3) -> str:
    """
    Recupera lo stato degli ultimi deploy su Vercel per monitorare se i siti online sono attivi o se ci sono errori di build.
    """
    token = os.environ.get("VERCEL_TOKEN")
    if not token:
        return "⚠️ Errore: VERCEL_TOKEN non configurato su Railway."
        
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.vercel.com/v6/deployments?limit={limit}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return f"Impossibile connettersi a Vercel. Status: {response.status_code}"
            
        data = response.json()
        deployments = data.get("deployments", [])
        
        if not deployments:
            return "Nessun deploy trovato su Vercel."
            
        output = f"🌐 *Stato Ultimi Deploy Vercel:*\n\n"
        for dep in deployments:
            name = dep.get("name")
            url_sito = dep.get("url")
            state = dep.get("state")
            creator = dep.get("creator", {}).get("username", "Unknown")
            
            status_emoji = "🟢 READY" if state == "READY" else "🔴 ERROR" if state == "ERROR" else "🟡 " + state
            
            output += f"📁 *Progetto:* {name}\n"
            output += f"📊 *Stato:* {status_emoji}\n"
            output += f"🔗 *Link:* https://{url_sito}\n"
            output += f"👤 *Autore:* {creator}\n"
            output += "─" * 20 + "\n"
            
        return output
        
    except Exception as e:
        return f"⚠️ Errore durante la lettura delle API di Vercel: {str(e)}"


def check_github_commits(repo_owner: str, repo_name: str, limit: int = 3) -> str:
    """
    Controlla gli ultimi commit di un determinato repository GitHub per verificare le ultime modifiche al codice.
    
    Args:
        repo_owner: Il proprietario del repository (es. 'bronovito-maker').
        repo_name: Il nome del repository (es. 'tom').
        limit: Numero di commit da mostrare.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return "⚠️ Errore: GITHUB_TOKEN non configurato su Railway."
        
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/commits?per_page={limit}"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return f"Impossibile leggere il repo {repo_name}. Status: {response.status_code}"
            
        commits = response.json()
        if not commits or not isinstance(commits, list):
            return f"Nessun commit trovato per il repo {repo_name}."
            
        output = f"🐙 *Ultimi modifiche su GitHub ({repo_name}):*\n\n"
        for commit_data in commits:
            commit_info = commit_data.get("commit", {})
            author = commit_info.get("author", {}).get("name")
            message = commit_info.get("message")
            date = commit_info.get("author", {}).get("date")
            
            output += f"👤 *Developer:* {author}\n"
            output += f"📝 *Messaggio:* {message.strip()}\n"
            output += f"📅 *Data:* {date}\n"
            output += "─" * 20 + "\n"
            
        return output
        
    except Exception as e:
        return f"⚠️ Errore durante la lettura delle API di GitHub: {str(e)}"


def check_baserow_leads(limit: int = 3) -> str:
    """
    Controlla gli ultimi lead o contatti inseriti nella tabella Baserow di Nikita.
    
    Args:
        limit: Il numero di record da mostrare (default 3).
    """
    token = os.environ.get("BASEROW_TOKEN")
    table_id = os.environ.get("BASEROW_TABLE_CLIENTI_ID", "931646")
    if not token or not table_id:
        return "⚠️ Variabili Baserow (BASEROW_TOKEN o BASEROW_TABLE_CLIENTI_ID) mancanti."
        
    headers = {"Authorization": f"Token {token}"}
    url = f"https://api.baserow.io/api/database/rows/table/{table_id}/?size={limit}&user_field_names=true"
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return f"Impossibile leggere da Baserow. Status: {response.status_code}"
            
        data = response.json()
        rows = data.get("results", [])
        if not rows:
            return "Nessun record trovato su Baserow."
            
        output = f"📊 *Ultimi {len(rows)} record da Baserow (Tabella {table_id}):*\n\n"
        for row in rows:
            row_id = row.get("id")
            output += f"🆔 *ID:* {row_id}\n"
            for key, val in row.items():
                if key in ("id", "order") or val is None or val == "":
                    continue
                if isinstance(val, dict) and "value" in val:
                    val = val["value"]
                elif isinstance(val, list):
                    val = ", ".join([str(item.get("value", item)) if isinstance(item, dict) else str(item) for item in val])
                output += f"📌 *{key}:* {val}\n"
            output += "─" * 20 + "\n"
        return output
    except Exception as e:
        return f"⚠️ Errore Baserow: {str(e)}"


def check_supabase_logs(project: str = "TOM", table_name: str = "logs", limit: int = 5) -> str:
    """
    Legge gli ultimi record inseriti in una tabella Supabase (progetto 'BUN' o 'TOM') per monitorare errori, eventi o utenti.
    
    Args:
        project: Il progetto da interrogare ('BUN' o 'TOM'). Default 'TOM'.
        table_name: Il nome della tabella da leggere (es. 'logs', 'users'). Default 'logs'.
        limit: Il numero massimo di righe da recuperare (default 5).
    """
    project = project.upper()
    if project == "BUN":
        url = os.environ.get("SUPABASE_BUN_URL")
        key = os.environ.get("SUPABASE_BUN_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_BUN_KEY")
    elif project == "TOM":
        url = os.environ.get("SUPABASE_TOM_URL")
        key = os.environ.get("SUPABASE_TOM_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_TOM_ANON_KEY")
    else:
        return f"⚠️ Progetto Supabase '{project}' non supportato. Usa 'BUN' o 'TOM'."
        
    if not url or not key:
        return f"⚠️ Credenziali Supabase mancanti per il progetto {project}."
        
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Range": f"0-{limit-1}"
    }
    
    api_url = f"{url}/rest/v1/{table_name}?order=created_at.desc"
    
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code == 400 and "created_at" in response.text:
            print("created_at not found, trying sorting by id.desc")
            api_url = f"{url}/rest/v1/{table_name}?order=id.desc"
            response = requests.get(api_url, headers=headers)
            
        if response.status_code == 400 and "id" in response.text:
            print("id not found, trying query without ordering")
            api_url = f"{url}/rest/v1/{table_name}"
            response = requests.get(api_url, headers=headers)
            
        if response.status_code != 200:
            return f"Impossibile leggere la tabella {table_name} su Supabase ({project}). Status: {response.status_code}"
            
        rows = response.json()
        if not rows:
            return f"Nessun record trovato nella tabella '{table_name}' del progetto Supabase ({project})."
            
        output = f"⚡ *Ultimi record della tabella '{table_name}' su Supabase ({project}):*\n\n"
        for i, row in enumerate(rows):
            output += f"🔹 *Record {i+1}:*\n"
            for k, v in row.items():
                if v is None or v == "":
                    continue
                output += f"  • *{k}:* {v}\n"
            output += "─" * 15 + "\n"
        return output
        
    except Exception as e:
        return f"⚠️ Errore Supabase ({project}) sulla tabella {table_name}: {str(e)}"


def create_handyman_ticket(
    customer_name: str,
    description: str,
    category: str,
    contact_phone: str = None,
    city: str = None,
    address: str = None,
    price_range_max: float = None,
    scheduled_at: str = None
) -> str:
    """
    Crea un nuovo ticket/intervento nel CRM di Nikituttofare su Supabase.
    
    Args:
        customer_name: Nome del cliente.
        description: Descrizione del guasto o del lavoro da fare.
        category: Categoria in inglese ('plumbing', 'electric', 'locksmith', 'climate', 'handyman', 'painting', etc.).
        contact_phone: Numero di telefono del cliente.
        city: Città dell'intervento (Rimini, Riccione, etc.).
        address: Indirizzo completo.
        price_range_max: Prezzo massimo stimato o preventivato.
        scheduled_at: Data e ora programmata in formato ISO (YYYY-MM-DDTHH:MM:SS).
    """
    url = os.environ.get("SUPABASE_TOM_URL")
    key = os.environ.get("SUPABASE_TOM_SERVICE_ROLE_KEY")
    
    if not url or not key:
        return "⚠️ Errore: Credenziali Supabase TOM mancanti su Railway."

    clean_phone = None
    if contact_phone:
        phone_digits = "".join([c for c in str(contact_phone) if c.isdigit()])
        if phone_digits:
            try:
                clean_phone = int(phone_digits)
            except:
                clean_phone = phone_digits

    valid_categories = ['plumbing', 'electric', 'locksmith', 'climate', 'handyman', 'painting', 'cleaning', 'carpentry', 'moving', 'garden', 'appliances', 'renovations', 'generic']
    if category not in valid_categories:
        category = 'generic'

    payload = {
        "customer_name": customer_name,
        "description": description,
        "category": category,
        "contact_phone": clean_phone,
        "city": city,
        "address": address,
        "price_range_max": price_range_max,
        "source": "phone_manual",
        "status": "new",
        "payment_status": "pending"
    }

    if scheduled_at:
        payload["scheduled_at"] = scheduled_at

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    try:
        api_url = f"{url}/rest/v1/tickets"
        response = requests.post(api_url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            created_ticket = response.json()[0]
            ticket_id = created_ticket.get("id", "Sconosciuto")
            return f"✅ Ticket creato con successo! ID: {ticket_id}. Cliente: {customer_name}, Categoria: {category}."
        else:
            return f"❌ Errore Supabase durante l'inserimento. Status: {response.status_code}, Dettagli: {response.text}"
            
    except Exception as e:
        return f"⚠️ Errore di rete/codice durante la creazione del ticket: {str(e)}"

