"""Bhashini (ULCA / Dhruva) ASR client - Phase 17.

Wraps the Government of India Bhashini speech-to-text pipeline. Kept fully
isolated from FastAPI (plain functions, no request objects) so it is trivial to
mock in tests and swap later.

Two-step ULCA flow:
  1. getModelsPipeline (config): POST the config URL with userID + ulcaApiKey
     headers; the response gives the ASR serviceId, the compute callbackUrl, and
     the inference auth header to use.
  2. compute: POST the callbackUrl with that auth header and the base64 audio;
     the response carries the transcript.

Any failure raises BhashiniError(code, message) so the caller can return a clean
typed error and the frontend can fall back gracefully.

NOTE: this is coded to Bhashini's documented contract but has NOT been verified
against a live account in this environment (no credentials, and the sandbox
cannot reach the government API). Audio format / samplingRate / pipelineId may
need small per-account adjustments - see docs/assumptions.md.
"""
from __future__ import annotations

import base64

import httpx

from app.config import get_settings

_ASR_TASK = "asr"
_TIMEOUT = httpx.Timeout(20.0)


class BhashiniError(Exception):
    """A failure talking to Bhashini. `code` is a short machine-readable tag."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _get_pipeline(source_language: str) -> dict:
    """Step 1: fetch the ASR pipeline config (serviceId + callback + auth header)."""
    settings = get_settings()
    headers = {
        "userID": settings.bhashini_user_id,
        "ulcaApiKey": settings.bhashini_api_key,
        "Content-Type": "application/json",
    }
    body = {
        "pipelineTasks": [
            {"taskType": _ASR_TASK, "config": {"language": {"sourceLanguage": source_language}}}
        ],
        "pipelineRequestConfig": {"pipelineId": settings.bhashini_pipeline_id},
    }
    try:
        resp = httpx.post(settings.bhashini_config_url, json=body, headers=headers, timeout=_TIMEOUT)
    except httpx.HTTPError as exc:
        raise BhashiniError("config_unreachable", f"Bhashini config call failed: {exc}") from exc
    if resp.status_code != 200:
        raise BhashiniError("config_http_error", f"Bhashini config returned HTTP {resp.status_code}.")
    try:
        data = resp.json()
        task = next(t for t in data["pipelineResponseConfig"] if t["taskType"] == _ASR_TASK)
        service_id = task["config"][0]["serviceId"]
        endpoint = data["pipelineInferenceAPIEndPoint"]
        api_key = endpoint["inferenceApiKey"]  # {"name": ..., "value": ...}
        return {
            "service_id": service_id,
            "callback_url": endpoint["callbackUrl"],
            "auth_name": api_key["name"],
            "auth_value": api_key["value"],
        }
    except (KeyError, IndexError, StopIteration, ValueError) as exc:
        raise BhashiniError("config_parse_error", f"Unexpected Bhashini config shape: {exc}") from exc


def transcribe(
    audio_bytes: bytes,
    *,
    source_language: str = "hi",
    audio_format: str = "wav",
    sampling_rate: int = 16000,
) -> str:
    """Transcribe `audio_bytes` to text. Raises BhashiniError on any failure."""
    settings = get_settings()
    if not settings.bhashini_configured:
        raise BhashiniError("not_configured", "Bhashini credentials are not configured.")

    pipeline = _get_pipeline(source_language)
    audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
    body = {
        "pipelineTasks": [
            {
                "taskType": _ASR_TASK,
                "config": {
                    "language": {"sourceLanguage": source_language},
                    "serviceId": pipeline["service_id"],
                    "audioFormat": audio_format,
                    "samplingRate": sampling_rate,
                },
            }
        ],
        "inputData": {"audio": [{"audioContent": audio_b64}]},
    }
    headers = {pipeline["auth_name"]: pipeline["auth_value"], "Content-Type": "application/json"}
    try:
        resp = httpx.post(pipeline["callback_url"], json=body, headers=headers, timeout=_TIMEOUT)
    except httpx.HTTPError as exc:
        raise BhashiniError("compute_unreachable", f"Bhashini compute call failed: {exc}") from exc
    if resp.status_code != 200:
        raise BhashiniError("compute_http_error", f"Bhashini compute returned HTTP {resp.status_code}.")
    try:
        data = resp.json()
        transcript = data["pipelineResponse"][0]["output"][0]["source"]
    except (KeyError, IndexError, ValueError) as exc:
        raise BhashiniError("compute_parse_error", f"Unexpected Bhashini compute shape: {exc}") from exc
    return (transcript or "").strip()
