"""Unit tests for translation engine resolution (no network)."""

import pytest

from app.config import Settings
from app.services import translate


def test_is_english():
    assert translate._is_english("English")
    assert translate._is_english("en")
    assert not translate._is_english("Spanish")


def test_to_code():
    assert translate._to_code("Spanish") == "es"
    assert translate._to_code("Chinese (Simplified)") == "zh"
    assert translate._to_code("fr") == "fr"
    with pytest.raises(translate.TranslateError):
        translate._to_code("Klingon")


def test_auto_english_uses_whisper():
    # No LLM, no LibreTranslate → English still works via Whisper.
    assert translate.resolve_engine(Settings(), "English") == "whisper"


def test_auto_other_language_needs_an_engine():
    with pytest.raises(translate.TranslateError):
        translate.resolve_engine(Settings(), "Spanish")


def test_auto_prefers_libretranslate_then_llm():
    libre = Settings(libretranslate_url="http://lt:5000")
    assert translate.resolve_engine(libre, "Spanish") == "libretranslate"
    assert translate.resolve_engine(Settings(local_llm_url="http://x/v1"), "Spanish") == "llm"


def test_translation_caps():
    enabled, english_only = Settings().translation_caps()
    assert enabled and english_only
    enabled, english_only = Settings(libretranslate_url="http://lt:5000").translation_caps()
    assert enabled and not english_only
