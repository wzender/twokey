from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Dict, List, Tuple

import httpx
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from openai import OpenAI

from gemini_service import analyze_audio

logger = logging.getLogger("twokey.api")
logging.basicConfig(level=logging.INFO)

server = FastAPI(title="Levantine Pronunciation Coach - WhatsApp Bot")

# Allow local development and ngrok callbacks.
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_CONTENT_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/ogg",
    "application/ogg",
    "audio/webm",
    "audio/mpeg",
}


def _get_env(primary: str, fallback: List[str] | None = None, default: str | None = None) -> str | None:
    keys = [primary] + (fallback or [])
    for key in keys:
        value = os.environ.get(key)
        if value:
            return value
    return default


def _require_env(primary: str, fallback: List[str] | None = None) -> str:
    value = _get_env(primary, fallback=fallback)
    if not value:
        names = [primary] + (fallback or [])
        raise HTTPException(status_code=500, detail=f"{' / '.join(names)} is not set.")
    return value


GRAPH_VERSION = _get_env("VERSION", fallback=["WHATSAPP_GRAPH_VERSION"], default="v20.0")
GRAPH_API_BASE = _get_env("GRAPH_API_BASE") or f"https://graph.facebook.com/{GRAPH_VERSION}"
VERIFY_TOKEN = _get_env("VERIFY_TOKEN", fallback=["WHATSAPP_VERIFY_TOKEN"])
APP_SECRET = _get_env("APP_SECRET", fallback=["WHATSAPP_APP_SECRET"])


def _filename_for_content_type(content_type: str | None, default: str = "recording") -> str:
    if not content_type:
        return f"{default}.wav"
    mapping = {
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/wave": "wav",
        "audio/ogg": "ogg",
        "application/ogg": "ogg",
        "audio/webm": "webm",
        "audio/mpeg": "mp3",
    }
    ext = mapping.get(content_type.lower(), "wav")
    return f"{default}.{ext}"


async def _send_whatsapp_text(to_number: str, body: str) -> None:
    token = _require_env("ACCESS_TOKEN", fallback=["WHATSAPP_TOKEN"])
    phone_number_id = _require_env("PHONE_NUMBER_ID", fallback=["WHATSAPP_PHONE_NUMBER_ID"])
    url = f"{GRAPH_API_BASE}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body[:4000]},
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            logger.info("Sent WhatsApp message to %s status=%s", to_number, resp.status_code)
    except httpx.TimeoutException:
        logger.error("Timeout occurred while sending WhatsApp message")
        raise
    except httpx.HTTPStatusError as exc:
        logger.error(
            "WhatsApp send failed status=%s body=%s", exc.response.status_code, exc.response.text
        )
        raise
    except httpx.RequestError as exc:
        logger.error("Request failed while sending WhatsApp message: %s", exc)
        raise


async def _fetch_media(media_id: str, mime_type_hint: str | None) -> Tuple[bytes, str]:
    token = _require_env("ACCESS_TOKEN", fallback=["WHATSAPP_TOKEN"])
    meta_url = f"{GRAPH_API_BASE}/{media_id}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        meta_resp = await client.get(meta_url, params={"access_token": token})
        meta_resp.raise_for_status()
        meta_json = meta_resp.json()
        media_url = meta_json.get("url")
        mime_type = mime_type_hint or meta_json.get("mime_type")
        if not media_url:
            raise ValueError("Media URL missing in WhatsApp response.")

        media_resp = await client.get(media_url, headers={"Authorization": f"Bearer {token}"})
        media_resp.raise_for_status()
        file_name = _filename_for_content_type(mime_type, default="voice_note")
        return media_resp.content, file_name


def _format_feedback(result: Dict[str, Any]) -> str:
    transcription = result.get("transcription") or ""
    feedback = result.get("feedback") or ""
    translation_score = result.get("translation_score", result.get("score", 0)) or 0
    pronunciation_score = result.get("pronunciation_score", result.get("score", 0)) or 0
    return (
        f"תמלול: {transcription}\n"
        f"דיוק תרגום: {translation_score}%\n"
        f"הגייה: {pronunciation_score}%\n"
        f"משוב: {feedback}"
    )


def _is_valid_signature(app_secret: str, signature_header: str | None, body: bytes) -> bool:
    if not signature_header or "=" not in signature_header:
        return False
    algo, provided_sig = signature_header.split("=", 1)
    if algo != "sha256":
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_sig)


