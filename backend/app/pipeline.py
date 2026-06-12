"""The job pipeline: extract audio → transcribe → optionally enhance.

Runs in a worker thread; progress and results are persisted to SQLite so the
API can poll them. Per-job model/precision/LLM-model overrides are applied by
copying the settings object once, up front.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from app import db
from app.config import Settings
from app.models import Artifact, Job, JobResult, JobStatus
from app.services import formats, llm, media, translate
from app.services.transcribe import transcribe

log = logging.getLogger("caption.pipeline")

PREVIEW_CUES = 50


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _update(
    job_id: str,
    *,
    status: JobStatus | None = None,
    progress: float | None = None,
    message: str | None = None,
    result: JobResult | None = None,
    error: str | None = None,
    thumbnail: bool | None = None,
) -> Job | None:
    job = db.get_job(job_id)
    if job is None:
        return None
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = max(0.0, min(1.0, progress))
    if message is not None:
        job.stage_message = message
    if result is not None:
        job.result = result
    if error is not None:
        job.error = error
    if thumbnail is not None:
        job.thumbnail = thumbnail
    job.updated_at = _now()
    db.save_job(job)
    return job


def _write_artifact(
    job_dir: Path,
    *,
    id: str,
    kind: str,
    label: str,
    filename: str,
    content: str,
    content_type: str,
) -> Artifact:
    path = job_dir / filename
    path.write_text(content, encoding="utf-8")
    return Artifact(
        id=id,
        kind=kind,
        label=label,
        filename=filename,
        content_type=content_type,
        size=path.stat().st_size,
    )


def _effective(settings: Settings, job: Job) -> Settings:
    """Apply per-job overrides (model size, precision, LLM model) to settings."""
    o = job.options
    updates = {}
    if o.whisper_model:
        updates["whisper_model"] = o.whisper_model
    if o.whisper_compute_type:
        updates["whisper_compute_type"] = o.whisper_compute_type
    if o.llm_model:
        updates["llm_model"] = o.llm_model
    return settings.model_copy(update=updates) if updates else settings


def run_pipeline(job_id: str, settings: Settings) -> None:
    job = db.get_job(job_id)
    if job is None:
        log.warning("pipeline: job %s vanished", job_id)
        return
    try:
        _run(job, settings)
    except Exception as exc:  # noqa: BLE001 — surface any failure to the user cleanly
        log.exception("pipeline failed for job %s", job_id)
        _update(job_id, status=JobStatus.failed, error=str(exc))


def _run(job: Job, base_settings: Settings) -> None:
    job_id = job.id
    opts = job.options
    settings = _effective(base_settings, job)
    src = settings.uploads_dir / job_id / job.filename
    out_dir = settings.outputs_dir / job_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError("Uploaded file is missing — it may have been purged.")

    # extract audio + a thumbnail  (progress 0 → 0.10)
    _update(job_id, status=JobStatus.extracting, progress=0.02, message="Extracting audio…")
    duration = media.probe_duration(src)
    if media.extract_thumbnail(src, out_dir / "thumb.jpg", at_seconds=(duration or 10) * 0.1):
        _update(job_id, thumbnail=True)
    audio = media.extract_audio(src, settings.uploads_dir / job_id / "audio.wav")
    _update(job_id, progress=0.10, message="Audio ready")

    # transcribe  (progress 0.10 → 0.65)
    _update(job_id, status=JobStatus.transcribing, progress=0.12, message="Transcribing…")

    def on_transcribe_progress(frac: float) -> None:
        _update(job_id, progress=0.12 + 0.53 * frac, message=f"Transcribing… {int(frac * 100)}%")

    tr = transcribe(
        audio, settings, source_language=opts.source_language, progress=on_transcribe_progress
    )
    duration = tr.duration or duration
    segments = tr.segments

    result = JobResult(
        detected_language=tr.language,
        duration=duration,
        cue_count=len(segments),
        preview_segments=segments[:PREVIEW_CUES],
    )
    if not segments:
        result.warnings.append(
            "No speech was detected — the audio track may be silent or contain no speech, "
            "so the subtitles and transcript are empty."
        )

    # subtitles + transcript
    _update(job_id, progress=0.66, message="Writing subtitles…")
    result.artifacts += [
        _write_artifact(out_dir, id="subtitles_srt", kind="subtitles", label="Subtitles (.srt)",
                        filename="subtitles.srt", content=formats.to_srt(segments),
                        content_type="application/x-subrip"),
        _write_artifact(out_dir, id="subtitles_vtt", kind="subtitles", label="Subtitles (.vtt)",
                        filename="subtitles.vtt", content=formats.to_vtt(segments),
                        content_type="text/vtt"),
        _write_artifact(out_dir, id="transcript_txt", kind="transcript", label="Transcript (.txt)",
                        filename="transcript.txt", content=formats.to_plain_text(segments),
                        content_type="text/plain"),
    ]

    # optional extras (progress 0.66 → 0.98). A failed extra is recorded as a
    # warning so the subtitles are still delivered.
    if segments and (opts.translate_to or opts.generate_chapters or opts.generate_summary):
        _update(job_id, status=JobStatus.enhancing, progress=0.70, message="Generating extras…")

    if segments and opts.translate_to:
        _update(job_id, message=f"Translating to {opts.translate_to}…")
        try:
            translated = translate.translate_segments(
                settings, segments, opts.translate_to,
                audio=audio, source_language=opts.source_language,
            )
            tag = _lang_tag(opts.translate_to)
            result.artifacts += [
                _write_artifact(out_dir, id="translation_srt", kind="translation",
                                label=f"Translation · {opts.translate_to} (.srt)",
                                filename=f"subtitles.{tag}.srt", content=formats.to_srt(translated),
                                content_type="application/x-subrip"),
                _write_artifact(out_dir, id="translation_vtt", kind="translation",
                                label=f"Translation · {opts.translate_to} (.vtt)",
                                filename=f"subtitles.{tag}.vtt", content=formats.to_vtt(translated),
                                content_type="text/vtt"),
            ]
        except Exception as exc:  # noqa: BLE001
            log.warning("translation failed for job %s: %s", job_id, exc)
            result.warnings.append(f"Translation failed: {exc}")
        _update(job_id, progress=0.85)

    if segments and (opts.generate_chapters or opts.generate_summary):
        if not settings.llm_enabled:
            result.warnings.append("Chapters and summary need an LLM (LLM_BASE_URL); skipped.")
        else:
            if opts.generate_chapters:
                _update(job_id, message="Generating chapters…")
                try:
                    chapters = llm.generate_chapters(
                        settings, segments, duration, opts.chapter_count
                    )
                    result.chapters = chapters
                    if chapters:
                        result.artifacts.append(
                            _write_artifact(out_dir, id="chapters_md", kind="chapters",
                                            label="Chapters (.md)", filename="chapters.md",
                                            content=formats.chapters_to_markdown(chapters),
                                            content_type="text/markdown")
                        )
                except Exception as exc:  # noqa: BLE001
                    log.warning("chapters failed for job %s: %s", job_id, exc)
                    result.warnings.append(f"Chapters failed: {exc}")
                _update(job_id, progress=0.92)

            if opts.generate_summary:
                _update(job_id, message="Writing summary…")
                try:
                    summary = llm.generate_summary(settings, segments)
                    result.summary = summary
                    result.artifacts.append(
                        _write_artifact(out_dir, id="summary_md", kind="summary",
                                        label="Summary (.md)", filename="summary.md",
                                        content=formats.summary_to_markdown(summary),
                                        content_type="text/markdown")
                    )
                except Exception as exc:  # noqa: BLE001
                    log.warning("summary failed for job %s: %s", job_id, exc)
                    result.warnings.append(f"Summary failed: {exc}")

    _update(job_id, status=JobStatus.completed, progress=1.0, message="Completed", result=result)
    log.info("job %s completed (%d artifacts)", job_id, len(result.artifacts))


def _lang_tag(language: str) -> str:
    """A filesystem-safe short tag for a target language label."""
    tag = "".join(c for c in language.lower() if c.isalnum())[:12]
    return tag or "translated"
