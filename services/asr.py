# services/asr.py
import mimetypes
import requests
from pathlib import Path

import config

GROQ_BASE = "https://api.groq.com/openai/v1"


def _mime_for_audio(path: Path) -> str:
    # reasonable default if mimetypes misses it
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "audio/wav"


def transcribe_groq(audio_path: Path, model: str = None) -> str:
    """
    Transcribe audio using Groq's Whisper endpoint (OpenAI-compatible).
    Returns plain text (empty string if not recognized).
    """
    if model is None:
        model = config.GROQ_WHISPER_MODEL

    url = f"{GROQ_BASE}/audio/transcriptions"
    mime = _mime_for_audio(audio_path)

    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    files = {"file": (audio_path.name, open(audio_path, "rb"), mime)}
    data = {"model": model}

    r = requests.post(url, headers=headers, files=files, data=data, timeout=120)
    if r.status_code >= 300:
        raise RuntimeError(f"Transcription failed ({r.status_code}): {r.text}")

    j = r.json()
    text = (j.get("text") or j.get("transcript") or "").strip()
    return text
