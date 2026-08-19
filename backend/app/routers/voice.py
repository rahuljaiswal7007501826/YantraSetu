"""Voice transcription proxy (Phase 17). Mounted at /api/voice.

A thin proxy so the Bhashini credentials never reach the browser. Accepts a
short audio clip (multipart), forwards it to Bhashini, and returns the
transcript - or a clear, typed error the frontend uses to trigger its own
fallback (Web Speech API, then manual text entry). Authentication is required so
the quota-limited external call can't be hit anonymously; any role may use it.
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.core.deps import get_current_user
from app.models import User
from app.services.bhashini_client import BhashiniError, transcribe

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
        # "not_configured" is a soft, expected state (no creds) -> 503; any real
        # upstream failure -> 502. Both carry the code so the client can fall back.
        code_status = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if exc.code == "not_configured"
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=code_status, detail={"code": exc.code, "message": exc.message})

    return {"transcript": transcript, "language": "hi"}
