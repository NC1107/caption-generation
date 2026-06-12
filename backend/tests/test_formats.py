from app.models import Chapter, Segment
from app.services import formats

SEGS = [
    Segment(start=0.0, end=2.5, text="Hello world"),
    Segment(start=2.5, end=5.0, text="  second line  "),
    Segment(start=3661.0, end=3663.0, text="past an hour"),
]


def test_timestamp_srt_and_vtt():
    assert formats.format_timestamp(0) == "00:00:00,000"
    assert formats.format_timestamp(1.5) == "00:00:01,500"
    assert formats.format_timestamp(3661.25, sep=".") == "01:01:01.250"
    # negative clamps to zero
    assert formats.format_timestamp(-3) == "00:00:00,000"


def test_srt_structure():
    srt = formats.to_srt(SEGS)
    blocks = srt.strip().split("\n\n")
    assert len(blocks) == 3
    assert blocks[0].startswith("1\n00:00:00,000 --> 00:00:02,500\nHello world")
    # text is stripped
    assert "second line" in blocks[1] and "  second line  " not in blocks[1]


def test_vtt_has_header_and_dot_separator():
    vtt = formats.to_vtt(SEGS)
    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.500" in vtt


def test_plain_text_joins_without_timestamps():
    txt = formats.to_plain_text(SEGS)
    assert "00:00" not in txt
    assert txt.startswith("Hello world second line")


def test_empty_inputs():
    assert formats.to_srt([]) == ""
    assert formats.to_vtt([]).startswith("WEBVTT")
    assert formats.chapters_to_markdown([]) == ""


def test_chapters_markdown():
    md = formats.chapters_to_markdown(
        [Chapter(start=0.0, title="Intro"), Chapter(start=125.0, title="Main")]
    )
    assert "# Chapters" in md
    assert "`00:00:00` Intro" in md
    assert "`00:02:05` Main" in md
