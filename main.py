from __future__ import annotations

import logging
import os
from typing import Any, Dict
from xml.sax.saxutils import escape

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import Response

from app import app
from llm_service import analyze_audio
from openai import OpenAI

server = FastAPI(title="Levantine Pronunciation Coach API")

# Allow local development from different origins (e.g., Dash hot reload).
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@server.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    phrase: str | None = Form(None),
    hint: str | None = Form(None),
    arabic_transliteration: str | None = Form(None),
) -> Dict[str, Any]:
    """
    Receive an uploaded WAV file from the frontend, run Gemini analysis,
    and return structured feedback. Accepts the native phrase as context.
    """
    if file.content_type not in {"audio/wav", "audio/x-wav", "audio/wave"}:
        raise HTTPException(status_code=400, detail="File must be a WAV audio.")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received.")

    try:
        result = await analyze_audio(
            audio_bytes,
            phrase=phrase,
            hint=hint,
            arabic_transliteration=arabic_transliteration,
        )
    except ValueError as exc:
        # Likely configuration issues such as missing API key.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("Gemini analysis failed")
        raise HTTPException(status_code=500, detail="Failed to analyze audio.") from exc

    return result


def _tts_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def _twilio_auth() -> tuple[str, str]:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise HTTPException(
            status_code=500,
            detail="TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN is missing.",
        )
    return sid, token


async def _download_twilio_media(url: str) -> bytes:
    """
    Fetch media from a Twilio-provided URL (requires basic auth).
    """
    sid, token = _twilio_auth()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, auth=(sid, token))
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:  # noqa: B904
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch media from Twilio: {exc.response.status_code}",
            ) from exc
        return resp.content


def _twiml_message(body: str) -> Response:
    """
    Return a minimal TwiML Message response.
    """
    xml = f"<Response><Message>{escape(body)}</Message></Response>"
    return Response(content=xml, media_type="application/xml")


@server.post("/api/tts")
async def tts(text: Dict[str, str]) -> Response:
    """
    Convert Hebrew feedback text to speech using OpenAI TTS and return audio bytes.
    """
    content = text.get("text") if isinstance(text, dict) else None
    if not content or not isinstance(content, str):
        raise HTTPException(status_code=400, detail="Missing text for TTS.")

    try:
        client = _tts_client()
        speech = client.audio.speech.create(
            model=os.environ.get("OPENAI_MODEL_TTS", "gpt-4o-mini-tts"),
            voice=os.environ.get("OPENAI_TTS_VOICE", "alloy"),
            input=content,
        )
    except Exception as exc:  # noqa: BLE001
        logging.exception("TTS generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate audio.") from exc

    audio_bytes = speech.read()
    headers = {"Content-Disposition": 'attachment; filename="feedback.mp3"'}
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)


@server.post("/api/whatsapp")
async def whatsapp_voice_webhook(
    num_media: int = Form(0, alias="NumMedia"),
    media_url: str | None = Form(None, alias="MediaUrl0"),
    media_content_type: str | None = Form(None, alias="MediaContentType0"),
    body: str | None = Form(None, alias="Body"),
    sender: str | None = Form(None, alias="From"),
) -> Response:
    """
    Twilio webhook to accept WhatsApp voice notes and return feedback via TwiML.
    """
    if num_media < 1 or not media_url:
        return _twiml_message("שלחו הודעת קול בוואטסאפ כדי לקבל משוב הגייה.")

    if media_content_type and not media_content_type.startswith("audio/"):
        return _twiml_message("ההודעה שקיבלתי אינה אודיו. שלחו הודעת קול חדשה.")

    try:
        audio_bytes = await _download_twilio_media(media_url)
        result = await analyze_audio(
            audio_bytes,
            phrase=body,
            hint=None,
            arabic_transliteration=None,
        )
    except HTTPException as exc:
        # Pass along explicit HTTP errors (e.g., missing creds).
        raise exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("WhatsApp analysis failed")
        return _twiml_message("לא הצלחתי לנתח את ההודעה. נסו שוב מאוחר יותר.")

    transcription = result.get("transcription", "")
    score = result.get("score", 0)
    feedback = result.get("feedback", "")

    sender_text = f"{sender} " if sender else ""
    reply = (
        f"{sender_text}תמלול: {transcription}\n"
        f"ציון כללי: {score}/100\n"
        f"משוב: {feedback}"
    )
    return _twiml_message(reply)


# Mount Dash under the root path after API routes are registered.
server.mount("/", WSGIMiddleware(app.server))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:server", host="0.0.0.0", port=port, reload=True)
