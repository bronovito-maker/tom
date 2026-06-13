import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from slack_sdk import WebClient

# Load environment variables
load_dotenv()

def run_cron():
    url = os.environ.get("SUPABASE_TOM_URL")
    key = os.environ.get("SUPABASE_TOM_SERVICE_ROLE_KEY")
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    
    if not url or not key or not slack_token:
        print("❌ Error: Missing SUPABASE_TOM_URL, SUPABASE_TOM_SERVICE_ROLE_KEY or SLACK_BOT_TOKEN.")
        return
        
    slack_client = WebClient(token=slack_token)
    
    # Calculate timestamps: between 4 days ago (96 hours) and 5 days ago (120 hours)
    now = datetime.now(timezone.utc)
    four_days_ago = now - timedelta(days=4)
    five_days_ago = now - timedelta(days=5)
    
    # Format to ISO 8601 with Z timezone
    four_days_iso = four_days_ago.isoformat().replace("+00:00", "Z")
    five_days_iso = five_days_ago.isoformat().replace("+00:00", "Z")
    
    print(f"Checking tickets completed between {five_days_iso} and {four_days_iso} with no review...")
    
    # Query Supabase: completed_at is between 4 and 5 days ago, and rating is null
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}"
    }
    api_url = (
        f"{url}/rest/v1/tickets"
        f"?completed_at=gte.{five_days_iso}"
        f"&completed_at=lte.{four_days_iso}"
        f"&rating=is.null"
    )
    
    try:
        response = requests.get(api_url, headers=headers)
        if response.status_code != 200:
            print(f"❌ Supabase query failed: {response.status_code} - {response.text}")
            return
            
        tickets = response.json()
        if not tickets:
            print("No tickets found to request reviews for.")
            return
            
        print(f"Found {len(tickets)} tickets. Sending reminders...")
        
        for ticket in tickets:
            customer_name = ticket.get("customer_name") or "Cliente Sconosciuto"
            contact_phone = ticket.get("contact_phone")
            description = ticket.get("description") or "Nessuna descrizione"
            category = ticket.get("category") or "generic"
            ticket_id = ticket.get("id")
            
            # Format phone number
            phone_str = str(int(contact_phone)) if contact_phone else "Non fornito"
            
            message = (
                f"📢 *Promemoria Recensione automatico di Tom*\n\n"
                f"Nikita, sono passati *4 giorni* dall'intervento per:\n"
                f"👤 *Cliente:* {customer_name}\n"
                f"🛠️ *Lavoro:* {description} ({category})\n"
                f"📞 *Contatto:* {phone_str}\n\n"
                f"Ricordati di scrivergli o chiamarlo per chiedergli un feedback! "
                f"Una volta fatta, puoi inserire la recensione nel gestionale."
            )
            
            # Send message to handyman channel
            channel_id = os.environ.get("SLACK_HANDYMAN_CHANNEL_ID", "C0BA846TML2")
            try:
                slack_client.chat_postMessage(channel=channel_id, text=message)
                print(f"Sent reminder for ticket {ticket_id} ({customer_name})")
            except Exception as slack_err:
                print(f"❌ Failed to send Slack message for ticket {ticket_id}: {slack_err}")
                
    except Exception as e:
        print(f"❌ Error during cron execution: {e}")

if __name__ == "__main__":
    run_cron()
