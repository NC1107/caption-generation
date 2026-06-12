"""Pydantic models shared across the API, worker, and services."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    queued = "queued"
    extracting = "extracting"
    transcribing = "transcribing"
    enhancing = "enhancing"
    completed = "completed"
    failed = "failed"


TERMINAL_STATUSES = {JobStatus.completed, JobStatus.failed}


class Segment(BaseModel):
    """A single timed line of transcription."""

    start: float
    end: float
    text: str


class JobOptions(BaseModel):
    """User-selected work for a job. Subtitles are always produced."""

    source_language: str | None = None
    generate_chapters: bool = False
    chapter_count: int | None = None  # target number of chapters; None => auto
    generate_summary: bool = False
    translate_to: str | None = None
    # Per-job overrides (fall back to server config when unset).
    whisper_model: str | None = None
    whisper_compute_type: str | None = None
    llm_model: str | None = None


class Chapter(BaseModel):
    start: float  # seconds
    title: str


class Artifact(BaseModel):
    """A downloadable output file produced by a job."""

    id: str
    kind: str  # "subtitles" | "transcript" | "translation" | "chapters" | "summary"
    label: str
    filename: str
    content_type: str
    size: int = 0


class JobResult(BaseModel):
    detected_language: str | None = None
    duration: float | None = None
    cue_count: int = 0
    artifacts: list[Artifact] = Field(default_factory=list)
    chapters: list[Chapter] = Field(default_factory=list)
    summary: str | None = None
    preview_segments: list[Segment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Job(BaseModel):
    id: str
    status: JobStatus = JobStatus.queued
    progress: float = 0.0
    stage_message: str = "Queued"
    filename: str
    size: int = 0
    thumbnail: bool = False
    created_at: str
    updated_at: str
    options: JobOptions = Field(default_factory=JobOptions)
    result: JobResult | None = None
    error: str | None = None


class CreateJobResponse(BaseModel):
    id: str


class ConfigResponse(BaseModel):
    """Capabilities the frontend uses to enable/disable features."""

    name: str = "Caption Generation"
    version: str
    transcribe_engine: str
    whisper_model: str
    whisper_device: str
    whisper_compute_type: str
    llm_enabled: bool
    llm_model: str | None = None
    translation_enabled: bool = True
    translation_english_only: bool = False
    max_upload_mb: int
