# === config.py ===
import os
from dotenv import load_dotenv

load_dotenv()

# --- Required keys ---
RESEMBLE_API_KEY = os.getenv("RESEMBLE_API_KEY")
RESEMBLE_PROJECT_ID = os.getenv("RESEMBLE_PROJECT_ID")
RESEMBLE_VOICE_ID = os.getenv("RESEMBLE_VOICE_ID", "")

# --- Groq ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# --- App behavior ---
DEFAULT_LANG = "en"
MAX_UPLOAD_MB = 25
MAX_UPLOAD_SEC = 60
ALLOWED_AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
OUTPUT_FORMAT = "wav"
AUDIO_SAMPLE_RATE = 16000
OUTPUTS_LIMIT = 200

# --- Models ---
GROQ_WHISPER_MODEL = "whisper-large-v3"
GROQ_LLM_MODEL = "llama-3.1-8b-instant"

# --- Server ---
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True