import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from slack_bolt import App
from slack_bolt.adapter.fastapi import SlackRequestHandler
from google import genai  # Google GenAI SDK
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

# 3. Channel Mapping Configuration
# Sostituisci gli ID segnaposto (es. 'C_ID_DEV') con gli ID reali dei tuoi canali Slack
CHANNELS = {
    "C_ID_DEV": {
        "agente": "dev",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "system": "Sei l'assistente Dev senior di Nikita. Scrivi codice pulito, ottimizzato e risolvi i bug spiegando la logica in modo conciso."
    },
    "C_ID_TECH": {
        "agente": "tech",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "system": "Sei l'esperto tecnologico di Nikita. Analizzi log di errore, architetture cloud, database (Supabase, Baserow) e problemi sistemistici."
    },
    "C_ID_COPY": {
        "agente": "copy",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "system": "Sei il copywriter creativo di Nikita. Scrivi testi persuasivi, email commerciali e post per i clienti con un tono professionale ma accattivante."
    },
    "C_ID_ADV": {
        "agente": "adv",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "system": "Sei l'esperto di digital marketing e Google Ads di Nikita. Analizzi le performance delle campagne e proponi ottimizzazioni basate sui dati."
    },
    "C_ID_HANDYMAN": {
        "agente": "handyman",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "system": "Sei l'assistente tecnico handyman di Nikita. Aiutalo a strutturare preventivi di riparazione, idraulica ed elettrica per i clienti locali."
    }
}

DEFAULT_CONFIG = {
    "provider": "gemini",
    "model": "gemini-2.5-flash",
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
    
    # Avoid responding to itself
    if event.get("bot_id") is not None:
        return

    print(f"🔹 Received message in channel {channel_id} from user {user}: {text}")

    # Retrieve agent config based on channel
    config = CHANNELS.get(channel_id, DEFAULT_CONFIG)
    
    try:
        if config["provider"] == "gemini":
            # Call Google Gemini using the new SDK
            response = gemini_client.models.generate_content(
                model=config["model"],
                contents=text,
                config={"system_instruction": config["system"]}
            )
            risposta_ai = response.text

        elif config["provider"] == "deepseek":
            # Call DeepSeek via OpenAI SDK compatibilities
            response = deepseek_client.chat.completions.create(
                model=config["model"],
                messages=[
                    {"role": "system", "content": config["system"]},
                    {"role": "user", "content": text}
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


