# services/emotion.py
from typing import Dict

# Simple mapper. You can expand this to set speed/pitch defaults per emotion if you like.
_EMOTION_MAP = {
    "neutral": {"emotion": "neutral"},
    "happy": {"emotion": "happy"},
    "sad": {"emotion": "sad"},
    "excited": {"emotion": "excited"},
    "angry": {"emotion": "angry"},
}


def map_emotion(ui_value: str) -> Dict:
    """
    Map UI 'emotion' string to provider parameters.
    If the provider ignores 'emotion', this dict will be harmless.
    """
    key = (ui_value or "neutral").strip().lower()
    return _EMOTION_MAP.get(key, {"emotion": "neutral"})
