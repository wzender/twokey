## Levantine Pronunciation Coach (WhatsApp)

Send a voice note on WhatsApp and get instant transcription + pronunciation feedback for Levantine Arabic. The FastAPI app now acts as a WhatsApp webhook instead of serving a Dash UI.

### How it works
- WhatsApp Cloud API delivers audio messages to `POST /webhook`.
- The bot downloads the media, runs Whisper + GPT scoring via `gemini_service.py`, and replies with scores/feedback as a WhatsApp text message.
- `/api/analyze` remains available for manual audio POSTs; `/api/tts` returns synthesized speech if you want to play feedback elsewhere.

### Environment variables
- `OPENAI_API_KEY` – required for transcription + scoring.
- WhatsApp (reference naming): `ACCESS_TOKEN` (permanent), `PHONE_NUMBER_ID`, `VERIFY_TOKEN`, `APP_SECRET` (used to verify `X-Hub-Signature-256`), `VERSION` (Graph version, e.g., `v22.0`). Legacy fallbacks (`WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_GRAPH_VERSION`) are also read.
- Optional AI tuning: `OPENAI_MODEL_TRANSCRIBE`, `OPENAI_MODEL_EVAL`, `OPENAI_MODEL_TTS`, `OPENAI_TTS_VOICE`.

### Run locally with ngrok (per the python-whatsapp-bot flow)
Follow https://github.com/daveebbelaar/python-whatsapp-bot/tree/main?tab=readme-ov-file#launch-ngrok for the Meta-side setup; the steps below map to this app.
1) Install deps and export env vars:
```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...
export WHATSAPP_TOKEN=...
export WHATSAPP_PHONE_NUMBER_ID=...
export WHATSAPP_VERIFY_TOKEN=some-secret
```
2) Start the API:
```bash
uvicorn main:server --host 0.0.0.0 --port 8000 --reload
```
3) Expose with ngrok (see the linked guide): `ngrok http 8000`.
4) In Meta > WhatsApp > Configuration, set the webhook URL to `https://<ngrok-id>.ngrok.io/webhook` with `WHATSAPP_VERIFY_TOKEN`. Subscribe to `messages` for your phone number ID.

### Usage
- Send a voice note to the connected WhatsApp number. The bot replies with:
  - Transcription in Hebrew transliteration
  - Translation accuracy score and pronunciation score (0-100)
  - Concise feedback on what to fix
- Text messages receive a short instruction on how to use the bot.

### Deploy
Render start command remains:
```bash
uvicorn main:server --host 0.0.0.0 --port $PORT
```