async def _handle_audio_message(message: Dict[str, Any]) -> None:
    sender = message.get("from")
    audio_block = message.get("audio") or message.get("voice") or {}
    media_id = audio_block.get("id")
    mime_type = audio_block.get("mime_type")
    if not sender or not media_id:
        logger.warning("Audio message missing sender or media id.")
        return

    try:
        audio_bytes, file_name = await _fetch_media(media_id, mime_type)
        result = await analyze_audio(audio_bytes, file_name=file_name)
        response_text = _format_feedback(result)
        await _send_whatsapp_text(sender, response_text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process WhatsApp audio message: %s", exc)
        await _send_whatsapp_text(
            sender,
            "שגיאה בניתוח ההקלטה. ודאו שהקלטתם הודעת קול ברורה ונסו שוב.",
        )


async def _handle_text_message(message: Dict[str, Any]) -> None:
    sender = message.get("from")
    if not sender:
        return
    await _send_whatsapp_text(
        sender,
        "שלחו הודעת קול (Voice Note) כדי לקבל תמלול ומשוב הגייה בערבית לבנטינית.",
    )


async def _process_whatsapp_payload(payload: Dict[str, Any]) -> None:
    entries = payload.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            for message in messages:
                msg_type = message.get("type")
                if msg_type == "audio" or msg_type == "voice":
                    await _handle_audio_message(message)
                elif msg_type == "text":
                    await _handle_text_message(message)
                else:
                    sender = message.get("from")
                    if sender:
                        await _send_whatsapp_text(
                            sender,
                            "קיבלתי את ההודעה. כרגע נתמכות רק הודעות קוליות לקבלת משוב.",
                        )


@server.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge", "")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@server.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    body_bytes = await request.body()
    if APP_SECRET:
        signature = request.headers.get("x-hub-signature-256") or request.headers.get("X-Hub-Signature-256")
        if not _is_valid_signature(APP_SECRET, signature, body_bytes):
            raise HTTPException(status_code=403, detail="Invalid signature.")
    payload = json.loads(body_bytes or b"{}")
    background_tasks.add_task(_process_whatsapp_payload, payload)
    return JSONResponse({"status": "accepted"})


@server.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@server.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    phrase: str | None = Form(None),
    hint: str | None = Form(None),
    arabic_transliteration: str | None = Form(None),
) -> Dict[str, Any]:
    """
    Receive an uploaded audio file (wav/ogg/webm/mp3), run Gemini analysis,
    and return structured feedback. Accepts the native phrase as context.
    """
    logger.info(
        "/api/analyze called filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )
    print(f"[analyze] received file={file.filename} content_type={file.content_type}")
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="File must be an audio clip (wav/ogg/webm/mp3).")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received.")
    logger.info("/api/analyze audio_size_bytes=%d", len(audio_bytes))
    print(f"[analyze] audio bytes={len(audio_bytes)}")

    try:
        result = await analyze_audio(
            audio_bytes,
            phrase=phrase,
            hint=hint,
            arabic_transliteration=arabic_transliteration,
            file_name=file.filename or _filename_for_content_type(file.content_type),
        )
        logger.info(
            "/api/analyze succeeded transcription_len=%s score=%s translation_score=%s pronunciation_score=%s",
            len(result.get("transcription", "") or ""),
            result.get("score"),
            result.get("translation_score"),
            result.get("pronunciation_score"),
        )
        print(
            f"[analyze] success scores t={result.get('translation_score')} p={result.get('pronunciation_score')} avg={result.get('score')}"
        )
    except ValueError as exc:
        logger.error("ValueError during analysis: %s", exc, exc_info=True)
        print(f"[analyze] ValueError: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini analysis failed")
        print(f"[analyze] unexpected error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to analyze audio.") from exc

    return result


def _tts_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


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
        logger.info("/api/tts succeeded")
        print("[tts] success")
    except Exception as exc:  # noqa: BLE001
        logger.exception("TTS generation failed")
        print(f"[tts] error: {exc}")
        raise HTTPException(status_code=500, detail="Failed to generate audio.") from exc

    audio_bytes = speech.read()
    headers = {"Content-Disposition": 'attachment; filename=\"feedback.mp3\"'}
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:server", host="0.0.0.0", port=port, reload=True)
