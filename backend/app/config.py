"""Env-driven settings. Defaults give a fully-local install with no LLM."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TranscribeEngine = Literal["local", "openai"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # server
    caption_host: str = "0.0.0.0"
    caption_port: int = 8000
    caption_cors_origins: str = ""
    caption_static_dir: str = ""  # built frontend; auto-detected when empty
    log_level: str = "info"

    # storage & limits
    data_dir: Path = Path("/data")
    max_upload_mb: int = 51200  # ~50 GB; set 0 for unlimited
    worker_concurrency: int = 1
    job_retention_hours: int = 72

    # transcription
    transcribe_engine: TranscribeEngine = "local"
    whisper_model: str = "base"
    whisper_device: str = "auto"  # auto | cpu | cuda
    whisper_compute_type: str = "auto"  # auto | int8 | int8_float16 | float16 | float32

    transcribe_api_base_url: str = "https://api.openai.com/v1"
    transcribe_api_key: str = ""
    transcribe_api_model: str = "whisper-1"

    # llm providers (optional) — a local OpenAI-compatible server and/or OpenRouter (cloud)
    local_llm_url: str = ""  # e.g. http://localhost:11434/v1 (Ollama, LM Studio, vLLM)
    openrouter_api_key: str = ""
    llm_model: str = ""  # default model spec: "local::id", "cloud::id", or a plain id
    llm_max_input_tokens: int = 12000

    # translation: auto | whisper | libretranslate | llm | off
    translate_engine: str = "auto"
    libretranslate_url: str = ""
    libretranslate_api_key: str = ""

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "caption.sqlite"

    @property
    def has_local_llm(self) -> bool:
        return bool(self.local_llm_url.strip())

    @property
    def has_cloud_llm(self) -> bool:
        return bool(self.openrouter_api_key.strip())

    @property
    def llm_enabled(self) -> bool:
        return self.has_local_llm or self.has_cloud_llm

    @property
    def default_llm_spec(self) -> str:
        """Env-configured default model, provider-prefixed. May be empty."""
        if not self.llm_model:
            return ""
        if "::" in self.llm_model:
            return self.llm_model
        return ("local::" if self.has_local_llm else "cloud::") + self.llm_model

    def resolve_llm(self, spec: str) -> tuple[str, str, str]:
        """Map a model spec ('local::id' | 'cloud::id' | 'id') to (base_url, api_key, model)."""
        provider, sep, mid = spec.partition("::")
        if not sep:
            mid = spec
            provider = "local" if self.has_local_llm else "cloud"
        if provider == "cloud":
            return ("https://openrouter.ai/api/v1", self.openrouter_api_key or "sk-no-key", mid)
        return (self.local_llm_url.rstrip("/"), "ollama", mid)

    @property
    def has_libretranslate(self) -> bool:
        return bool(self.libretranslate_url.strip())

    def translation_caps(self) -> tuple[bool, bool]:
        """Return (enabled, english_only) for the current TRANSLATE_ENGINE + config.

        Whisper's translate task is always available (it only outputs English), so
        translation is generally possible; other targets need LibreTranslate or an LLM.
        """
        eng = self.translate_engine.lower()
        libre, llm = self.has_libretranslate, self.llm_enabled
        if eng == "off":
            return (False, False)
        if eng == "whisper":
            return (True, True)
        if eng == "libretranslate":
            return (libre, False)
        if eng == "llm":
            return (llm, False)
        # auto: whisper covers English; libretranslate/llm unlock other languages
        return (True, not (libre or llm))

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.caption_cors_origins.split(",") if o.strip()]

    @property
    def static_path(self) -> Path | None:
        """The built frontend dir, or None when running API-only (dev)."""
        candidates: list[Path] = []
        if self.caption_static_dir:
            candidates.append(Path(self.caption_static_dir))
        candidates.append(Path("/app/static"))
        candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
        for c in candidates:
            if (c / "index.html").is_file():
                return c
        return None

    @field_validator("whisper_device")
    @classmethod
    def _valid_device(cls, v: str) -> str:
        v = v.lower()
        if v not in {"auto", "cpu", "cuda"}:
            raise ValueError("WHISPER_DEVICE must be one of: auto, cpu, cuda")
        return v

    def ensure_dirs(self) -> None:
        for p in (self.uploads_dir, self.outputs_dir, self.models_dir):
            p.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
