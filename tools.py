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
        
        # Insert the event into Nikita's calendar (shared with the service account)
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
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


def list_calendar_events(start_time: str, end_time: str) -> str:
    """
    Ritorna la lista degli eventi presenti nel calendario di Google di Nikita in un dato intervallo di tempo.
    Utile per verificare la presenza di conflitti o se un appuntamento è già registrato.
    
    Args:
        start_time: Data e ora di inizio ricerca in formato ISO (es. "2026-06-15T00:00:00").
        end_time: Data e ora di fine ricerca in formato ISO (es. "2026-06-15T23:59:59").
    """
    import json
    try:
        # Load credentials
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
            return "⚠️ Errore Google Calendar: Credenziali non trovate."

        # Build service
        service = build('calendar', 'v3', credentials=creds)
        
        # Format timezone suffix if not present
        if "T" in start_time and not start_time.endswith("Z") and "+" not in start_time and "-" not in start_time[10:]:
            start_time = start_time + "+02:00"
        if "T" in end_time and not end_time.endswith("Z") and "+" not in end_time and "-" not in end_time[10:]:
            end_time = end_time + "+02:00"

        # Read events from Nikita's calendar (shared with the service account)
        calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time,
            timeMax=end_time,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        if not events:
            return f"Non ho trovato nessun evento in calendario tra il {start_time} e il {end_time}."
            
        output = f"📅 *Eventi in calendario trovati:*\n\n"
        for event in events:
            summary = event.get('summary', 'Senza titolo')
            start = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            end = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
            output += f"📌 *{summary}*\n⏰ *Inizio:* {start}\n⏰ *Fine:* {end}\n"
            output += "─" * 15 + "\n"
        return output
        
    except Exception as e:
        return f"⚠️ Errore durante la lettura del calendario Google: {str(e)}"


# Google Analytics 4 Property IDs
GA4_PROPERTIES = {
    "ZIREL": "541486430",
    "NIKITUTTOFARE": "541507101"
}

def check_ga_analytics(project: str = "ZIREL", days: int = 7) -> str:
    """
    Recupera le statistiche di Google Analytics 4 (sessioni, utenti, pagine viste, top pagine)
    per uno dei progetti configurati.

    Args:
        project: Il progetto da analizzare. Valori validi: 'ZIREL' o 'NIKITUTTOFARE'. Default 'ZIREL'.
        days: Numero di giorni da analizzare a ritroso da oggi (default 7).
    """
    import json
    import google.auth.transport.requests as ga_transport
    from datetime import date, timedelta

    project_upper = project.upper()
    if project_upper not in GA4_PROPERTIES:
        return f"⚠️ Progetto '{project}' non riconosciuto. Usa 'ZIREL' o 'NIKITUTTOFARE'."

    property_id = GA4_PROPERTIES[project_upper]
    ga_scopes = ["https://www.googleapis.com/auth/analytics.readonly"]

    try:
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=ga_scopes
            )
        elif os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
            info = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"))
            creds = service_account.Credentials.from_service_account_info(
                info, scopes=ga_scopes
            )
        else:
            return "⚠️ Credenziali Google non trovate (né file locale né variabile d'ambiente)."

        # Refresh token
        auth_req = ga_transport.Request()
        creds.refresh(auth_req)

        today = date.today()
        start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")

        api_url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json"
        }

        # Query 1: totali aggregati
        totals_payload = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "metrics": [
                {"name": "sessions"},
                {"name": "activeUsers"},
                {"name": "newUsers"},
                {"name": "screenPageViews"}
            ]
        }
        totals_resp = requests.post(api_url, json=totals_payload, headers=headers)
        if totals_resp.status_code != 200:
            return f"❌ Errore GA4 API (totali): {totals_resp.status_code} — {totals_resp.text}"

        totals_data = totals_resp.json()
        totals = totals_data.get("totals", [{}])[0].get("metricValues", [])

        # Query 2: top 5 pagine per sessioni
        pages_payload = {
            "dateRanges": [{"startDate": start_date, "endDate": end_date}],
            "dimensions": [{"name": "pagePath"}],
            "metrics": [
                {"name": "sessions"},
                {"name": "activeUsers"}
            ],
            "orderBys": [{"metric": {"metricName": "sessions"}, "desc": True}],
            "limit": 5
        }
        pages_resp = requests.post(api_url, json=pages_payload, headers=headers)
        if pages_resp.status_code != 200:
            return f"❌ Errore GA4 API (pagine): {pages_resp.status_code} — {pages_resp.text}"

        pages_data = pages_resp.json()

        project_labels = {"ZIREL": "Zirèl", "NIKITUTTOFARE": "Nikituttofare"}
        label = project_labels.get(project_upper, project_upper)

        output = f"📊 *Google Analytics — {label}*\n"
        output += f"📅 Periodo: {start_date} → {end_date} ({days} giorni)\n\n"

        if totals:
            output += f"👥 *Utenti attivi:* {totals[1].get('value', 'N/A')}\n"
            output += f"🆕 *Nuovi utenti:* {totals[2].get('value', 'N/A')}\n"
            output += f"📈 *Sessioni:* {totals[0].get('value', 'N/A')}\n"
            output += f"👁️ *Pagine viste:* {totals[3].get('value', 'N/A')}\n\n"

        rows = pages_data.get("rows", [])
        if rows:
            output += f"🏆 *Top {len(rows)} pagine per sessioni:*\n"
            for row in rows:
                page = row.get("dimensionValues", [{}])[0].get("value", "/")
                metrics = row.get("metricValues", [])
                sessions_val = metrics[0].get("value", "0") if metrics else "0"
                users_val = metrics[1].get("value", "0") if len(metrics) > 1 else "0"
                output += f"  📄 `{page}` — {sessions_val} sessioni, {users_val} utenti\n"

        return output

    except Exception as e:
        return f"⚠️ Errore Google Analytics: {str(e)}"


