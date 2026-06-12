import os
from dotenv import load_dotenv
from slack_bolt import App

# Load environment variables from .env file
load_dotenv()

# Initialize Slack App with bot token and signing secret
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

# Capture any text message sent to channels where the bot is a member
@app.event("message")
def handle_message_events(body, logger):
    event = body.get("event", {})
    text = event.get("text")
    channel_id = event.get("channel")
    user = event.get("user")
    
    # Avoid responding to itself
    if event.get("bot_id") is not None:
        return

    print(f"🔹 Received message in channel {channel_id} from user {user}: {text}")

    # Channel-based routing (Phase 1 Placeholder logic)
    # Replace these placeholder IDs with your actual Slack channel IDs
    if channel_id == "ID_CANALE_DEV":
        risposta = "[Agente Dev - DeepSeek]: Sto elaborando il codice..."
    elif channel_id == "ID_CANALE_COPY":
        risposta = "[Agente Copy - Gemini]: Sto scrivendo il testo..."
    else:
        risposta = f"Ciao! Ho ricevuto il tuo messaggio: '{text}'. Sto configurando i miei circuiti."

    # Post response back to the same channel
    app.client.chat_postMessage(channel=channel_id, text=risposta)

if __name__ == "__main__":
    if not os.environ.get("SLACK_BOT_TOKEN"):
        print("❌ Error: SLACK_BOT_TOKEN environment variable not set.")
    elif not os.environ.get("SLACK_SIGNING_SECRET"):
        print("❌ Error: SLACK_SIGNING_SECRET environment variable not set.")
    else:
        port = int(os.environ.get("PORT", 3000))
        print(f"⚡ Jarvis Core is online and listening to Slack events on port {port}!")
        app.start(port=port)

