from __future__ import annotations

import asyncio
import io
import json
import os
from typing import Any, Dict

from openai import OpenAI

TRANSCRIBE_MODEL = os.environ.get("OPENAI_MODEL_TRANSCRIBE", "whisper-1")
EVAL_MODEL = os.environ.get("OPENAI_MODEL_EVAL", "gpt-4o-mini")

SYSTEM_PROMPT_ENG = (
    "You are a strict Levantine Arabic pronunciation and translation coach. "
    "Use the transcript to judge translation accuracy and provide concise, "
    "actionable pronunciation feedback (focus on Levantine phonemes like Qaf glottal stop, Haa, and 'Ayn). "
    "Return STRICT JSON with keys transcription, score (0-100), and feedback. "
    "Score reflects overall pronunciation quality and translation accuracy."
)

SYSTEM_PROMPT = (
    "אתה מורה לערבית לבנטינית (הגייה ודיוק תרגום) לדוברי עברית. "
    "השתמש בתמלול כדי לבדוק אם התרגום נכון ולהחזיר משוב קצר, חד ופרקטי על ההגייה. "
    "התמקד באותיות שקשות לדוברי עברית: קוף חיכית/גלוטלית, אותיות מודגשות, ח'/ח, ר מגולגלת/גרונית, וע׳ין/עין. "
    "אל תשתמש באותיות ערביות כלל; השתמש בתעתיק עברי לפי המפה הבאה (תן גם רמזי הגייה): "
    "ا/أ/إ/آ→'א' או 'ע' רפויה; "
    "ب→'בּ' סגורה; "
    "ت→'ת' קלה; "
    "ث→'ת׳' (לעיתים נשמעת 'ס'); "
    "ج→'ג׳' (כמו ג'מייל), אפשר 'ג' קלה בדיאלקט; "
    "ح→'ח' עמוקה גרונית; "
    "خ→'ח׳' / 'כּ' חיכית, עם חיכוך עמוק; "
    "د→'ד'; "
    "ذ→'ד׳/ז׳' (th רפה); "
    "ر→'ר' מגולגלת או גרונית; "
    "ز→'ז'; "
    "س→'ס'; "
    "ش→'שׁ'; "
    "ص→'צ' מודגשת (חיכוך מודגש); "
    "ض→'ד׳' עמוקה/מצלצלת; "
    "ط→'ט' מודגשת; "
    "ظ→'ט׳/ז׳' מודגשת; "
    "ع→'ע' עמוקה, לוחצת; "
    "غ→'ע׳/ר׳' חיכית/וילונית; "
    "ف→'פ' שפתית; "
    "ق→'ק' אחורית/גלוטלית; "
    "ك→'כ' קדמית (לעיתים 'ק' רפה); "
    "ل→'ל'; "
    "م→'מ'; "
    "ن→'נ'; "
    "ه→'ה'; "
    "و→'ו' (חצי תנועה u/w); "
    "ي→'י' (חצי תנועה i/y). "
    "החזר JSON קפדני עם המפתחות transcription, score (0-100), feedback (בעברית). "
    "אם ניתנת arabic_transliteration השתמש בה כמשפט היעד המדויק להשוואת תרגום/הגייה. "
    "החזר גם translation_score (0-100) להערכת דיוק התרגום, ו-pronunciation_score (0-100) להערכת הגייה. "
    "score יכול להיות הממוצע בין שניהם. "
    "הציון משקף איכות הגייה ודיוק תרגום; המשוב ישים: אילו אותיות/הברות היו שגויות ואיזו אות עברית להשתמש כדי לתקן."
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


def _evaluate(
    client: OpenAI,
    transcription: str,
    phrase: str | None,
    hint: str | None,
    arabic_transliteration: str | None,
) -> Dict[str, Any]:
    context = []
    if phrase:
        context.append(f"Target meaning (native phrase): {phrase}")
    if hint:
        context.append(f"Prompt to user: {hint}")
    if arabic_transliteration:
        context.append(f"Target Arabic transliteration (reference pronunciation): {arabic_transliteration}")
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
                    f"Learner transcription: {transcription}\n"
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
    translation_score = data.get("translation_score", data.get("translationScore"))
    pronunciation_score = data.get("pronunciation_score", data.get("pronunciationScore"))

    if feedback == "":
        raise ValueError("Evaluation response missing required fields.")

    def _to_int(val: Any) -> int | None:
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    score_int = _to_int(score)
    translation_int = _to_int(translation_score)
    pronunciation_int = _to_int(pronunciation_score)

    # Derive missing scores sensibly.
    if score_int is None and translation_int is not None and pronunciation_int is not None:
        score_int = round((translation_int + pronunciation_int) / 2)
    if translation_int is None:
        translation_int = score_int
    if pronunciation_int is None:
        pronunciation_int = score_int
    if score_int is None:
        raise ValueError("Score must be an integer.")

    return {
        "transcription": transcription_out,
        "feedback": feedback,
        "score": max(0, min(score_int, 100)),
        "translation_score": max(0, min(translation_int or 0, 100)),
        "pronunciation_score": max(0, min(pronunciation_int or 0, 100)),
    }


def _run_model(
    audio_bytes: bytes,
    phrase: str | None,
    hint: str | None,
    arabic_transliteration: str | None,
) -> Dict[str, Any]:
    client = _client()
    transcription = _transcribe(client, audio_bytes)
    return _evaluate(client, transcription, phrase, hint, arabic_transliteration)


async def analyze_audio(
    audio_bytes: bytes,
    phrase: str | None = None,
    hint: str | None = None,
    arabic_transliteration: str | None = None,
) -> Dict[str, Any]:
    """
    Run pronunciation analysis using Whisper for transcription, then an LLM for scoring/feedback.
    Wrapped in a thread to avoid blocking the event loop.
    """

    return await asyncio.to_thread(
        _run_model,
        audio_bytes,
        phrase,
        hint,
        arabic_transliteration,
    )
