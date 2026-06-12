"""Render segments into subtitle/text formats. Pure functions, no I/O."""

from __future__ import annotations

from app.models import Chapter, Segment


def _clamp(seconds: float) -> float:
    return max(0.0, float(seconds))


def format_timestamp(seconds: float, *, sep: str = ",") -> str:
    """HH:MM:SS,mmm (SRT, sep=',') or HH:MM:SS.mmm (VTT, sep='.')."""
    seconds = _clamp(seconds)
    millis = int(round(seconds * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def to_srt(segments: list[Segment]) -> str:
    """SubRip (.srt)."""
    blocks: list[str] = []
    for i, seg in enumerate(segments, start=1):
        start = format_timestamp(seg.start, sep=",")
        end = format_timestamp(seg.end, sep=",")
        text = seg.text.strip()
        blocks.append(f"{i}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def to_vtt(segments: list[Segment]) -> str:
    """WebVTT (.vtt)."""
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_timestamp(seg.start, sep=".")
        end = format_timestamp(seg.end, sep=".")
        lines.append(f"{start} --> {end}")
        lines.append(seg.text.strip())
        lines.append("")
    return "\n".join(lines)


def to_plain_text(segments: list[Segment]) -> str:
    """Continuous transcript with no timestamps."""
    return " ".join(seg.text.strip() for seg in segments).strip() + "\n"


def chapters_to_markdown(chapters: list[Chapter]) -> str:
    """Render chapters as a Markdown list with HH:MM:SS anchors (YouTube-style)."""
    if not chapters:
        return ""
    lines = ["# Chapters", ""]
    for ch in chapters:
        ts = format_timestamp(ch.start, sep=".").split(".")[0]  # HH:MM:SS
        lines.append(f"- `{ts}` {ch.title.strip()}")
    return "\n".join(lines) + "\n"


def summary_to_markdown(summary: str) -> str:
    return f"# Summary\n\n{summary.strip()}\n"
