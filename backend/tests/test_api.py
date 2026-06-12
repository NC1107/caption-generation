"""End-to-end API + pipeline test with ffmpeg/Whisper stubbed out.

Exercises the real worker, SQLite job store, pipeline orchestration, artifact
writing, and download endpoints — only the heavy media/ML calls are faked.
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Segment
from app.services.transcribe import TranscriptionResult

FAKE_SEGMENTS = [
    Segment(start=0.0, end=2.0, text="Welcome to the show."),
    Segment(start=2.0, end=4.5, text="Today we talk about subtitles."),
    Segment(start=4.5, end=7.0, text="Thanks for watching."),
]


@pytest.fixture
def stub_pipeline(monkeypatch):
    def fake_probe(_src: Path):
        return 7.0

    def fake_extract(_src: Path, dst: Path) -> Path:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"\x00\x00")
        return dst

    def fake_transcribe(_audio, _settings, *, source_language=None, progress=None):
        if progress:
            progress(1.0)
        return TranscriptionResult(language="en", duration=7.0, segments=list(FAKE_SEGMENTS))

    monkeypatch.setattr("app.services.media.probe_duration", fake_probe)
    monkeypatch.setattr("app.services.media.extract_audio", fake_extract)
    monkeypatch.setattr("app.pipeline.transcribe", fake_transcribe)


def _wait_for_terminal(client: TestClient, job_id: str, timeout: float = 15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            return job
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} did not finish in time")


def test_health_and_config():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        cfg = client.get("/api/config").json()
        assert cfg["name"] == "Caption Generation"
        assert cfg["llm_enabled"] is False


def test_full_subtitle_job(stub_pipeline):
    with TestClient(app) as client:
        resp = client.post(
            "/api/jobs",
            files={"file": ("clip.mp4", b"not a real video", "video/mp4")},
        )
        assert resp.status_code == 201
        job_id = resp.json()["id"]

        job = _wait_for_terminal(client, job_id)
        assert job["status"] == "completed", job.get("error")
        assert job["result"]["detected_language"] == "en"

        ids = {a["id"] for a in job["result"]["artifacts"]}
        assert {"subtitles_srt", "subtitles_vtt", "transcript_txt"} <= ids

        srt = client.get(f"/api/jobs/{job_id}/artifacts/subtitles_srt")
        assert srt.status_code == 200
        assert "Welcome to the show." in srt.text
        assert "00:00:00,000 --> 00:00:02,000" in srt.text


def test_empty_transcript_warns_and_skips_extras(monkeypatch):
    def fake_extract(_src, dst):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"\x00")
        return dst

    def fake_empty(_audio, _settings, *, source_language=None, task="transcribe", progress=None):
        if progress:
            progress(1.0)
        return TranscriptionResult(language="en", duration=10.0, segments=[])

    monkeypatch.setattr("app.services.media.probe_duration", lambda _s: 10.0)
    monkeypatch.setattr("app.services.media.extract_audio", fake_extract)
    monkeypatch.setattr("app.pipeline.transcribe", fake_empty)
    with TestClient(app) as client:
        jid = client.post(
            "/api/jobs",
            files={"file": ("silent.mp4", b"data", "video/mp4")},
            data={"translate_to": "English"},
        ).json()["id"]
        job = _wait_for_terminal(client, jid)
        assert job["status"] == "completed"
        ids = {a["id"] for a in job["result"]["artifacts"]}
        assert "translation_srt" not in ids  # extras skipped on empty transcript
        assert any("No speech" in w for w in job["result"]["warnings"])


def test_llm_features_rejected_when_disabled():
    with TestClient(app) as client:
        resp = client.post(
            "/api/jobs",
            files={"file": ("clip.mp4", b"data", "video/mp4")},
            data={"generate_chapters": "true"},
        )
        assert resp.status_code == 400
        assert "LLM" in resp.json()["detail"]


def test_non_english_translation_rejected_without_engine():
    # Default config has no LLM/LibreTranslate, so only English translation is possible.
    with TestClient(app) as client:
        resp = client.post(
            "/api/jobs",
            files={"file": ("c.mp4", b"data", "video/mp4")},
            data={"translate_to": "Spanish"},
        )
        assert resp.status_code == 400
        assert "LIBRETRANSLATE_URL" in resp.json()["detail"]


def test_empty_upload_rejected():
    with TestClient(app) as client:
        resp = client.post("/api/jobs", files={"file": ("empty.mp4", b"", "video/mp4")})
        assert resp.status_code == 400


def test_delete_job(stub_pipeline):
    with TestClient(app) as client:
        job_id = client.post(
            "/api/jobs", files={"file": ("c.mp4", b"data", "video/mp4")}
        ).json()["id"]
        _wait_for_terminal(client, job_id)
        assert client.delete(f"/api/jobs/{job_id}").status_code == 204
        assert client.get(f"/api/jobs/{job_id}").status_code == 404
