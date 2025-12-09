## Deployment and Sandbox Setup

This guide walks you through creating a Render account for hosting and a Twilio WhatsApp sandbox for testing voice messages end-to-end.

### 1) Render (hosting)
1. Sign up at https://render.com/ (free tier is enough for testing).
2. Connect your GitHub repo and click **New +** → **Web Service**.
3. Repo/branch: select this project. Environment: **Python**.
4. Build command: `pip install -r requirements.txt`
5. Start command: `uvicorn main:server --host 0.0.0.0 --port $PORT`
6. Set environment variables:
   - `OPENAI_API_KEY` (required)
   - Optional overrides: `OPENAI_MODEL_TRANSCRIBE`, `OPENAI_MODEL_EVAL`
   - Twilio fetch auth: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` (needed for WhatsApp webhook)
   - You can also keep these in a local `.env` for development; Render needs them in the dashboard.
7. Deploy. Note the resulting public URL, e.g., `https://your-app.onrender.com`.

### 2) Twilio WhatsApp Sandbox (testing)
1. Sign up at https://www.twilio.com/ (free trial works for sandbox).
2. In the Twilio Console, go to **Messaging** → **Try it out** → **WhatsApp Sandbox**.
3. Follow the on-screen instructions to join the sandbox (send the provided join code from your WhatsApp to the Twilio sandbox number).
4. Set the **Sandbox Inbound Webhook** (When a message comes in) to:
   - URL: `https://your-app.onrender.com/api/whatsapp`
   - Method: `POST`
5. In **Settings**, copy your `Account SID` and `Auth Token` and set them in Render as env vars (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`).
6. The app will serve voiced feedback from `GET /api/whatsapp/tts` (Twilio will fetch this media URL provided in the webhook response).

### 3) Test the flow
1. From your joined WhatsApp number, send `start` to the Twilio sandbox number to receive the practice sentence (Hebrew).
2. Reply with a voice note containing your Levantine Arabic translation.
3. The webhook downloads the audio, runs transcription/feedback, and replies with both text and a voiced MP3 (served from `/api/whatsapp/tts`).
4. If you change the Render URL (redeploy), update the Twilio webhook URL accordingly.

### 4) Quick readiness checks (Render)
- After deploy, hit the root: `curl -I https://your-app.onrender.com` (should return 200 from the Dash UI).
- Check the WhatsApp webhook echoes TwiML:  
  `curl -X POST https://your-app.onrender.com/api/whatsapp -d "Body=start"`  
  You should get an XML `<Response>` with the practice sentence.
- If either check fails, verify env vars (`OPENAI_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`) and redeploy.
