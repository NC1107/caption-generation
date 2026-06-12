"""Unit tests for LLM-output parsing — no network; _post_chat is stubbed."""

from app.config import Settings
from app.models import Segment
from app.services import llm

LLM_SETTINGS = Settings(llm_base_url="http://fake:11434/v1", llm_model="test")


def test_extract_json_from_fenced_block():
    raw = 'Sure!\n```json\n{"chapters": [{"start": 0, "title": "Intro"}]}\n```'
    data = llm._extract_json(raw)
    assert data["chapters"][0]["title"] == "Intro"


def test_extract_json_bare_array():
    assert llm._extract_json("[1, 2, 3]") == [1, 2, 3]


def test_generate_chapters_parses_and_prepends_start(monkeypatch):
    monkeypatch.setattr(
        llm,
        "_post_chat",
        lambda *a, **k: '{"chapters":[{"start":30,"title":"Middle"}]}',
    )
    segs = [Segment(start=0, end=30, text="x"), Segment(start=30, end=60, text="y")]
    chapters = llm.generate_chapters(LLM_SETTINGS, segs, duration=60)
    # A chapter at 0 is inserted because the model's first chapter started at 30.
    assert chapters[0].start == 0.0
    assert chapters[-1].title == "Middle"


def test_translation_preserves_timing_and_count(monkeypatch):
    # Echo translator: returns the same numbered lines, "translated".
    def fake_post(_s, messages, **k):
        user = messages[-1]["content"]
        out = []
        for line in user.splitlines():
            num = line.split(":", 1)[0]
            out.append(f"{num}: TR-{line.split(':', 1)[1].strip()}")
        return "\n".join(out)

    monkeypatch.setattr(llm, "_post_chat", fake_post)
    segs = [
        Segment(start=0.0, end=1.0, text="one"),
        Segment(start=1.0, end=2.0, text="two"),
        Segment(start=2.0, end=3.0, text="three"),
    ]
    translated = llm.translate_segments(LLM_SETTINGS, segs, "Spanish")
    assert len(translated) == 3
    assert [t.start for t in translated] == [0.0, 1.0, 2.0]  # timing preserved
    assert translated[0].text == "TR-one"


def test_translation_falls_back_on_dropped_lines(monkeypatch):
    # Model drops line 2 — we must keep the original so timing stays aligned.
    monkeypatch.setattr(llm, "_post_chat", lambda *a, **k: "1: uno\n3: tres")
    segs = [
        Segment(start=0.0, end=1.0, text="one"),
        Segment(start=1.0, end=2.0, text="two"),
        Segment(start=2.0, end=3.0, text="three"),
    ]
    translated = llm.translate_segments(LLM_SETTINGS, segs, "Spanish")
    assert [t.text for t in translated] == ["uno", "two", "tres"]
