
import os
import json
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Flask app
app = Flask(__name__)

# Load credentials from .env
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

# --- Hardcoded Data & State ---

CURRICULUM = [
    {"hebrew": "אני רוצה קפה", "target_arabic": "בדי קהוה", "phonetic": "Bidi Kahwa"},
    {"hebrew": "איפה השירותים?", "target_arabic": "וין אל חמאם?", "phonetic": "Wein al hammam?"},
    {"hebrew": "כמה זה עולה?", "target_arabic": "קדיש חקו?", "phonetic": "Qaddesh haqqo?"},
    {"hebrew": "אני לא מבין", "target_arabic": "מש פאהם", "phonetic": "Mish fahem"},
]

# In-memory state management
# user_state = { "whatsapp_user_id": {"current_index": 0, "waiting_for_audio": False} }
user_state = {}

# --- Helper Functions ---

def send_whatsapp_message(to, body):
    """Sends a WhatsApp message."""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": body},
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending WhatsApp message: {e}")
        app.logger.error(response.text)
        return None

def download_media(media_id):
    """Downloads media from WhatsApp servers."""
    try:
        # Get media URL
        url = f"https://graph.facebook.com/v18.0/{media_id}/"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        media_url = response.json().get("url")

        if not media_url:
            app.logger.error("Could not get media URL from Meta API.")
            return None

        # Download the actual media file
        headers_download = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        media_response = requests.get(media_url, headers=headers_download)
        media_response.raise_for_status()
        
        # Save temporarily
        temp_filename = f"temp_{media_id}.ogg"
        with open(temp_filename, "wb") as f:
            f.write(media_response.content)
        return temp_filename
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error downloading media: {e}")
        if 'response' in locals():
            app.logger.error(response.text)
        return None


def get_ai_feedback(audio_path, hebrew_phrase, target_arabic):
    """Uploads audio to Gemini and gets feedback."""
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        audio_file = genai.upload_file(path=audio_path, display_name="Student Translation")
        
        prompt = f"""
        Role: You are a friendly, encouraging Palestinian Arabic tutor.
        Task: The student is trying to translate the Hebrew phrase: "{hebrew_phrase}" into Palestinian Arabic (Levantine dialect). The expected target is roughly "{target_arabic}".
        Input: An audio file of the student speaking.
        Output:
        1. Transcribe what they actually said (in Arabic script).
        2. Give a Score (0-100).
        3. If the score is < 100, explain the mistake (pronunciation or grammar) in simple English.
        4. Be lenient with synonyms (e.g., 'Bidi' vs 'Haabeb' are both okay for 'want').
        """

        response = model.generate_content([prompt, audio_file])
        return response.text
    except Exception as e:
        app.logger.error(f"Error with Gemini AI: {e}")
        return "Sorry, I had a problem analyzing the audio. Please try again."
    finally:
        # Clean up the temporary file
        if os.path.exists(audio_path):
            os.remove(audio_path)


def get_next_lesson(user_id):
    """Sends the next lesson to the user."""
    current_index = user_state.get(user_id, {}).get("current_index", 0)
    if current_index < len(CURRICULUM):
        lesson = CURRICULUM[current_index]
        hebrew_sentence = lesson["hebrew"]
        send_whatsapp_message(user_id, f"Translate this to Palestinian Arabic: {hebrew_sentence}")
        user_state[user_id]["waiting_for_audio"] = True
    else:
        send_whatsapp_message(user_id, "You've completed the curriculum! Type 'Reset' to start over.")
        user_state[user_id]["waiting_for_audio"] = False

# --- Flask Routes ---

@app.route("/webhook", methods=["GET"])
def webhook_verification():
    """Verifies the webhook subscription."""
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200
    return "Hello world", 200

@app.route("/webhook", methods=["POST"])
def webhook_handler():
    """Handles incoming WhatsApp messages."""
    data = request.get_json()
    app.logger.info(json.dumps(data, indent=2))

    if data.get("object"):
        if (
            data.get("entry")
            and data["entry"][0].get("changes")
            and data["entry"][0]["changes"][0].get("value")
            and data["entry"][0]["changes"][0]["value"].get("messages")
        ):
            message_info = data["entry"][0]["changes"][0]["value"]["messages"][0]
            user_id = message_info["from"]
            message_type = message_info["type"]

            # Initialize user if not exists
            if user_id not in user_state:
                user_state[user_id] = {"current_index": 0, "waiting_for_audio": False}

            # Handle Text Messages
            if message_type == "text":
                command = message_info["text"]["body"].strip().lower()
                if command == "start":
                    user_state[user_id]["current_index"] = 0
                    get_next_lesson(user_id)
                elif command == "reset":
                    user_state[user_id]["current_index"] = 0
                    send_whatsapp_message(user_id, "Let's start from the beginning!")
                    get_next_lesson(user_id)
                else:
                    if user_state[user_id].get("waiting_for_audio"):
                         send_whatsapp_message(user_id, "Please send a voice note with the translation.")
                    else:
                         send_whatsapp_message(user_id, "Type 'Start' to begin.")


            # Handle Audio Messages
            elif message_type == "audio":
                if not user_state[user_id].get("waiting_for_audio"):
                    send_whatsapp_message(user_id, "Type 'Start' to begin.")
                    return jsonify({"status": "ok"}), 200

                media_id = message_info["audio"]["id"]
                audio_path = download_media(media_id)

                if audio_path:
                    current_index = user_state[user_id]["current_index"]
                    lesson = CURRICULUM[current_index]
                    
                    feedback = get_ai_feedback(audio_path, lesson["hebrew"], lesson["target_arabic"])
                    send_whatsapp_message(user_id, feedback)

                    # Advance to next lesson
                    user_state[user_id]["current_index"] += 1
                    get_next_lesson(user_id)

    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    # Make sure to set the host to '0.0.0.0' to be accessible externally
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
