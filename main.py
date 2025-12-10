from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict
from urllib.parse import quote_plus
import httpx
from xml.sax.saxutils import escape
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import Response
from app import PHRASES, app
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
    logging.info(
        "Analyze API: received file content_type=%s size=%d phrase_provided=%s",
        file.content_type,
        len(audio_bytes),
        bool(phrase),
    )
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


def _generate_tts_bytes(content: str) -> bytes:
    try:
        client = _tts_client()
        logging.info("Generating TTS audio: %d characters", len(content))
        speech = client.audio.speech.create(
            model=os.environ.get("OPENAI_MODEL_TTS", "gpt-4o-mini-tts"),
            voice=os.environ.get("OPENAI_TTS_VOICE", "alloy"),
            input=content,
        )
    except Exception as exc:  # noqa: BLE001
        logging.exception("TTS generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate audio.") from exc

    return speech.read()


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
    Fetch media from a Twilio-provided URL using an async HTTP client.
    """
    # If Twilio provides a relative URL, resolve it to an absolute one.
    if not url.startswith("http"):
        url = f"https://api.twilio.com{url}"
        logging.info("Resolved relative Twilio media URL to absolute: %s", url)
    else:
        logging.info("Using Twilio media URL: %s", url)

    sid, token = _twilio_auth()
    auth = httpx.BasicAuth(sid, token)

    # Twilio media URLs require basic auth with the account SID and token.
    async with httpx.AsyncClient(auth=auth, timeout=30.0) as client:
        try:
            logging.info("Requesting media from Twilio (auth SID only)")
            response = await client.get(url, follow_redirects=True)
            logging.info(
                "Twilio media response: status=%s content_length=%s",
                response.status_code,
                response.headers.get("Content-Length"),
            )
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.content
        except httpx.RequestError as exc:
            logging.error(f"Failed to fetch media from Twilio via httpx: {exc}")
            raise HTTPException(
                status_code=502, detail="Failed to fetch media from Twilio."
            ) from exc
        except httpx.HTTPStatusError as exc:
            logging.error(
                "Twilio media fetch failed: status=%s body=%s",
                exc.response.status_code,
                exc.response.text,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch media from Twilio: {exc.response.status_code}",
            ) from exc


def _twiml_message(body: str, media_url: str | None = None) -> Response:
    """
    Return a minimal TwiML Message response (optionally with media).
    """
    body_xml = f"<Body>{escape(body)}</Body>" if body else ""
    media_xml = f"<Media>{escape(media_url)}</Media>" if media_url else ""
    xml = f"<Response><Message>{body_xml}{media_xml}</Message></Response>"
    return Response(content=xml, media_type="application/xml")


@server.post("/api/tts")
async def tts(text: Dict[str, str]) -> Response:
    """
    Convert Hebrew feedback text to speech using OpenAI TTS and return audio bytes.
    """
    content = text.get("text") if isinstance(text, dict) else None
    if not content or not isinstance(content, str):
        raise HTTPException(status_code=400, detail="Missing text for TTS.")

    logging.info("TTS endpoint invoked: text_length=%d", len(content))
    audio_bytes = _generate_tts_bytes(content)
    logging.info("TTS audio generated: %d bytes", len(audio_bytes))
    headers = {"Content-Disposition": 'attachment; filename="feedback.mp3"'}
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)


@server.post("/api/whatsapp")
async def whatsapp_voice_webhook(
    request: Request,
    num_media: int = Form(0, alias="NumMedia"),
    media_url: str | None = Form(None, alias="MediaUrl0"),
    media_content_type: str | None = Form(None, alias="MediaContentType0"),
    body: str | None = Form(None, alias="Body"),
    sender: str | None = Form(None, alias="From"),
) -> Response:
    """
    Twilio webhook to accept WhatsApp voice notes and return feedback via TwiML.
    """
    message_text = (body or "").strip().lower()
    logging.info("WhatsApp webhook invoked: sender=%s media_url=%s content_type=%s body=%s", sender, media_url, media_content_type, message_text)
    logging.info(
        "WhatsApp form details: NumMedia=%s From=%s ContentType=%s",
        num_media,
        sender,
        media_content_type,
    )

    # Step 1: Handle "start" to send the native phrase to practice.
    if not media_url and message_text == "start":
        phrase = PHRASES[0]["native"]
        instructions = (
            "היי! שלחו הודעת קול עם התרגום לערבית לבנטינית.\n"
            f"משפט לתרגול: {phrase}"
        )
        logging.info("Responding with start instructions and phrase")
        return _twiml_message(instructions)

    # Step 2: Handle missing media or non-audio.
    if num_media < 1 or not media_url:
        logging.warning("Missing media in WhatsApp request: num_media=%s media_url=%s", num_media, media_url)
        return _twiml_message('שלחו "start" לקבלת משפט, ואז שלחו הודעת קול עם התרגום.')

    if media_content_type and not media_content_type.startswith("audio/"):
        logging.warning("Invalid media content type: %s", media_content_type)
        return _twiml_message("ההודעה שקיבלתי אינה אודיו. שלחו הודעת קול חדשה.")

    # Step 3: Analyze the voice note against the practice phrase.
    phrase = PHRASES[0]
    try:
        logging.info("Downloading media from Twilio: %s", media_url)
        audio_bytes = await _download_twilio_media(media_url)
        logging.info("Media downloaded, %d bytes", len(audio_bytes))

        logging.info("Starting analysis with phrase context")
        result = await analyze_audio(
            audio_bytes,
            phrase=phrase["native"],
            hint=phrase.get("hint"),
            arabic_transliteration=phrase.get("arabic_transliteration"),
        )
        logging.info("Analysis completed: %s", result)
    except HTTPException as exc:
        logging.exception("HTTPException during WhatsApp analysis: %s", exc.detail)
        raise exc
    except Exception as exc:  # noqa: BLE001
        logging.exception("WhatsApp analysis failed with unexpected error")
        return _twiml_message("לא הצלחתי לנתח את ההודעה. נסו שוב מאוחר יותר.")

    transcription = result.get("transcription", "")
    score = result.get("score", 0)
    translation_score = result.get("translation_score", score)
    pronunciation_score = result.get("pronunciation_score", score)
    feedback = result.get("feedback", "")

    sender_text = f"{sender} " if sender else ""
    summary = (
        f"{sender_text}תמלול: {transcription}\n"
        f"ציון תרגום: {translation_score}/100 | ציון הגייה: {pronunciation_score}/100\n"
        f"משוב: {feedback}"
    )
    logging.info(
        "Summary prepared: transcription_len=%d feedback_len=%d translation_score=%s pronunciation_score=%s",
        len(transcription),
        len(feedback),
        translation_score,
        pronunciation_score,
    )

    # Build media URL for TTS so Twilio can fetch the audio response.
    base_url = str(request.base_url).rstrip("/")
    tts_payload = f"ציון {score}/100. {feedback}"
    tts_url = f"{base_url}/api/whatsapp/tts?text={quote_plus(tts_payload)}"
    logging.info("Responding with summary and TTS media URL: %s", tts_url)

    return _twiml_message(summary, media_url=tts_url)


@server.get("/api/whatsapp/tts")
async def whatsapp_tts(text: str | None = None) -> Response:
    """
    Serve TTS audio for WhatsApp replies. Used as the Media URL in TwiML.
    """
    if not text:
        raise HTTPException(status_code=400, detail="Missing text for TTS.")

    audio_bytes = _generate_tts_bytes(text)
    headers = {"Content-Disposition": 'attachment; filename="whatsapp-feedback.mp3"'}
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)


# Mount Dash under the root path after API routes are registered.
server.mount("/", WSGIMiddleware(app.server))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "10000"))
    uvicorn.run("main:server", host="0.0.0.0", port=port, reload=True)
