from __future__ import annotations

import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from app import app
from gemini_service import analyze_audio

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


# Mount Dash under the root path after API routes are registered.
server.mount("/", WSGIMiddleware(app.server))


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:server", host="0.0.0.0", port=port, reload=True)
