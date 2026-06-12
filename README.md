# Caption Generation

Drop in a video or audio file, get back subtitles (`.srt` / `.vtt`), a transcript,
and optionally chapters, a summary, and translations. Runs on your own machine —
no API keys required.

A modern, self-hostable take on the (abandoned) [subvert](https://github.com/aschmelyun/subvert):
local transcription with [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
and AI extras through any local or cloud LLM.

<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/2ccdc641-fa33-4630-a48f-4f38cb622951" />

## Quick start

```bash
cp .env.example .env        # optional — defaults work as-is
docker compose up -d        # pulls the prebuilt image → http://localhost:8000
```

(Builds locally instead with `docker compose up -d --build`.)

Drop in a file, hit **Generate subtitles**. First run downloads the Whisper model
(~140 MB) to `./data`; everything (uploads, output, models, DB) lives there.

Subtitles and English translation are fully local and need no key.

## Chapters, summaries & other-language translation

These use an LLM — set one of:

```ini
OPENROUTER_API_KEY=sk-or-...          # cloud, easiest
LOCAL_LLM_URL=http://ollama:11434/v1  # local (Ollama/LM Studio/vLLM)
```

Then pick a model in the UI (`(local)` / `(cloud)`). No Ollama yet? Bundle one with
`docker compose --profile ollama up -d`.

## Settings

All optional — see `.env.example` for the full list. The common ones:

| Variable | Default | |
|---|---|---|
| `CAPTION_PORT` | `8000` | Port to serve on |
| `MAX_UPLOAD_MB` | `51200` | Upload cap (~50 GB); `0` = no limit |
| `WHISPER_MODEL` | `base` | `tiny`·`base`·`small`·`medium`·`large-v3` |
| `OPENROUTER_API_KEY` / `LOCAL_LLM_URL` | — | Enable cloud / local LLM |

**GPU:** `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`

## Develop

```bash
make install   # deps    make backend / make frontend   # dev servers
make test      # pytest  make lint                       # ruff
```

[MIT](LICENSE).
