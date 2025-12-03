
import logging
import sqlite3
from fastapi import FastAPI, Response, Form
from twilio.twiml.messaging_response import MessagingResponse

# Database setup
DB_NAME = "twokey.db"

def initialize_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone_number TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# Initialize the database on startup
initialize_database()

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_user_to_db(phone_number: str):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (phone_number) VALUES (?)", (phone_number,))
        conn.commit()
        conn.close()
        logger.info(f"User {phone_number} added to the database.")
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")


@app.post("/whatsapp")
async def handle_whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    """
    Handles incoming WhatsApp messages from Twilio.
    """
    logger.info(f"Incoming message from {From}: {Body}")

    messaging_response = MessagingResponse()

    if Body.lower().strip() == 'start':
        add_user_to_db(From)
        messaging_response.message("Please record your first phrase in Levantine Arabic")
    else:
        messaging_response.message("Hello from the bot")

    return Response(content=str(messaging_response), media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
