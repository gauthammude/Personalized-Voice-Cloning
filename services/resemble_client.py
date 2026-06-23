# services/resemble_client.py
import base64
import json
import requests
from typing import Optional

import config

SYNTH_URL = "https://f.cluster.resemble.ai/synthesize"


def low_latency_synthesize(
    voice_uuid: str,
    text: str,
    output_format: str = "wav",
    sample_rate: int = 16000,
    speed: Optional[float] = None,
    pitch: Optional[float] = None,
    **extra  # e.g., {"emotion": "happy"} or other provider-specific fields
) -> bytes:
    """
    Calls Resemble low-latency synthesis and returns raw audio bytes.
    Response JSON contains 'audio_content' (base64).

    Args:
      voice_uuid: Resemble voice UUID
      text: text to speak
      output_format: "wav" or "mp3"
      sample_rate: 8000|16000|22050|32000|44100
      speed: optional float multiplier (provider may ignore)
      pitch: optional semitone shift (provider may ignore)
      extra: additional fields (e.g., emotion="happy")

    Returns:
      bytes of the synthesized audio file
    """
    payload = {
        "voice_uuid": voice_uuid,
        "data": text,
        "output_format": output_format,
        "sample_rate": sample_rate,
    }

    if speed is not None:
        payload["speed"] = float(speed)
    if pitch is not None:
        payload["pitch"] = float(pitch)

    # Merge any additional provider parameters (e.g., emotion)
    if extra:
        payload.update(extra)

    headers = {
        "Authorization": f"Bearer {config.RESEMBLE_API_KEY}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip",
    }

    r = requests.post(SYNTH_URL, headers=headers, data=json.dumps(payload), timeout=60)
    if r.status_code >= 300:
        raise RuntimeError(f"Synthesis failed ({r.status_code}): {r.text}")

    try:
        data = r.json()
    except Exception as e:
        raise RuntimeError(f"Non-JSON synth response: {r.text}") from e

    b64 = data.get("audio_content")
    if not b64:
        raise RuntimeError(f"Missing 'audio_content' in response: {data}")

    try:
        return base64.b64decode(b64)
    except Exception as e:
        raise RuntimeError("Failed to decode base64 audio_content") from e
