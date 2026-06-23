# === app.py ===
import json
import time
import uuid
import shutil
import pathlib
from typing import Optional

from flask import (
    Flask, request, jsonify, send_from_directory,
    render_template, abort
)

import config
from services import resemble_client, asr, answerer, audio_utils, emotion

# ---------------------------------
# Paths (no DB; file-based storage)
# ---------------------------------
ROOT      = pathlib.Path(__file__).resolve().parent
UPLOADS   = ROOT / "uploads"
OUTPUTS   = ROOT / "outputs"
VOICES    = ROOT / "voices"
TMP       = ROOT / "tmp"

for p in (UPLOADS, OUTPUTS, VOICES, TMP):
    p.mkdir(parents=True, exist_ok=True)

# -------------
# Flask App
# -------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024

# -------------
# Utilities
# -------------
def _now_ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S")

def _safe_filename(stem: str, ext: str) -> str:
    base = "".join(c for c in stem if c.isalnum() or c in ("-", "_"))
    return f"{base[:40]}_{_now_ts()}_{uuid.uuid4().hex[:6]}{ext}"

def _ext_ok(filename: str) -> bool:
    return pathlib.Path(filename).suffix.lower() in config.ALLOWED_AUDIO_EXTS

def _save_upload(field_name: str, dest_dir: pathlib.Path) -> pathlib.Path:
    if field_name not in request.files:
        abort(400, description=f"Missing file field '{field_name}'")
    f = request.files[field_name]
    if not f.filename:
        abort(400, description="Empty filename.")
    if not _ext_ok(f.filename):
        abort(400, description=f"Unsupported audio type. Allowed: {config.ALLOWED_AUDIO_EXTS}")
    ext = pathlib.Path(f.filename).suffix.lower()
    out_path = dest_dir / _safe_filename(pathlib.Path(f.filename).stem, ext)
    f.save(out_path)
    return out_path

def _current_voice_json_path() -> pathlib.Path:
    return VOICES / "current.json"

def get_current_voice_id() -> Optional[str]:
    # Priority: config constant, else file voices/current.json
    if getattr(config, "RESEMBLE_VOICE_ID", ""):
        return config.RESEMBLE_VOICE_ID
    p = _current_voice_json_path()
    if p.exists():
        try:
            data = json.loads(p.read_text("utf-8"))
            return data.get("voice_id")
        except Exception:
            return None
    return None

def set_current_voice_id(voice_id: str, sample_path: Optional[str] = None) -> None:
    data = {
        "voice_id": voice_id,
        "created_at": time.time(),
        "sample_path": sample_path
    }
    _current_voice_json_path().write_text(json.dumps(data, indent=2), encoding="utf-8")

