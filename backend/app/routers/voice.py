"""Voice proxy (Phase 17 ASR + Phase 18 TTS). Mounted at /api/voice.

A thin proxy so the Bhashini credentials never reach the browser:
  - POST /transcribe : short audio clip -> Hindi transcript (ASR).
  - POST /speak      : Hindi text -> spoken audio (TTS).

Both require authentication (the quota-limited external call must not be hit
anonymously; any role may use it) and return typed {code,message} errors so the
frontend can fall back deliberately. TTS clips are cached briefly per-process
because confirmation/status copy repeats often.
"""
import base64
import time
from threading import Lock

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.config import get_settings
from app.core.deps import get_current_user
from app.models import User
from app.services.bhashini_client import BhashiniError, synthesize, transcribe

router = APIRouter(prefix="/voice", tags=["Voice"])

# Map an uploaded content-type to the audioFormat hint Bhashini expects.
_FORMAT_BY_MIME = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/flac": "flac",
}


def _too_large(limit: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail={"code": "too_large", "message": f"Audio clip exceeds {limit} bytes."},
    )


def _bhashini_http_error(exc: BhashiniError) -> HTTPException:
    """Map a BhashiniError to HTTP. "not_configured" is a soft, expected state
    (no creds) -> 503; any real upstream failure -> 502. Both carry the code so
    the client can fall back."""
    code_status = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if exc.code == "not_configured"
        else status.HTTP_502_BAD_GATEWAY
    )
    return HTTPException(status_code=code_status, detail={"code": exc.code, "message": exc.message})


@router.post("/transcribe")
def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Transcribe a short Hindi audio clip via Bhashini.

    Success -> {"transcript": str, "language": "hi"}.
    Failure -> 4xx/5xx with detail={"code","message"} so the frontend can fall
    back deliberately instead of guessing from an empty string.
    """
    settings = get_settings()
    limit = settings.voice_max_upload_bytes

    # Reject oversized uploads before reading the whole body into memory.
    if audio.size is not None and audio.size > limit:
        raise _too_large(limit)
    data = audio.file.read()
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_audio", "message": "No audio was received."},
        )
    if len(data) > limit:
        raise _too_large(limit)

    mime = (audio.content_type or "").split(";")[0].strip().lower()
    audio_format = _FORMAT_BY_MIME.get(mime, "wav")

    try:
        transcript = transcribe(data, source_language="hi", audio_format=audio_format)
    except BhashiniError as exc:
        raise _bhashini_http_error(exc)

    return {"transcript": transcript, "language": "hi"}


# --- TTS (Phase 18) -------------------------------------------------------
# Small per-process TTL cache: confirmation/status copy repeats a lot, so we
# skip re-calling Bhashini for an identical string within the TTL window.
_TTS_LANG = "hi"
_TTS_GENDER = "female"
_TTS_CACHE: dict[tuple, tuple[bytes, str, float]] = {}
_TTS_CACHE_LOCK = Lock()


def _cache_get(key: tuple) -> tuple[bytes, str] | None:
    with _TTS_CACHE_LOCK:
        hit = _TTS_CACHE.get(key)
        if hit is None:
            return None
        audio, mime, expires_at = hit
        if time.monotonic() > expires_at:
            _TTS_CACHE.pop(key, None)
            return None
        return audio, mime


def _cache_put(key: tuple, audio: bytes, mime: str, ttl: int) -> None:
    with _TTS_CACHE_LOCK:
        _TTS_CACHE[key] = (audio, mime, time.monotonic() + ttl)


def clear_tts_cache() -> None:
    """Clear the TTS cache (used by tests)."""
    with _TTS_CACHE_LOCK:
        _TTS_CACHE.clear()


class SpeakRequest(BaseModel):
    text: str = Field(..., max_length=2000)


@router.post("/speak")
def speak(
    body: SpeakRequest,
    current_user: User = Depends(get_current_user),
):
    """Speak a short Hindi string via Bhashini TTS.

    Success -> {"audio_base64": str, "mime": "audio/wav", "language": "hi",
                "cached": bool}. The on-screen text always remains, so a failure
    only removes the audio convenience.
    """
    settings = get_settings()
    text = body.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_text", "message": "No text was provided to speak."},
        )

    key = (text, _TTS_LANG, _TTS_GENDER)
    cached = _cache_get(key)
    if cached is not None:
        audio, mime = cached
        return {
            "audio_base64": base64.b64encode(audio).decode("ascii"),
            "mime": mime,
            "language": _TTS_LANG,
            "cached": True,
        }

    try:
        audio, mime = synthesize(text, lang=_TTS_LANG, gender=_TTS_GENDER)
    except BhashiniError as exc:
        raise _bhashini_http_error(exc)

    _cache_put(key, audio, mime, settings.voice_tts_cache_ttl_seconds)
    return {
        "audio_base64": base64.b64encode(audio).decode("ascii"),
        "mime": mime,
        "language": _TTS_LANG,
        "cached": False,
    }
