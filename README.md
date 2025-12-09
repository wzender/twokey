## 1. Project Overview
We are building a mobile-first web application (PWA) to help students learn Levantine Arabic pronunciation.

Core user journey:
1. The app presents a phrase in the user's native language (e.g., Hebrew).
2. The user records the translation in the learned language (e.g., Levantine Arabic).
3. After submitting (no streaming), the app analyzes the recording with Gemini.
4. The result (transcription, score, feedback) is shown in the results pane.

## 2. Tech Stack & Architecture
* **Backend:** FastAPI (for high-performance API endpoints and async handling).
* **Frontend:** Dash (Plotly) for the UI, mounted *inside* the FastAPI application.
* **AI:** OpenAI Whisper for transcription + GPT (e.g., `gpt-4o-mini`) for scoring/feedback.
* **Deployment:** Render.com (Python Environment).
* **Audio Handling:** JavaScript (MediaRecorder API) via Dash Clientside Callbacks.

## 3. Directory Structure
Adhere strictly to this file structure:
```text
/
├── assets/
│   ├── style.css           # Mobile-responsive styling
│   └── audio_recorder.js   # Clientside logic for Microphone access
├── app.py                  # Dash application definition (UI Layout)
├── main.py                 # FastAPI entry point (Mounts Dash here)
├── gemini_service.py       # Interacts with Google Gemini API
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

D. Gemini Service (gemini_service.py)
Use the gemini-1.5-flash model (it is multimodal and accepts audio directly).

Prompt Engineering:

Role: Strict Levantine Arabic Teacher.

Task: Analyze pronunciation.

Output Format: Strict JSON { "transcription": "...", "score": int, "feedback": "..." }.

Specifics: Check for glottal stop usage for 'Qaf'.

5. Coding Standards
Type Hinting: Use Python type hints (e.g., def func(x: str) -> dict:) everywhere.

Async/Await: Use async def for FastAPI routes.

Environment Variables: Never hardcode API keys. Use os.environ.get("GEMINI_API_KEY").

Error Handling: Wrap API calls in try/except blocks to handle API quotas or network failures gracefully.

6. Deployment (Render.com)
The start command must be: uvicorn main:server --host 0.0.0.0 --port $PORT

Ensure ffmpeg is not required if possible (send raw bytes to Gemini), but if needed, note it for the Dockerfile.

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
   ```
3. Run the app locally:
   ```bash
   uvicorn main:server --host 0.0.0.0 --port 8000 --reload
   ```
4. Open http://localhost:8000 and tap **Record** to send audio to `/api/analyze`.
