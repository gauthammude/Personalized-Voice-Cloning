# services/audio_utils.py
import time
import uuid
from pathlib import Path
from typing import Optional


def _now_ts() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def _safe_filename(stem: str, ext_with_dot: str) -> str:
    ext = ext_with_dot if ext_with_dot.startswith(".") else "." + ext_with_dot
    base = "".join(c for c in stem if c.isalnum() or c in ("-", "_"))
    return f"{base[:40]}_{_now_ts()}_{uuid.uuid4().hex[:6]}{ext}"


def save_audio_bytes_to_outputs(
    audio_bytes: bytes,
    outputs_dir: Path,
    base_name: str = "out",
    output_ext: str = ".wav",
    limit: int = 200,
) -> str:
    """
    Save audio bytes as a file inside outputs_dir and prune old files to 'limit'.
    Returns a URL path like '/outputs/<file>'.
    """
    outputs_dir.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(base_name, output_ext)
    out_path = outputs_dir / filename
    with open(out_path, "wb") as f:
        f.write(audio_bytes)

    # prune older files
    files = sorted(outputs_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[limit:]:
        try:
            f.unlink()
        except Exception:
            pass

    return f"/outputs/{filename}"


# Optional utilities (stubs) if you decide to normalize/convert later.
# They are intentionally no-op to avoid extra dependencies.
def normalize_to_wav(in_path: Path, tmp_dir: Path) -> Path:
    """
    Placeholder for future loudness/sr normalization if you add deps (pydub, librosa, etc.).
    Currently returns input path untouched.
    """
    return in_path
