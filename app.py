import os
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from google import genai  # Google GenAI SDK
from google.genai import types  # For Part/bytes operations
from openai import OpenAI  # OpenAI client compatible with DeepSeek

# Load environment variables from .env file
load_dotenv()

# 1. Initialize Slack Bolt App
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)
handler = SlackRequestHandler(app)

# 2. Initialize AI Clients
# Google Gemini
gemini_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# DeepSeek
deepseek_client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# Helper function to download files from Slack
def download_slack_file(url):
    token = os.environ.get("SLACK_BOT_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"Failed to download file: HTTP {response.status_code}")

# Helper to call Gemini with a robust fallback chain
def call_gemini(model_name, contents, system_instruction):
    # Prova il modello principale richiesto (es. gemini-3.1-flash-lite)
    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=contents,
            config={"system_instruction": system_instruction}
        )
        return response.text
    except Exception as e:
        print(f"⚠️ Model {model_name} failed. Attempting fallback 1 (gemini-2.5-flash-lite)... Error: {e}")
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=contents,
                config={"system_instruction": system_instruction}
            )
            return response.text
        except Exception as e2:
            fallback_pro = "gemini-2.5-pro"
            print(f"⚠️ Fallback 1 failed. Attempting fallback 2 ({fallback_pro})... Error: {e2}")
            response = gemini_client.models.generate_content(
                model=fallback_pro,
                contents=contents,
                config={"system_instruction": system_instruction}
            )
            return response.text

# Helper to describe image with Gemini using a robust fallback chain
def describe_image_with_gemini(file_bytes, mimetype):
    contents = [
        types.Part.from_bytes(data=file_bytes, mime_type=mimetype),
        "Descrivi questa immagine in modo estremamente dettagliato per un assistente AI testuale, estraendo log, codice, o dettagli visivi rilevanti."
    ]
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=contents
        )
        return response.text
    except Exception as e:
        print(f"⚠️ Describe image with gemini-3.1-flash-lite failed. Trying gemini-2.5-flash-lite... Error: {e}")
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=contents
            )
            return response.text
        except Exception as e2:
            fallback_pro = "gemini-2.5-pro"
            print(f"⚠️ Fallback to gemini-2.5-flash-lite failed. Trying {fallback_pro}... Error: {e2}")
            response = gemini_client.models.generate_content(
                model=fallback_pro,
                contents=contents
            )
            return response.text

# 3. Channel Mapping Configuration
# Sostituisci gli ID segnaposto (es. 'C_ID_DEV') con gli ID reali dei tuoi canali Slack
CHANNELS = {
    "C_ID_DEV": {
        "agente": "dev",
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "system": "Sei l'assistente Dev senior di Nikita. Scrivi codice pulito, ottimizzato e risolvi i bug spiegando la logica in modo conciso."
    },
    "C_ID_TECH": {
        "agente": "tech",
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "system": "Sei l'esperto tecnologico di Nikita. Analizzi log di errore, architetture cloud, database (Supabase, Baserow) e problemi sistemistici."
    },
    "C0BA1NT1KEX": {
        "agente": "copy",
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "system": "Sei il copywriter creativo di Nikita. Scrivi testi persuasivi, email commerciali e post per i clienti con un tono professionale ma accattivante."
    },
    "C0B9SKR7E87": {
        "agente": "adv",
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "system": "Sei l'esperto di digital marketing e Google Ads di Nikita. Analizzi le performance delle campagne e proponi ottimizzazioni basate sui dati."
    },
    "C_ID_HANDYMAN": {
        "agente": "handyman",
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "system": "Sei l'assistente tecnico handyman di Nikita. Aiutalo a strutturare preventivi di riparazione, idraulica ed elettrica per i clienti locali."
    }
}

DEFAULT_CONFIG = {
    "provider": "gemini",
    "model": "gemini-3.1-flash-lite",
    "system": "Sei Jarvis (tom), l'assistente personale esecutivo e segretario di Nikita. Sei brillante, conciso e pronto a rispondere a qualsiasi richiesta."
}



# Initialize FastAPI App
api = FastAPI()

# Root endpoint for Railway HTTP Healthcheck
@api.get("/")
async def root():
    return {"status": "ok", "message": "Jarvis Core is online"}

# Webhook endpoint for Slack Events
@api.post("/slack/events")
async def slack_events(request: Request):
    return await handler.handle(request)

