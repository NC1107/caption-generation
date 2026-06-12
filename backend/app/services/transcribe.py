"""Transcription via faster-whisper (local) or any OpenAI-compatible Whisper API.

``task="translate"`` makes Whisper output English (its only translation target);
that powers the 'whisper' translation engine. Per-job model/precision overrides
arrive via the settings object (the pipeline copies settings with overrides).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.config import Settings
from app.models import Segment

log = logging.getLogger("caption.transcribe")

ProgressFn = Callable[[float], None]


@dataclass
class TranscriptionResult:
    language: str | None
    duration: float | None
    segments: list[Segment] = field(default_factory=list)


class TranscriptionError(RuntimeError):
    pass


_model_cache: dict[tuple[str, str, str], object] = {}


def _resolve_device_and_compute(settings: Settings) -> tuple[str, str]:
    device = settings.whisper_device
    compute = settings.whisper_compute_type
    if device == "auto":
        device = "cpu"
        try:
            import ctranslate2  # ships with faster-whisper

            if ctranslate2.get_cuda_device_count() > 0:
                device = "cuda"
        except Exception:  # noqa: BLE001
            device = "cpu"
    if compute == "auto":
        compute = "float16" if device == "cuda" else "int8"
    return device, compute


def _get_local_model(settings: Settings):
    device, compute = _resolve_device_and_compute(settings)
    key = (settings.whisper_model, device, compute)
    if key not in _model_cache:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - only when dep missing
            raise TranscriptionError(
                "faster-whisper is not installed. Use TRANSCRIBE_ENGINE=openai "
                "or install backend requirements."
            ) from exc
        log.info(
            "loading whisper model=%s device=%s compute=%s", settings.whisper_model, device, compute
        )
        _model_cache[key] = WhisperModel(
            settings.whisper_model,
            device=device,
            compute_type=compute,
            download_root=str(settings.models_dir),
        )
    return _model_cache[key]


def _transcribe_local(
    audio: Path,
    settings: Settings,
    source_language: str | None,
    task: str,
    progress: ProgressFn | None,
) -> TranscriptionResult:
    model = _get_local_model(settings)
    language = None if (not source_language or source_language == "auto") else source_language
    segments_iter, info = model.transcribe(
        str(audio),
        language=language,
        task=task,
        vad_filter=True,
        beam_size=5,
    )
    total = float(getattr(info, "duration", 0.0) or 0.0)
    out: list[Segment] = []
    for seg in segments_iter:
        out.append(Segment(start=float(seg.start), end=float(seg.end), text=seg.text))
        if progress and total > 0:
            progress(min(1.0, float(seg.end) / total))
    if progress:
        progress(1.0)
    return TranscriptionResult(
        language=getattr(info, "language", None),
        duration=total or (out[-1].end if out else None),
        segments=out,
    )


# Most hosted Whisper APIs reject files larger than ~25 MB.
_API_MAX_BYTES = 24 * 1024 * 1024


def _transcribe_api(
    audio: Path,
    settings: Settings,
    source_language: str | None,
    task: str,
    progress: ProgressFn | None,
) -> TranscriptionResult:
    if not settings.transcribe_api_key:
        raise TranscriptionError("TRANSCRIBE_API_KEY is required when TRANSCRIBE_ENGINE=openai.")
    size = audio.stat().st_size
    if size > _API_MAX_BYTES:
        raise TranscriptionError(
            f"Extracted audio is {size // (1024 * 1024)} MB — over the ~25 MB limit of hosted "
            "Whisper APIs. Use TRANSCRIBE_ENGINE=local for long media."
        )
    # The translations endpoint always outputs English and takes no language hint.
    endpoint = "/audio/translations" if task == "translate" else "/audio/transcriptions"
    url = settings.transcribe_api_base_url.rstrip("/") + endpoint
    data = {"model": settings.transcribe_api_model, "response_format": "verbose_json"}
    if task != "translate" and source_language and source_language != "auto":
        data["language"] = source_language

    if progress:
        progress(0.1)
    with audio.open("rb") as fh:
        files = {"file": (audio.name, fh, "audio/wav")}
        resp = httpx.post(
            url,
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {settings.transcribe_api_key}"},
            timeout=600,
        )
    if resp.status_code >= 400:
        raise TranscriptionError(f"Transcription API error {resp.status_code}: {resp.text[:300]}")
    payload = resp.json()
    segs = [
        Segment(start=float(s["start"]), end=float(s["end"]), text=s.get("text", ""))
        for s in payload.get("segments", [])
    ]
    if not segs and payload.get("text"):
        dur = float(payload.get("duration", 0.0) or 0.0)
        segs = [Segment(start=0.0, end=dur, text=payload["text"])]
    if progress:
        progress(1.0)
    return TranscriptionResult(
        language=payload.get("language"),
        duration=payload.get("duration"),
        segments=segs,
    )


def transcribe(
    audio: Path,
    settings: Settings,
    *,
    source_language: str | None = None,
    task: str = "transcribe",
    progress: ProgressFn | None = None,
) -> TranscriptionResult:
    if settings.transcribe_engine == "local":
        return _transcribe_local(audio, settings, source_language, task, progress)
    return _transcribe_api(audio, settings, source_language, task, progress)
