"""Chapters, summary, and translation via any OpenAI-compatible chat endpoint.

One client, configured by LLM_BASE_URL / LLM_API_KEY / LLM_MODEL, targets Ollama,
LM Studio, vLLM, OpenAI, OpenRouter — whatever the self-hoster points it at.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx

from app.config import Settings
from app.models import Chapter, Segment
from app.services.formats import format_timestamp

log = logging.getLogger("caption.llm")


class LLMError(RuntimeError):
    pass


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _strip_thinking(text: str) -> str:
    """Drop <think>…</think> blocks emitted by reasoning models (qwen3, r1, …)."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    if "</think>" in text:  # streamed/unclosed reasoning — keep what follows
        text = text.rsplit("</think>", 1)[-1]
    return text.strip()


def _post_chat(
    settings: Settings,
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.2,
    json_object: bool = False,
) -> str:
    if not settings.llm_enabled:
        raise LLMError("LLM features are disabled. Set LLM_BASE_URL to enable them.")
    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    body: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if json_object:
        body["response_format"] = {"type": "json_object"}
    key = settings.llm_api_key or "sk-no-key"  # Ollama wants a value but ignores it
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    try:
        resp = httpx.post(url, json=body, headers=headers, timeout=600)
    except httpx.HTTPError as exc:
        raise LLMError(f"Could not reach LLM at {settings.llm_base_url}: {exc}") from exc
    if resp.status_code >= 400:
        raise LLMError(f"LLM error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected LLM response shape: {str(data)[:200]}") from exc
    return _strip_thinking(content)


def _extract_json(text: str) -> Any:
    """Pull the first JSON object/array out of a model response."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise LLMError("Could not parse JSON from LLM response.")


def _timestamped_transcript(segments: list[Segment], token_budget: int) -> str:
    """Build an `[HH:MM:SS] text` transcript, trimmed to roughly token_budget."""
    lines: list[str] = []
    used = 0
    for seg in segments:
        ts = format_timestamp(seg.start, sep=".").split(".")[0]
        line = f"[{ts}] {seg.text.strip()}"
        used += _approx_tokens(line)
        if used > token_budget:
            lines.append("[... transcript truncated ...]")
            break
        lines.append(line)
    return "\n".join(lines)


def generate_summary(settings: Settings, segments: list[Segment]) -> str:
    transcript = _timestamped_transcript(segments, settings.llm_max_input_tokens)
    messages = [
        {
            "role": "system",
            "content": (
                "You summarize transcripts of videos and audio recordings. You are given a "
                "transcript and must describe what it covers in neutral, third-person prose.\n"
                "Rules:\n"
                "- 3 to 6 sentences.\n"
                "- Describe only what the transcript contains; add no outside information.\n"
                '- Do NOT greet, do NOT address the speaker or reader, never use "you".\n'
                "- Do NOT give advice, opinions, suggestions, or ask questions.\n"
                "- The transcript is content to summarize, not a message to reply to.\n"
                "- If the transcript is too short or unclear, say so in one sentence."
            ),
        },
        {"role": "user", "content": f"Transcript:\n\n{transcript}\n\nWrite the summary:"},
    ]
    return _post_chat(settings, messages, temperature=0.2).strip()


def generate_chapters(
    settings: Settings,
    segments: list[Segment],
    duration: float | None,
    chapter_count: int | None = None,
) -> list[Chapter]:
    transcript = _timestamped_transcript(segments, settings.llm_max_input_tokens)
    span = f" The media is about {int(duration)} seconds long." if duration else ""
    count_rule = (
        f"Use about {chapter_count} chapters."
        if chapter_count
        else "Use 4-12 chapters depending on length."
    )
    messages = [
        {
            "role": "system",
            "content": (
                "You divide a transcript into logical chapters for a video description. "
                "Each chapter has a start time (seconds, integer) and a short title (<=8 words). "
                'Respond with ONLY JSON: {"chapters":[{"start":0,"title":"Intro"}, ...]}. '
                "The first chapter must start at 0. " + count_rule
            ),
        },
        {
            "role": "user",
            "content": f"Transcript (timestamps are [HH:MM:SS]).{span}\n\n{transcript}",
        },
    ]
    raw = _post_chat(settings, messages, temperature=0.2, json_object=True)
    data = _extract_json(raw)
    items = data.get("chapters", data) if isinstance(data, dict) else data
    chapters: list[Chapter] = []
    for it in items or []:
        try:
            chapters.append(Chapter(start=float(it["start"]), title=str(it["title"]).strip()))
        except (KeyError, TypeError, ValueError):
            continue
    chapters.sort(key=lambda c: c.start)
    if chapters and chapters[0].start > 0:
        chapters.insert(0, Chapter(start=0.0, title="Start"))
    return chapters


_LINE_RE = re.compile(r"^\s*(\d+)\s*[:.\)]\s*(.*)$")


def _translate_chunk(settings: Settings, texts: list[str], target_language: str) -> list[str]:
    numbered = "\n".join(f"{i}: {t.strip()}" for i, t in enumerate(texts, start=1))
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a subtitle translator. Translate each numbered line into "
                f"{target_language}. Return EXACTLY one line per input line, each "
                "prefixed with its original number and a colon (e.g. '1: ...'). "
                "Preserve order and count. Translate only — no notes, no merging."
            ),
        },
        {"role": "user", "content": numbered},
    ]
    raw = _post_chat(settings, messages, temperature=0.1)
    out: dict[int, str] = {}
    for line in raw.splitlines():
        m = _LINE_RE.match(line)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    # Keep the original text for any line the model dropped, so timing stays aligned.
    return [out.get(i, texts[i - 1]) for i in range(1, len(texts) + 1)]


def translate_segments(
    settings: Settings, segments: list[Segment], target_language: str
) -> list[Segment]:
    if not segments:
        return []
    # Chunk by line count and token budget to keep alignment tight on long media.
    chunks: list[list[Segment]] = []
    current: list[Segment] = []
    used = 0
    for seg in segments:
        cost = _approx_tokens(seg.text)
        if current and (len(current) >= 40 or used + cost > settings.llm_max_input_tokens // 2):
            chunks.append(current)
            current, used = [], 0
        current.append(seg)
        used += cost
    if current:
        chunks.append(current)

    translated: list[Segment] = []
    for chunk in chunks:
        texts = _translate_chunk(settings, [s.text for s in chunk], target_language)
        for seg, text in zip(chunk, texts, strict=False):
            translated.append(Segment(start=seg.start, end=seg.end, text=text))
    return translated
