from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import Response

from app import app
from gemini_service import analyze_audio
from openai import OpenAI

logger = logging.getLogger("twokey.api")
logging.basicConfig(level=logging.INFO)

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
    logger.info(
        "/api/analyze called filename=%s content_type=%s",
        file.filename,
        file.content_type,
    )
    print(f"[analyze] received file={file.filename} content_type={file.content_type}")
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
        logger.info("/api/analyze succeeded")
        print("[analyze] success")
    except ValueError as exc:
        # Likely configuration issues such as missing API key.
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
    headers = {"Content-Disposition": 'attachment; filename="feedback.mp3"'}
    return Response(content=audio_bytes, media_type="audio/mpeg", headers=headers)


# Mount Dash under the root path after API routes are registered.
server.mount("/", WSGIMiddleware(app.server))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:server", host="0.0.0.0", port=port, reload=True)
