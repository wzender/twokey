## 1. Project Overview
We are building a mobile-first web application (PWA) to help students learn Levantine Arabic pronunciation.

Core user journey:
1. The app presents a phrase in the user's native language (e.g., Hebrew).
2. The user records the translation in the learned language (e.g., Levantine Arabic).
3. After submitting (no streaming), the app analyzes the recording with OpenAI Whisper for transcription + an OpenAI GPT model for feedback (no Gemini LLMs).
4. The result (transcription, score, feedback) is shown in the results pane.

## 2. Tech Stack & Architecture
* **Backend:** FastAPI (for high-performance API endpoints and async handling).
* **Frontend:** Dash (Plotly) for the UI, mounted *inside* the FastAPI application.
* **AI:** OpenAI Whisper for transcription + GPT (e.g., `gpt-4o-mini`) for scoring/feedback. (No Gemini LLMs.)
* **Deployment:** Render.com (Python Environment) or any HTTPS host.
* **Audio Handling:** JavaScript (MediaRecorder API) via Dash Clientside Callbacks.
* **Optional WhatsApp Ingest:** Twilio WhatsApp webhook can forward voice notes to `/api/whatsapp`.

## 3. Directory Structure
Adhere strictly to this file structure:
```text
/
├── assets/
│   ├── style.css           # Mobile-responsive styling
│   └── audio_recorder.js   # Clientside logic for Microphone access
├── app.py                  # Dash application definition (UI Layout)
├── main.py                 # FastAPI entry point (Mounts Dash here)
├── llm_service.py          # Interacts with OpenAI Whisper + GPT
├── requirements.txt        # Python dependencies
└── render.yaml             # Render deployment config

4. Implementation Guidelines
A. FastAPI Integration (main.py)
The entry point is main.py.

Initialize server = FastAPI().

Mount the Dash app using WSGIMiddleware:

Python

from fastapi.middleware.wsgi import WSGIMiddleware
server.mount("/", WSGIMiddleware(app.server))
Create a specific API endpoint @server.post("/api/analyze") to receive the .wav file from the frontend.

B. Dash Frontend (app.py)
Mobile First: Ensure the Dash app includes the viewport meta tag: meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1'}]

Components: Use html.Div and html.Button. Avoid complex graphs; this is a text/audio app.

State Management: Use dcc.Store to hold the JSON response from the API.

C. Audio Recording (The "Tricky" Part)
Dash cannot natively access the microphone.

Use a Clientside Callback in assets/audio_recorder.js.

Logic:

User clicks "Record".

JS captures audio via navigator.mediaDevices.getUserMedia.

JS converts to Blob/File.

JS uses fetch() to POST the file to the FastAPI endpoint /api/analyze.

JS writes the response to a hidden Dash component to trigger a callback update in the UI.

D. LLM Service (llm_service.py)
Use OpenAI Whisper (`whisper-1`) for transcription and an OpenAI GPT model (e.g., `gpt-4o-mini`) for scoring/feedback.

Prompt Engineering:

Role: Strict Levantine Arabic Teacher.

Task: Analyze pronunciation.

Output Format: Strict JSON { "transcription": "...", "score": int, "feedback": "..." }.

Specifics: Check for glottal stop usage for 'Qaf'.

5. Coding Standards
Type Hinting: Use Python type hints (e.g., def func(x: str) -> dict:) everywhere.

Async/Await: Use async def for FastAPI routes.

Environment Variables: Never hardcode API keys. Use os.environ.get("OPENAI_API_KEY").

Error Handling: Wrap API calls in try/except blocks to handle API quotas or network failures gracefully.

6. Deployment (Render.com)
The start command must be: uvicorn main:server --host 0.0.0.0 --port $PORT

Ensure ffmpeg is not required if possible (send raw bytes to OpenAI), but if needed, note it for the Dockerfile.

## 7. Local Development
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Set the environment variables:
   ```bash
   export OPENAI_API_KEY="your-key"
   # Optional overrides:
   # export OPENAI_MODEL_TRANSCRIBE="whisper-1"
   # export OPENAI_MODEL_EVAL="gpt-4o-mini"
   # Optional: enable WhatsApp voice notes via Twilio
   # export TWILIO_ACCOUNT_SID="your-sid"
   # export TWILIO_AUTH_TOKEN="your-token"
   ```
3. Run the app locally:
   ```bash
   uvicorn main:server --host 0.0.0.0 --port 8000 --reload
   ```
4. Open http://localhost:8000 and tap **Record** to send audio to `/api/analyze`.

## 8. WhatsApp Voice via Twilio (optional)
- Set environment variables `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` so the server can fetch media from Twilio.
- Point your Twilio WhatsApp sandbox/number webhook to `POST https://<your-domain>/api/whatsapp`.
- Send a WhatsApp voice note; the webhook downloads the media, runs the same analysis pipeline, and replies with a TwiML message containing transcription, score, and feedback.

## 9. Deploying to Render and connecting Twilio
- Render setup: push the repo, select “Web Service”, use the included `render.yaml`, and set env vars: `OPENAI_API_KEY`, optional `OPENAI_MODEL_TRANSCRIBE`/`OPENAI_MODEL_EVAL`, and `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN` for WhatsApp.
- Start command is already set to `uvicorn main:server --host 0.0.0.0 --port $PORT`.
- After deploy, copy the Render service URL (e.g., `https://your-app.onrender.com`) and set the Twilio WhatsApp sandbox/number webhook to `POST https://your-app.onrender.com/api/whatsapp`.
- Only OpenAI models are used (Whisper + GPT). No Gemini models are required or used in any deployment.