# Capture any text message sent to channels where the bot is a member
@app.event("message")
def handle_message_events(body, say):
    event = body.get("event", {})
    text = event.get("text")
    channel_id = event.get("channel")
    user = event.get("user")
    files = event.get("files", [])
    
    # Avoid responding to itself
    if event.get("bot_id") is not None:
        return

    print(f"🔹 Received message in channel {channel_id} from user {user}: {text} (Attachments: {len(files)})")

    # Retrieve agent config based on channel
    config = CHANNELS.get(channel_id, DEFAULT_CONFIG)
    
    try:
        if config["provider"] == "gemini":
            # Build content parts for Gemini
            gemini_contents = []
            
            # Download files and add as Parts
            for file_info in files:
                mimetype = file_info.get("mimetype", "")
                url = file_info.get("url_private_download", "")
                name = file_info.get("name", "")
                if not url:
                    continue
                try:
                    file_bytes = download_slack_file(url)
                    if mimetype.startswith("image/"):
                        gemini_contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mimetype))
                    elif mimetype.startswith("text/") or mimetype in ("application/json", "application/javascript", "text/plain") or name.endswith(('.log', '.py', '.js', '.ts', '.html', '.css', '.json', '.txt')):
                        text_content = file_bytes.decode("utf-8", errors="ignore")
                        gemini_contents.append(f"\n[Contenuto file allegato '{name}']:\n```\n{text_content}\n```\n")
                except Exception as dwn_err:
                    print(f"Error downloading file {name}: {dwn_err}")
            
            # Add user prompt text
            if text:
                gemini_contents.append(text)
            elif not gemini_contents:
                say("Non ho rilevato testo o allegati leggibili.")
                return
            else:
                gemini_contents.append("Analizza l'allegato fornito.")

            # Call Google Gemini using robust helper with fallback
            risposta_ai = call_gemini(
                model_name=config["model"],
                contents=gemini_contents,
                system_instruction=config["system"]
            )

        elif config["provider"] == "deepseek":
            # DeepSeek does not natively support multimodal image input.
            # We construct a text-only prompt. If images are provided, we ask Gemini to describe them first.
            deepseek_prompt_parts = []
            
            for file_info in files:
                mimetype = file_info.get("mimetype", "")
                url = file_info.get("url_private_download", "")
                name = file_info.get("name", "")
                if not url:
                    continue
                try:
                    file_bytes = download_slack_file(url)
                    if mimetype.startswith("image/"):
                        # Ask Gemini to describe the image using robust helper
                        print(f"Generating Gemini description for image: {name}")
                        image_description = describe_image_with_gemini(file_bytes, mimetype)
                        deepseek_prompt_parts.append(f"\n[Descrizione visiva dell'allegato '{name}']:\n{image_description}\n")
                    elif mimetype.startswith("text/") or mimetype in ("application/json", "application/javascript", "text/plain") or name.endswith(('.log', '.py', '.js', '.ts', '.html', '.css', '.json', '.txt')):
                        text_content = file_bytes.decode("utf-8", errors="ignore")
                        deepseek_prompt_parts.append(f"\n[Contenuto file allegato '{name}']:\n```\n{text_content}\n```\n")
                except Exception as dwn_err:
                    print(f"Error processing file {name} for DeepSeek: {dwn_err}")

            if text:
                deepseek_prompt_parts.append(text)
            elif not deepseek_prompt_parts:
                say("Non ho rilevato testo o allegati leggibili.")
                return
            else:
                deepseek_prompt_parts.append("Analizza l'allegato descritto sopra.")

            full_deepseek_prompt = "\n".join(deepseek_prompt_parts)

            # Call DeepSeek
            response = deepseek_client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": config["system"]},
                    {"role": "user", "content": full_deepseek_prompt}
                ]
            )
            risposta_ai = response.choices[0].message.content
            
        else:
            risposta_ai = f"Errore: Provider {config['provider']} non supportato."

        # Say message in Slack channel
        say(risposta_ai)

    except Exception as e:
        error_msg = f"⚠️ C'è stato un problema di comunicazione con l'agente ({config['provider']}): {str(e)}"
        print(f"❌ Error: {error_msg}")
        say(error_msg)

if __name__ == "__main__":
    import uvicorn
    if not os.environ.get("SLACK_BOT_TOKEN"):
        print("❌ Error: SLACK_BOT_TOKEN environment variable not set.")
    elif not os.environ.get("SLACK_SIGNING_SECRET"):
        print("❌ Error: SLACK_SIGNING_SECRET environment variable not set.")
    else:
        port = int(os.environ.get("PORT", 3000))
        print(f"⚡ Jarvis Core is online and listening to Slack events on port {port}!")
        uvicorn.run("app:api", host="0.0.0.0", port=port, reload=True)



