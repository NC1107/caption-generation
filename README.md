# Caption Generation
This is meant to be a replacement for [subvert](https://github.com/aschmelyun/subvert) which seems to be abandoned. I have a similar video editing pipeline that I run locally so I thought it might be useful to offer another alternative with a more modern stack. I spin this up using qwen3:8b and get pretty good summaries/chapters/review. If anyone actually uses this wants some modifications or features, feel free to create a github issue and I'll get to it.

Local transcription with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and AI extras through any local or cloud LLM.

<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/2ccdc641-fa33-4630-a48f-4f38cb622951" />

## Quick start

```bash
cp .env.example .env        # optional — defaults work as-is
docker compose up -d        # → http://localhost:8000
```

Drop in a file, hit **Generate subtitles**. First run downloads the Whisper model
(~140 MB) to `./data`; everything (uploads, output, models, DB) lives there. Subtitles
and English translation are fully local and need no key. (Build locally with `--build`.)

### Images

| Image | Size | Translation |
|---|---|---|
| `ghcr.io/nc1107/caption-generation:latest` | ~1.4 GB | →English via Whisper; other languages via your LLM |
| `…:latest-translate` | ~3.5 GB | bundled offline translator (LibreTranslate) — every language, no LLM |

For the bundled translator, set `image: ghcr.io/nc1107/caption-generation:latest-translate` in `docker-compose.yml`.

## Chapters, summaries & other-language translation

These use an LLM — set one of:

```ini
OPENROUTER_API_KEY=sk-or-...          # cloud, easiest
LOCAL_LLM_URL=http://ollama:11434/v1  # local (Ollama/LM Studio/vLLM)
```

Then pick a model in the UI — local models are denoted `(local)`, and once you set a valid
OpenRouter key you'll see `(cloud)` models. No Ollama yet? Bundle one with
`docker compose --profile ollama up -d`.

## Settings

All optional — see `.env.example` for the full list. The common ones:

| Variable | Default | |
|---|---|---|
| `PORT` | `8000` | Port to serve on |
| `MAX_UPLOAD_MB` | `51200` | Upload cap (~50 GB); `0` = no limit |
| `WHISPER_MODEL` | `base` | `tiny`·`base`·`small`·`medium`·`large-v3` |
| `OPENROUTER_API_KEY` / `LOCAL_LLM_URL` | — | Enable cloud / local LLM |

**GPU:** uncomment the GPU blocks in `docker-compose.yml`, then `docker compose up -d --build`.

## Roadmap

Ideas, not built yet:

- **Auth / login** — protect a shared instance
- **Render pipeline** — burn captions into the video
- **Silence cutting** — auto-trim long dead-air gaps
- **Richer media info** — codecs, bitrate, streams
- **LLM review** — score chapters against a custom rubric to keep/drop them

## Develop

```bash
make install   # deps    make backend / make frontend   # dev servers
make test      # pytest  make lint                       # ruff
```

[MIT](LICENSE).
