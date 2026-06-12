"""HTTP API: config, model discovery, job creation/status, downloads, thumbnails."""

from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app import __version__, db
from app.config import Settings, get_settings
from app.jobs import JobManager, new_job
from app.models import ConfigResponse, CreateJobResponse, Job, JobOptions

router = APIRouter(prefix="/api")

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_CHUNK = 1024 * 1024


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _manager(request: Request) -> JobManager:
    return request.app.state.manager


def _safe_filename(name: str) -> str:
    base = Path(name or "upload").name
    cleaned = _UNSAFE.sub("_", base).strip("._") or "upload"
    return cleaned[:120]


def _is_english(language: str) -> bool:
    t = language.strip().lower()
    return t in {"en", "eng"} or t.startswith("english")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/config", response_model=ConfigResponse)
def config(request: Request) -> ConfigResponse:
    s = _settings(request)
    enabled, english_only = s.translation_caps()
    model = s.whisper_model if s.transcribe_engine == "local" else s.transcribe_api_model
    return ConfigResponse(
        version=__version__,
        transcribe_engine=s.transcribe_engine,
        whisper_model=model,
        whisper_device=s.whisper_device,
        whisper_compute_type=s.whisper_compute_type,
        llm_enabled=s.llm_enabled,
        llm_model=s.llm_model if s.llm_enabled else None,
        translation_enabled=enabled,
        translation_english_only=english_only,
        max_upload_mb=s.max_upload_mb,
    )


@router.get("/llm/models")
def llm_models(request: Request) -> dict:
    """List models from the configured OpenAI-compatible endpoint (Ollama, etc.)."""
    s = _settings(request)
    if not s.llm_enabled:
        return {"models": [], "current": None}
    url = s.llm_base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {s.llm_api_key or 'sk-no-key'}"}
    try:
        resp = httpx.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        models = sorted({m.get("id") for m in data if m.get("id")})
    except (httpx.HTTPError, ValueError, KeyError):
        models = []
    # Ensure the configured default is always selectable.
    if s.llm_model and s.llm_model not in models:
        models.insert(0, s.llm_model)
    return {"models": models, "current": s.llm_model}


@router.post("/jobs", response_model=CreateJobResponse, status_code=201)
async def create_job(
    request: Request,
    file: UploadFile = File(...),
    source_language: str | None = Form(None),
    generate_chapters: bool = Form(False),
    chapter_count: int | None = Form(None),
    generate_summary: bool = Form(False),
    translate_to: str | None = Form(None),
    whisper_model: str | None = Form(None),
    whisper_compute_type: str | None = Form(None),
    llm_model: str | None = Form(None),
) -> CreateJobResponse:
    s = _settings(request)
    mgr = _manager(request)

    if (generate_chapters or generate_summary) and not s.llm_enabled:
        raise HTTPException(
            status_code=400, detail="Chapters and summary need an LLM. Set LLM_BASE_URL."
        )
    if translate_to:
        enabled, english_only = s.translation_caps()
        if not enabled:
            raise HTTPException(
                status_code=400, detail="Translation is disabled (TRANSLATE_ENGINE)."
            )
        if english_only and not _is_english(translate_to):
            raise HTTPException(
                status_code=400,
                detail="Only English translation is available. Set LIBRETRANSLATE_URL or an LLM "
                "for other languages.",
            )

    job_id = uuid.uuid4().hex
    filename = _safe_filename(file.filename or "upload")
    dest_dir = s.uploads_dir / job_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename

    max_bytes = s.max_upload_mb * 1024 * 1024  # 0 = unlimited
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(_CHUNK):
            size += len(chunk)
            if max_bytes and size > max_bytes:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413, detail=f"File exceeds the {s.max_upload_mb} MB limit."
                )
            out.write(chunk)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Empty upload.")

    options = JobOptions(
        source_language=(source_language or None),
        generate_chapters=generate_chapters,
        chapter_count=chapter_count,
        generate_summary=generate_summary,
        translate_to=(translate_to or None),
        whisper_model=(whisper_model or None),
        whisper_compute_type=(whisper_compute_type or None),
        llm_model=(llm_model or None),
    )
    job = new_job(job_id, filename, size, options)
    mgr.submit(job)
    return CreateJobResponse(id=job_id)


@router.get("/jobs", response_model=list[Job])
def list_jobs() -> list[Job]:
    return db.list_jobs(limit=50)


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = db.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(request: Request, job_id: str) -> None:
    s = _settings(request)
    if db.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    shutil.rmtree(s.uploads_dir / job_id, ignore_errors=True)
    shutil.rmtree(s.outputs_dir / job_id, ignore_errors=True)
    db.delete_job(job_id)


@router.get("/jobs/{job_id}/thumbnail")
def thumbnail(request: Request, job_id: str) -> FileResponse:
    s = _settings(request)
    path = s.outputs_dir / job_id / "thumb.jpg"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No thumbnail.")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/jobs/{job_id}/artifacts/{artifact_id}")
def download_artifact(request: Request, job_id: str, artifact_id: str) -> FileResponse:
    s = _settings(request)
    job = db.get_job(job_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="Job or result not found.")
    artifact = next((a for a in job.result.artifacts if a.id == artifact_id), None)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = s.outputs_dir / job_id / artifact.filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file missing.")
    return FileResponse(path, media_type=artifact.content_type, filename=artifact.filename)


__all__ = ["router", "get_settings"]