def generate_handyman_quote(
    customer_name: str,
    city: str,
    address: str,
    items_json: str, # Riceverà una stringa JSON con l'elenco dei lavori e prezzi
    notes: str = None
) -> str:
    """
    Genera un file PDF professionale di preventivo per il servizio Nikituttofare,
    lo salva temporaneamente e restituisce il percorso del file PDF generato.
    
    Args:
        customer_name: Nome del cliente (es. "Marco Neri").
        city: Città di residenza/intervento (es. "Rimini").
        address: Indirizzo completo (es. "via Dante 5").
        items_json: Stringa JSON valida che rappresenta un array di oggetti con campi 'description' (str), 'details' (str) e 'price' (float). Esempio: '[{"description": "Sostituzione rubinetto cucina", "details": "", "price": 120.0}, {"description": "Manodopera", "details": "", "price": 80.0}]'.
        notes: Note o condizioni aggiuntive opzionali (es. garanzie, validità).
    """
    import json
    from datetime import datetime
    try:
        items = json.loads(items_json)
    except Exception:
        return "⚠️ Errore nel formato delle voci di spesa inviate a Tom."
        
    data_oggi = datetime.now().strftime('%d/%m/%Y')
    
    # Generate sequential-like quote number: N. [DayOfYear] - Anno [Year]
    now = datetime.now()
    day_of_year = now.strftime('%j')
    num_preventivo = f"N. {day_of_year.zfill(3)} - Anno {now.year}"
    
    # Calcolo dei totali
    totale_complessivo = sum(item.get('price', 0) for item in items)
    
    # Costruzione dinamica delle righe della tabella in HTML
    table_rows = ""
    for item in items:
        desc = item.get('description', '')
        sub_desc = item.get('details', '')
        price = item.get('price', 0)
        
        desc_html = f"<strong>{desc}</strong>"
        if sub_desc:
            desc_html += f"<br><span style='font-size: 8.5pt; color: #718096;'>{sub_desc}</span>"
            
        table_rows += f"""
        <tr>
            <td>{desc_html}</td>
            <td class="text-center">1</td>
            <td class="text-right">{price:,.2f} €</td>
            <td class="text-right">{price:,.2f} €</td>
        </tr>
        """

    # Note aggiuntive
    notes_extra = ""
    if notes:
        notes_extra = f"<p style='margin-top: 8px;'><strong>Note aggiuntive:</strong> {notes}</p>"

    # Template HTML (Versione fedele ai file docx)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: A4;
                margin: 20mm 15mm 20mm 15mm;
                @bottom-right {{
                    content: "Pagina " counter(page) " di " counter(pages);
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    font-size: 8pt;
                    color: #718096;
                }}
            }}
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                color: #2d3748;
                line-height: 1.5;
                font-size: 10pt;
            }}
            .header-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 25px;
            }}
            .header-table td {{
                vertical-align: top;
            }}
            .brand {{
                font-size: 24pt;
                font-weight: bold;
                color: #1a202c;
                line-height: 1.1;
                margin: 0;
            }}
            .brand-sub {{
                font-size: 10pt;
                color: #718096;
                margin: 5px 0 0 0;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .provider-details {{
                text-align: right;
                font-size: 9pt;
                color: #4a5568;
                line-height: 1.4;
            }}
            .title-container {{
                border-bottom: 2px solid #2d3748;
                padding-bottom: 5px;
                margin-bottom: 20px;
            }}
            .doc-title {{
                font-size: 18pt;
                font-weight: bold;
                color: #2d3748;
                text-transform: uppercase;
                margin: 0;
                letter-spacing: 0.5px;
            }}
            .meta-table {{
                width: 45%;
                border-collapse: collapse;
                margin-bottom: 25px;
            }}
            .meta-table th {{
                background-color: #edf2f7;
                color: #2d3748;
                font-size: 8.5pt;
                font-weight: bold;
                text-transform: uppercase;
                padding: 6px 10px;
                border: 1px solid #cbd5e0;
                text-align: center;
            }}
            .meta-table td {{
                padding: 8px 10px;
                border: 1px solid #cbd5e0;
                text-align: center;
                font-size: 9.5pt;
            }}
            .section-title {{
                font-size: 11pt;
                font-weight: bold;
                color: #2d3748;
                text-transform: uppercase;
                border-bottom: 1px solid #e2e8f0;
                padding-bottom: 4px;
                margin-top: 25px;
                margin-bottom: 10px;
            }}
            .client-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 25px;
            }}
            .client-table td {{
                padding: 8px 12px;
                border: 1px solid #cbd5e0;
                vertical-align: top;
            }}
            .client-table td.label {{
                width: 25%;
                background-color: #f7fafc;
                font-weight: bold;
                color: #4a5568;
                font-size: 9pt;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
                margin-bottom: 20px;
            }}
            .items-table th {{
                background-color: #2d3748;
                color: #ffffff;
                padding: 10px 12px;
                font-size: 9pt;
                font-weight: bold;
                text-transform: uppercase;
                text-align: left;
            }}
            .items-table td {{
                padding: 10px 12px;
                border-bottom: 1px solid #cbd5e0;
                border-left: 1px solid #cbd5e0;
                border-right: 1px solid #cbd5e0;
                font-size: 9.5pt;
            }}
            .text-right {{
                text-align: right;
            }}
            .text-center {{
                text-align: center;
            }}
            .total-row td {{
                border-bottom: none;
                border-left: none;
                border-right: none;
                font-weight: bold;
                padding-top: 15px;
            }}
            .total-label {{
                font-size: 10pt;
                color: #4a5568;
                text-transform: uppercase;
            }}
            .total-amount {{
                font-size: 12pt;
                color: #2d3748;
            }}
            .notes-block {{
                background-color: #f7fafc;
                border: 1px solid #cbd5e0;
                border-left: 4px solid #2d3748;
                padding: 15px;
                margin-top: 35px;
                font-size: 9pt;
                color: #4a5568;
                line-height: 1.4;
            }}
            .notes-block p {{
                margin: 4px 0;
            }}
            .signature-table {{
                width: 100%;
                margin-top: 60px;
                border-collapse: collapse;
            }}
            .signature-table td {{
                width: 50%;
                font-size: 9.5pt;
                color: #4a5568;
                vertical-align: bottom;
                padding-bottom: 30px;
            }}
        </style>
    </head>
    <body>
        <table class="header-table">
            <tr>
                <td>
                    <h1 class="brand">NikiTuttoFare</h1>
                    <p class="brand-sub">Servizi Domestici e Riparazioni</p>
                </td>
                <td class="provider-details">
                    <strong>Nikita Bronovs</strong><br>
                    Riccione, RN<br>
                    Codice Fiscale: BRNNKT00C10Z145R<br>
                    Telefono: +39 346 102 7447<br>
                    Email: bronovito@gmail.com
                </td>
            </tr>
        </table>

        <div class="title-container">
            <h2 class="doc-title">Preventivo</h2>
        </div>

        <table class="meta-table">
            <thead>
                <tr>
                    <th>Data di Emissione</th>
                    <th>Preventivo N.</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{data_oggi}</td>
                    <td>{num_preventivo}</td>
                </tr>
            </tbody>
        </table>

        <div class="section-title">Dati Cliente</div>
        <table class="client-table">
            <tr>
                <td class="label">Nome / Ragione Sociale</td>
                <td>{customer_name}</td>
            </tr>
            <tr>
                <td class="label">Indirizzo di Riferimento</td>
                <td>{address}, {city}</td>
            </tr>
        </table>

        <div class="section-title">Oggetto Intervento</div>
        <p style="margin: 5px 0 20px 0; font-size: 9.5pt; color: #2d3748;">
            Preventivo per servizi di montaggio, installazioni domestiche e interventi di manutenzione/riparazione presso l'abitazione del cliente.
        </p>

        <div class="section-title">Descrizione Attività e Costi</div>
        <table class="items-table">
            <thead>
                <tr>
                    <th>Descrizione Lavoro</th>
                    <th class="text-center" style="width: 10%;">Q.tà</th>
                    <th class="text-right" style="width: 20%;">Prezzo Unitario</th>
                    <th class="text-right" style="width: 20%;">Totale</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
                <tr class="total-row">
                    <td colspan="2"></td>
                    <td class="text-right total-label">TOTALE IMPONIBILE</td>
                    <td class="text-right total-amount">{totale_complessivo:,.2f} €</td>
                </tr>
                <tr class="total-row" style="padding-top: 0;">
                    <td colspan="2"></td>
                    <td class="text-right total-label">TOTALE COMPLESSIVO</td>
                    <td class="text-right total-amount" style="font-size: 13pt; color: #1a202c; border-top: 1px solid #cbd5e0; padding-top: 5px;">{totale_complessivo:,.2f} €</td>
                </tr>
            </tbody>
        </table>

        <div class="notes-block">
            <strong style="color: #2d3748; font-size: 9.5pt; text-transform: uppercase; display: block; margin-bottom: 5px;">Note e Condizioni Operative</strong>
            <p>Il preventivo include esclusivamente il montaggio/installazione standard su predisposizioni esistenti. Eventuali modifiche elettriche, fissaggi speciali, materiali aggiuntivi o problematiche non visibili in fase di sopralluogo saranno conteggiati separatamente.</p>
            <p><strong>Validità:</strong> Il presente documento ha una validità di 14 giorni dalla data di emissione.</p>
            {notes_extra}
        </div>

        <table class="signature-table">
            <tr>
                <td>
                    Firma per Accettazione (Cliente)<br><br><br>
                    __________________________________________
                </td>
                <td style="text-align: right;">
                    Firma Operatore (NikiTuttoFare)<br><br><br>
                    __________________________________________
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    
    # Output file path
    clean_name = customer_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    filename = f"preventivo_{clean_name}.pdf"
    output_path = f"/tmp/{filename}"
    
    try:
        from weasyprint import HTML
        HTML(string=html_template).write_pdf(output_path)
        return output_path
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"❌ WEASYPRINT ERROR:\n{tb}")
        return f"⚠️ Errore durante la compilazione del PDF: {str(e)}\n\nTraceback:\n{tb}"

