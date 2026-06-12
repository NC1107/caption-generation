# Caption Generation

Subtitles for your own videos. Drop in a video or audio file and get
clean `.srt` / `.vtt` subtitles and a transcript back — plus optional chapters, a
summary, and translated subtitles. It can run entirely on your own machine with no
API keys and nothing leaving your box.

## Why this exists

I'd been running a little local script to subtitle my own videos with Whisper —
nothing fancy, just something that saved me from paying for captions. Around the
same time I went looking for [subvert](https://github.com/aschmelyun/subvert),
which did basically this in a tidy web app, and found it abandoned and
locked to the OpenAI API. So I cleaned up my setup, wrapped it in Docker, and
turned it into something other people can actually run. That's Caption Generation.

It keeps the good parts of subvert (drop a file in, get subtitles out, one
container) and fixes the dealbreaker: **it doesn't need OpenAI, or any cloud at
all.** Transcription runs locally with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper). The optional AI
extras talk to whatever LLM you point them at — your local
[Ollama](https://ollama.com), LM Studio, vLLM, or a hosted API if you'd rather.

## What you get

- Subtitles from any media ffmpeg can read (MP4, MKV, MOV, MP3, WAV, M4A, …)
- `.srt`, `.vtt`, and a plain-text transcript to download
- Translated subtitles, with the timestamps kept intact
- Auto chapters (YouTube-description style) and a short summary
- A real job queue with live progress that survives a restart
- One Docker container, a couple of env vars, done

Subtitles and English translation need no API key — Whisper does both locally.
Chapters, summaries, and translating to other languages use an LLM (or a dedicated
translator), which can be fully local too.

## Quick start

You need Docker. That's it.

```bash
git clone <your-fork-url> caption-generation && cd caption-generation
cp .env.example .env        # optional, the defaults already work
docker compose up -d
```

Open <http://localhost:8000>, drop in a file, hit **Generate subtitles**.

The first run downloads the Whisper model (the default `base` model is ~140 MB)
into the `./data` folder. After that it's instant. Everything — uploads, output,
the model cache, the job database — lives in `./data`.

## Turning on chapters / summary / translation

These need an LLM. Easiest fully-local option is the bundled Ollama service:

```bash
# in .env:
#   LLM_BASE_URL=http://ollama:11434/v1
#   LLM_MODEL=llama3.1:8b
docker compose --profile ollama up -d
docker compose exec ollama ollama pull llama3.1:8b
```

The toggles light up in the UI on their own once an LLM is reachable.

**Already running Ollama on the host?** A bridged container can't reach an Ollama
bound to `127.0.0.1`, so run the app on the host network. Drop in a
`docker-compose.override.yml`:

```yaml
services:
  app:
    network_mode: host
```

…then point straight at it in `.env` and `docker compose up -d`:

```ini
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL=qwen3:8b
```

Prefer a hosted model? Point it anywhere OpenAI-compatible — your key goes in
`LLM_API_KEY`:

```ini
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# OpenRouter
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=sk-or-...
LLM_MODEL=meta-llama/llama-3.1-8b-instruct
```

## Translation

English translation runs locally through Whisper — no LLM, no API key. For other
languages, either point an LLM at it or run the bundled offline translator:

```bash
docker compose --profile translate up -d
# then in .env:
#   LIBRETRANSLATE_URL=http://libretranslate:5000   (or http://localhost:5000 on host network)
```

`TRANSLATE_ENGINE` (`auto` by default) can force `whisper`, `libretranslate`, or `llm`.

## GPU (NVIDIA)

CPU works fine for most things. If you've got an NVIDIA GPU and the
[Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
installed:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

That rebuilds the image with CUDA support and switches Whisper to the GPU. Bump
`WHISPER_MODEL` to `large-v3` while you're at it.

## Settings

Everything has a default. Copy `.env.example` to `.env` and change only what you need.

| Variable | Default | What it does |
|---|---|---|
| `CAPTION_PORT` | `8000` | Port the UI/API listens on |
| `DATA_DIR` | `/data` | Uploads, output, job DB, and the Whisper model cache |
| `MAX_UPLOAD_MB` | `51200` | Upload size cap in MB (~50 GB). Set `0` for no limit, or lower for a public instance |
| `WORKER_CONCURRENCY` | `1` | How many files transcribe at once |
| `JOB_RETENTION_HOURS` | `72` | Delete jobs + files after N hours (`0` = keep) |
| `TRANSCRIBE_ENGINE` | `local` | `local` (faster-whisper) or `openai` (hosted Whisper) |
| `WHISPER_MODEL` | `base` | `tiny` · `base` · `small` · `medium` · `large-v3` |
| `WHISPER_DEVICE` | `auto` | `auto` · `cpu` · `cuda` |
| `LLM_BASE_URL` | _(empty = off)_ | OpenAI-compatible endpoint for the AI extras |
| `LLM_API_KEY` | — | API key (any value for Ollama) |
| `LLM_MODEL` | `llama3.1:8b` | LLM model name (the UI also lists models from the endpoint) |
| `TRANSLATE_ENGINE` | `auto` | `auto` · `whisper` (→English) · `libretranslate` · `llm` · `off` |
| `LIBRETRANSLATE_URL` | _(empty)_ | Offline translator endpoint, for non-English without an LLM |

The full list, with the hosted-Whisper and tuning options, is in `.env.example`.

## How it works

Upload → ffmpeg pulls the audio to 16 kHz mono → faster-whisper transcribes it →
the segments get written out as `.srt`, `.vtt`, and text. If you asked for extras,
the transcript goes to your LLM for chapters, a summary, and/or a translation.

Jobs run on a background worker and live in a small SQLite database, so progress
survives a browser refresh or a container restart.

## Stack

Python / FastAPI + faster-whisper on the backend, React + Vite + Tailwind on the
front, ffmpeg for the audio, all in one multi-stage Docker image.

## Local development

```bash
make install     # .venv + frontend deps
make backend     # API on :8000 (autoreload)
make frontend    # Vite dev server on :5173, proxies /api → :8000
./scripts/dev.sh # both at once
make test        # backend tests
make lint        # ruff
```

## License

[MIT](LICENSE). Not affiliated with the original subvert — just a spiritual successor
so the idea doesn't die with it.
