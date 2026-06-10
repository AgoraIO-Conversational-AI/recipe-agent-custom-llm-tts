# Custom Audio LLM Endpoint — Mock

An OpenAI-compatible `POST /audio/chat/completions` server (port 8001) that Agora
cloud calls during a conversation. Instead of text, it returns **audio directly**
(`delta.audio`), which Agora plays over RTC with **no TTS step**. This mock emits a
sine-wave tone so you can exercise the full pipeline with **no API key**.

It has no `agora-agents` dependency — a plain FastAPI app, the boundary you replace
with your own audio source.

## The contract

`POST /audio/chat/completions`, streaming SSE:

1. **Transcript chunk** — `choices[0].delta.audio = {"id": <id>, "transcript": <text>}`.
2. **Audio chunks** — `choices[0].delta.audio = {"id": <id>, "data": <base64 PCM>}`.
3. Terminate with `data: [DONE]`.

Audio format: **PCM16, 16 kHz, mono, 1280-byte (40 ms) chunks**. Non-streaming
requests are rejected with HTTP 400.

> **The transcript is functionally required, not cosmetic.** Agora cloud stores
> `audio.transcript` as the agent's conversation context; if you omit it, the agent
> will not remember what it said. (Word-level `words` timestamps are optional and not
> emitted by this mock.)

## Run

```bash
cd llm
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/custom_llm_server.py     # serves on CUSTOM_LLM_PORT (default 8001)
```

## Expose it publicly

Agora cloud — not the browser — calls this server, so it must be reachable from the
public internet:

```bash
ngrok http 8001
```

Then set `CUSTOM_LLM_URL=https://<tunnel>/audio/chat/completions` in `server/.env.local`.

## Auth

This mock does **not** authenticate. A production endpoint should validate the
`Authorization: Bearer <CUSTOM_LLM_API_KEY>` header Agora cloud forwards.

## Replace the mock

Replace `generate_tone()` in `src/custom_llm_server.py` with your real audio source
(a TTS engine, your own model, or pre-recorded PCM), keeping the PCM format and the
transcript chunk.
