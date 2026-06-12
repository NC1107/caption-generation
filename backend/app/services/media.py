"""ffmpeg helpers: probe duration and extract 16 kHz mono WAV (what Whisper wants)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class MediaError(RuntimeError):
    """Raised when ffmpeg/ffprobe is missing or fails on the input."""


def _require(binary: str) -> str:
    path = shutil.which(binary)
    if not path:
        raise MediaError(
            f"`{binary}` not found on PATH. Install ffmpeg (the Docker image bundles it)."
        )
    return path


def probe_duration(src: Path) -> float | None:
    """Return media duration in seconds, or None if it cannot be determined."""
    ffprobe = _require("ffprobe")
    try:
        out = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(src),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        data = json.loads(out.stdout or "{}")
        dur = data.get("format", {}).get("duration")
        return float(dur) if dur is not None else None
    except (subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return None


def extract_audio(src: Path, dst: Path) -> Path:
    """Extract/transcode the audio track of ``src`` to 16 kHz mono WAV at ``dst``."""
    ffmpeg = _require("ffmpeg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i", str(src),
            "-vn",            # drop video
            "-ac", "1",       # mono
            "-ar", "16000",   # 16 kHz
            "-c:a", "pcm_s16le",
            str(dst),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-5:]
        raise MediaError("ffmpeg failed to extract audio:\n" + "\n".join(tail))
    if not dst.exists() or dst.stat().st_size == 0:
        raise MediaError("ffmpeg produced no audio — the file may contain no audio track.")
    return dst


def has_video_stream(src: Path) -> bool:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return False
    try:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(src)],
            capture_output=True, text=True, timeout=60,
        )
        return "video" in out.stdout
    except subprocess.SubprocessError:
        return False


def extract_thumbnail(src: Path, dst: Path, at_seconds: float = 0.0) -> bool:
    """Grab a single downscaled JPEG frame. Returns False if it can't (e.g. audio-only)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not has_video_stream(src):
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [ffmpeg, "-y", "-ss", f"{max(0.0, at_seconds):.2f}", "-i", str(src),
         "-frames:v", "1", "-vf", "scale=320:-2", str(dst)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
        # Seeking past the end can fail; retry from the start.
        proc = subprocess.run(
            [ffmpeg, "-y", "-i", str(src), "-frames:v", "1", "-vf", "scale=320:-2", str(dst)],
            capture_output=True, text=True,
        )
    return dst.exists() and dst.stat().st_size > 0
