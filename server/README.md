# Agora Agent Backend — Custom LLM-TTS Recipe

FastAPI service that owns Agora token generation and agent session lifecycle for
the custom-llm-tts recipe (port 8000). It is the service the web client reaches
through the Next.js `/api/*` rewrite proxy.

## What's different from the base quickstart

The LLM stage uses `CustomLLM` with `output_modalities=["audio"]`, pointed at your
own endpoint (the `llm/` server). Agora cloud calls that endpoint and plays the
returned PCM audio directly over RTC — **no TTS is used**. STT (Deepgram) still
transcribes the user's speech into text for the LLM.

> `agent.py` still calls `.with_tts()` with an inert TTS vendor: the agora-agents
> 2.0 builder requires one in cascading mode, but with `["audio"]` output it has
> nothing to synthesize and is never used.

## Run

Use the repo-root `README.md` for the full local flow (`bun run dev`). To work on
this module directly:

```bash
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/server.py
```

## Environment

`server/.env.example` is the template. Required:

- `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE` — Agora project credentials.
- `CUSTOM_LLM_URL` — the **public** URL of your `llm/` endpoint, ending in
  `/audio/chat/completions`. Agora cloud calls it, so it cannot be `localhost`.
- `CUSTOM_LLM_API_KEY` — forwarded by Agora cloud as `Authorization: Bearer`.
  Required by the `CustomLLM` vendor.

Optional: `CUSTOM_LLM_MODEL` (default `audio-mock`), `AGENT_GREETING`, `PORT`
(default `8000`).

## API

- `GET /get_config` — token + channel/UID config
- `POST /startAgent` — start an agent session
- `POST /stopAgent` — stop an agent session

`bun run verify:local:fastapi` exercises these routes through the Next proxy with
a fake agent — no live Agora session required.
