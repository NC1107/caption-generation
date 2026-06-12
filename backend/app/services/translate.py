"""Subtitle translation with a pluggable engine.

Resolution for TRANSLATE_ENGINE=auto:
  1. LibreTranslate, if LIBRETRANSLATE_URL is set (proper offline NMT, any pair)
  2. Whisper's translate task, when the target is English (free, already local)
  3. the LLM, if one is configured
Explicit engines (whisper | libretranslate | llm | off) skip the resolution.
"""

from __future__ import annotations

import logging

import httpx

from app.config import Settings
from app.models import Segment
from app.services import llm
from app.services.transcribe import transcribe

log = logging.getLogger("caption.translate")

# Language name → ISO code for LibreTranslate (matches the UI's offered languages).
_LANG_CODES = {
    "english": "en", "spanish": "es", "french": "fr", "german": "de", "italian": "it",
    "portuguese": "pt", "dutch": "nl", "russian": "ru", "japanese": "ja", "korean": "ko",
    "chinese": "zh", "arabic": "ar", "hindi": "hi",
}


class TranslateError(RuntimeError):
    pass


def _is_english(target: str) -> bool:
    t = target.strip().lower()
    return t in {"en", "eng"} or t.startswith("english")


def _to_code(target: str) -> str:
    t = target.strip().lower().split("(")[0].strip()
    if t in _LANG_CODES:
        return _LANG_CODES[t]
    if len(t) == 2 and t.isalpha():  # already an ISO code
        return t
    raise TranslateError(f"Don't know the language code for “{target}”. Use an ISO code like 'es'.")


def resolve_engine(settings: Settings, target_language: str) -> str:
    eng = settings.translate_engine.lower()
    if eng == "off":
        raise TranslateError("Translation is disabled (TRANSLATE_ENGINE=off).")
    if eng == "whisper":
        if not _is_english(target_language):
            raise TranslateError(
                "Whisper only translates to English. Pick English or change TRANSLATE_ENGINE."
            )
        return "whisper"
    if eng == "libretranslate":
        if not settings.has_libretranslate:
            raise TranslateError("LIBRETRANSLATE_URL is not set.")
        return "libretranslate"
    if eng == "llm":
        if not settings.llm_enabled:
            raise TranslateError("No LLM configured (set LLM_BASE_URL).")
        return "llm"
    # auto
    if settings.has_libretranslate:
        return "libretranslate"
    if _is_english(target_language):
        return "whisper"
    if settings.llm_enabled:
        return "llm"
    raise TranslateError(
        "Only English translation is available right now. Run LibreTranslate "
        "(set LIBRETRANSLATE_URL) or configure an LLM to translate to other languages."
    )


def translate_segments(
    settings: Settings,
    segments: list[Segment],
    target_language: str,
    *,
    audio,
    source_language: str | None = None,
) -> list[Segment]:
    if not segments:
        return []
    engine = resolve_engine(settings, target_language)
    log.info("translating %d segments to %s via %s", len(segments), target_language, engine)
    if engine == "whisper":
        res = transcribe(audio, settings, source_language=source_language, task="translate")
        return res.segments
    if engine == "libretranslate":
        return _libretranslate(settings, segments, target_language)
    return llm.translate_segments(settings, segments, target_language)


def _libretranslate(
    settings: Settings, segments: list[Segment], target_language: str
) -> list[Segment]:
    code = _to_code(target_language)
    url = settings.libretranslate_url.rstrip("/") + "/translate"
    body: dict = {
        "q": [s.text.strip() for s in segments],
        "source": "auto",
        "target": code,
        "format": "text",
    }
    if settings.libretranslate_api_key:
        body["api_key"] = settings.libretranslate_api_key
    try:
        resp = httpx.post(url, json=body, timeout=600)
    except httpx.HTTPError as exc:
        raise TranslateError(
            f"Could not reach LibreTranslate at {settings.libretranslate_url}: {exc}"
        ) from exc
    if resp.status_code >= 400:
        raise TranslateError(f"LibreTranslate error {resp.status_code}: {resp.text[:200]}")
    out = resp.json().get("translatedText", [])
    if isinstance(out, str):  # some versions return a string for a single item
        out = [out]
    return [
        Segment(start=seg.start, end=seg.end, text=(out[i] if i < len(out) else seg.text))
        for i, seg in enumerate(segments)
    ]
