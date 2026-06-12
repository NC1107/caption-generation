# Caption Generation
This is meant to be a replacement for [subvert](https://github.com/aschmelyun/subvert) which seems to be abandoned. I have a similar video editing pipeline that I run locally so I thought it might be useful to offer another alternative with a more modern stack. I spin this up using qwen3:8b and get pretty good summaries/chapters/review. If anyone actually uses this wants some modifications or features, feel free to create a github issue and I'll get to it.

Local transcription with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and AI extras through any local or cloud LLM.

<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/2ccdc641-fa33-4630-a48f-4f38cb622951" />

## Quick start

```bash
cp .env.example .env        # optional — defaults work as-is
docker compose up -d        # → http://localhost:8000
```

## Chapters, summaries & other-language translation

These use an LLM — set one of:

```ini
OPENROUTER_API_KEY=sk-or-...          # cloud, easiest
LOCAL_LLM_URL=http://ollama:11434/v1  # local (Ollama/LM Studio/vLLM)
```
Then pick a model in the UI, local models are denoted with (local) and after you set a valid api key for openrouter you will see models denoted with (cloud)



## Develop

```bash
make install   # deps    make backend / make frontend   # dev servers
make test      # pytest  make lint                       # ruff
```

[MIT](LICENSE).