def limit_outputs(max_files: int = None):
    """Keep the newest N files; delete older ones."""
    if max_files is None:
        max_files = config.OUTPUTS_LIMIT
    files = sorted(OUTPUTS.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[max_files:]:
        try:
            f.unlink()
        except Exception:
            pass

# -------------------
# Page Routes (UI)
# -------------------
@app.get("/")
def home():
    return render_template("index.html", voice_id=get_current_voice_id())

@app.route("/about")
def about():
    return render_template("about.html")

@app.get("/parrot")
def page_parrot():
    return render_template("parrot.html", voice_id=get_current_voice_id())

@app.get("/tts")
def page_tts():
    return render_template("tts.html", voice_id=get_current_voice_id())

@app.get("/qa")
def page_qa():
    return render_template("qa.html", voice_id=get_current_voice_id())

# -------------------
# API Routes
# -------------------
@app.post("/voice/set")
def api_voice_set():
    """
    Set active Resemble voice UUID without DB.
    Body: { "voice_id": "<uuid>" }
    """
    data = request.get_json(force=True, silent=True) or {}
    vid = (data.get("voice_id") or "").strip()
    if not vid:
        return jsonify({"ok": False, "error": "voice_id required"}), 400
    set_current_voice_id(vid)
    return jsonify({"ok": True, "voice_id": vid})

@app.post("/voice/enroll")
def api_voice_enroll():
    """
    Lightweight: accept a sample (for your own records) and remind the user to paste voice UUID.
    We are NOT creating voices via API to keep the flow simple and plan-agnostic.
    """
    try:
        audio_path = _save_upload("audio", UPLOADS)
        # Optional: normalize/trim the sample for consistency
        # norm_path = audio_utils.normalize_to_wav(audio_path, TMP)  # if you implement it
        return jsonify({
            "ok": True,
            "message": "Sample saved. This app does not auto-create voices via API. Copy a Resemble voice UUID and use /voice/set.",
            "sample": str(audio_path)
        })
    except Exception as e:
        app.logger.exception("enroll error")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/parrot/run")
def api_parrot_run():
    """
    Feature 1: echo same audio (keeps original emotion/tone).
    """
    try:
        audio_path = _save_upload("audio", UPLOADS)
        # If you want to normalize loudness for consistent playback, use audio_utils here.
        base = pathlib.Path(audio_path).stem or "parrot"
        ext = "." + config.OUTPUT_FORMAT.lstrip(".")
        out_name = _safe_filename(f"{base}_parrot", ext)
        out_path = OUTPUTS / out_name
        shutil.copy(audio_path, out_path)
        limit_outputs(config.OUTPUTS_LIMIT)
        return jsonify({"ok": True, "url": f"/outputs/{out_name}"})
    except Exception as e:
        app.logger.exception("parrot error")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/tts/run")
def api_tts_run():
    """
    Feature 2: Speak provided text in the cloned voice using Resemble low-latency synth.
    Body: { text, emotion?, speed?, pitch? }
    """
    try:
        data = request.get_json(force=True, silent=True) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"ok": False, "error": "text is required"}), 400

        vid = get_current_voice_id()
        if not vid:
            return jsonify({"ok": False, "error": "No voice configured. Use /voice/set to paste a Resemble voice UUID"}), 400

        # Map UI -> provider params (you can make this smarter inside services/emotion.py)
        emo  = (data.get("emotion") or "neutral").strip()
        spd  = data.get("speed")   # float or None
        pch  = data.get("pitch")   # float or None
        emo_payload = emotion.map_emotion(emo)  # returns dict like {"emotion": "..."} (may be empty)

        # Synthesize
        audio_bytes = resemble_client.low_latency_synthesize(
            voice_uuid=vid,
            text=text,
            output_format=config.OUTPUT_FORMAT,
            sample_rate=config.AUDIO_SAMPLE_RATE,
            speed=spd,
            pitch=pch,
            **emo_payload
        )

        out_url = audio_utils.save_audio_bytes_to_outputs(
            audio_bytes=audio_bytes,
            outputs_dir=OUTPUTS,
            base_name="tts",
            output_ext="." + config.OUTPUT_FORMAT.lstrip("."),
            limit=config.OUTPUTS_LIMIT
        )
        return jsonify({"ok": True, "url": out_url})
    except Exception as e:
        app.logger.exception("tts error")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.post("/qa/run")
def api_qa_run():
    """
    Feature 3: Voice question -> ASR (Groq Whisper) -> LLM answer (Groq) -> TTS in cloned voice.
    Form-Data: audio=<file>, emotion?=<str>
    """
    try:
        audio_path = _save_upload("audio", UPLOADS)

        # 1) ASR
        question = asr.transcribe_groq(audio_path, model=config.GROQ_WHISPER_MODEL).strip()
        if not question:
            question = "(unintelligible)"

        # 2) LLM answer (one sentence)
        answer = answerer.answer_short_groq(question, model=config.GROQ_LLM_MODEL).strip()

        # 3) TTS
        vid = get_current_voice_id()
        if not vid:
            return jsonify({
                "ok": False,
                "question": question,
                "answer": answer,
                "error": "No voice configured. Use /voice/set to paste a Resemble voice UUID"
            }), 400

        emo_q = (request.form.get("emotion") or "neutral").strip()
        emo_payload = emotion.map_emotion(emo_q)

        audio_bytes = resemble_client.low_latency_synthesize(
            voice_uuid=vid,
            text=answer,
            output_format=config.OUTPUT_FORMAT,
            sample_rate=config.AUDIO_SAMPLE_RATE,
            **emo_payload
        )

        out_url = audio_utils.save_audio_bytes_to_outputs(
            audio_bytes=audio_bytes,
            outputs_dir=OUTPUTS,
            base_name="qa",
            output_ext="." + config.OUTPUT_FORMAT.lstrip("."),
            limit=config.OUTPUTS_LIMIT
        )

        return jsonify({"ok": True, "question": question, "answer": answer, "url": out_url})
    except Exception as e:
        app.logger.exception("qa error")
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------
# Static / Files
# -------------------
@app.get("/outputs/<path:filename>")
def serve_outputs(filename: str):
    return send_from_directory(OUTPUTS, filename, as_attachment=False)

# Health
@app.get("/health")
def health():
    return jsonify({"ok": True})

# -------------
# Entrypoint
# -------------
if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
