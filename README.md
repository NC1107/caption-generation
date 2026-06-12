# Caption Generation
This is meant to be a replacement for [subvert](https://github.com/aschmelyun/subvert) which seems to be abandoned. I have a similar video editing pipeline that I run locally so I thought it might be useful to offer another alternative with a more modern stack. I spin this up using qwen3:8b and get pretty good summaries/chapters/review. If anyone actually uses this wants some modifications or features, feel free to create a github issue and I'll get to it.

Local transcription with [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and AI extras through any local or cloud LLM.

<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/2ccdc641-fa33-4630-a48f-4f38cb622951" />

Subtitles and English translation work out of the box. For chapters, summaries, and
other-language translation, set `OPENROUTER_API_KEY` (cloud) or `LOCAL_LLM_URL` (local,
e.g. Ollama) in `.env`, then pick a model in the UI. Everything configurable lives in
`.env.example`.

Images (GHCR): `:latest` (CPU) · `:latest-gpu` (NVIDIA) · `:latest-translate` (bundled
offline translator, larger).

[MIT](LICENSE)
