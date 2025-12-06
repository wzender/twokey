from __future__ import annotations

import asyncio
import io
import json
import os
from typing import Any, Dict

from openai import OpenAI

TRANSCRIBE_MODEL = os.environ.get("OPENAI_MODEL_TRANSCRIBE", "whisper-1")
EVAL_MODEL = os.environ.get("OPENAI_MODEL_EVAL", "gpt-4o-mini")

SYSTEM_PROMPT = (
    "You are a strict Levantine Arabic pronunciation and translation coach. "
    "Use the transcript to judge translation accuracy and provide concise, "
    "actionable pronunciation feedback (focus on Levantine phonemes like Qaf glottal stop, Haa, and 'Ayn). "
    "Return STRICT JSON with keys transcription, score (0-100), and feedback. "
    "Score reflects overall pronunciation quality and translation accuracy."
)


def _client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def _transcribe(client: OpenAI, audio_bytes: bytes) -> str:
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "recording.wav"
    transcript = client.audio.transcriptions.create(
        model=TRANSCRIBE_MODEL,
        file=audio_file,
        response_format="text",
    )
    text = transcript.strip()
    if not text:
        raise ValueError("Transcription is empty.")
    return text


def _evaluate(client: OpenAI, transcription: str, phrase: str | None, hint: str | None) -> Dict[str, Any]:
    context = []
    if phrase:
        context.append(f"Target meaning (native phrase): {phrase}")
    if hint:
        context.append(f"Prompt to user: {hint}")
    context_text = "\n".join(context) if context else "No target phrase provided."

    completion = client.chat.completions.create(
        model=EVAL_MODEL,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"{context_text}\n"
                    f"Transcription: {transcription}\n"
                    "Return JSON with transcription, score, feedback."
                ),
            },
        ],
    )
    text = completion.choices[0].message.content or ""

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Evaluation model returned non-JSON response.") from exc

    transcription_out = data.get("transcription", transcription).strip()
    feedback = data.get("feedback", "").strip()
    score = data.get("score")

    if feedback == "" or score is None:
        raise ValueError("Evaluation response missing required fields.")

    try:
        score_int = int(score)
    except (TypeError, ValueError) as exc:  # noqa: PERF203
        raise ValueError("Score must be an integer.") from exc

    return {
        "transcription": transcription_out,
        "feedback": feedback,
        "score": max(0, min(score_int, 100)),
    }


def _run_model(audio_bytes: bytes, phrase: str | None, hint: str | None) -> Dict[str, Any]:
    client = _client()
    transcription = _transcribe(client, audio_bytes)
    return _evaluate(client, transcription, phrase, hint)


async def analyze_audio(
    audio_bytes: bytes, phrase: str | None = None, hint: str | None = None
) -> Dict[str, Any]:
    """
    Run pronunciation analysis using Whisper for transcription, then an LLM for scoring/feedback.
    Wrapped in a thread to avoid blocking the event loop.
    """

    return await asyncio.to_thread(_run_model, audio_bytes, phrase, hint)
