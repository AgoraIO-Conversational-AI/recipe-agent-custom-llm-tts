# 02 · Architecture

> Two co-located processes. The browser talks only to Next.js `/api/*`, which rewrites to the FastAPI agent backend. The backend is **one process with two concerns**: it owns Agora tokens and agent lifecycle, and also mounts the custom audio endpoint at `/audio` that Agora cloud calls directly.

## Topology

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js (web/)  ──rewrite──▶  Agent backend (server/, :8000)
                                 │  CustomLLM(base_url=CUSTOM_LLM_URL, output_modalities=["audio"])
                                 ▼
                              Agora ConvoAI Cloud
                                 │  user speech → Deepgram STT (managed) → text
                                 │  POST <CUSTOM_LLM_URL>  (Authorization: Bearer)
                                 ▼
                              /audio/chat/completions  (mounted in server/, same :8000, public via tunnel)
                                 │  returns transcript + base64 PCM audio (SSE)
                                 ▼
                              Agora streams PCM directly to RTC — NO TTS
                                 │  RTM transcript + metrics → web UI
```

- **`web/`** — Next.js 16 / React 19 / TypeScript. Owns UI plus the RTC/RTM client lifecycle. Calls only `/api/*`.
- **`server/`** — Python FastAPI (:8000). Owns Agora token generation and agent session lifecycle. SDK: `agora-agents>=2.3.0` (`import agora_agent`).
- **`server/src/llm.py`** — The mounted custom audio endpoint. Provider-agnostic, no `agora_agent` import. This is the part you replace with your real model.

## Single-backend, two concerns

`server/src/server.py` mounts `llm.app` at `/audio`:

```
/get_config         (token/agent — server.py)
/startAgent         (token/agent — server.py)
/stopAgent          (token/agent — server.py)
/audio/chat/completions  (custom audio — llm.py, mounted)
/audio/health       (health — llm.py, mounted)
```

One `ngrok http 8000` exposes everything. Agora cloud calls `/audio/chat/completions` via the public URL.

## Request lifecycle

1. Browser `GET /api/get_config` → Next rewrites to backend `/get_config`; backend mints Token007 and returns channel + UIDs.
2. Browser joins the RTC channel, then `POST /api/startAgent`; backend builds `CustomLLM` vendor and starts an async agent session.
3. Agora routes user speech to Deepgram STT; transcript text goes to `POST <CUSTOM_LLM_URL>`.
4. The mounted endpoint (`/audio/chat/completions`) streams a transcript chunk then base64 PCM audio chunks via SSE.
5. Agora plays the PCM audio directly to the RTC channel — no TTS step.
6. RTM delivers transcript + metrics to the web UI.
7. `POST /api/stopAgent { agentId }` ends the session.

## Why audio output (no TTS)

`output_modalities=["audio"]` on `CustomLLM` tells Agora the LLM stage returns audio. An **inert TTS vendor** (`MiniMaxTTS`) is still configured in `agent.py` because the agora-agents builder requires `.with_tts()` in cascading mode — it raises "TTS configuration is required" otherwise. With audio output modalities, the TTS is never invoked.

## Key abstractions

- **`Agent`** (`server/src/agent.py`) — async wrapper around `AgoraAgent`; owns `AsyncAgora` client, `CustomLLM`/`DeepgramSTT`/`MiniMaxTTS` vendors, and the in-memory `_sessions` map keyed by `agent_id`.
- **`llm.app`** (`server/src/llm.py`) — standalone FastAPI app mounted at `/audio`; provider-agnostic (no Agora SDK), enforced by `test_llm_mount.py`.
- **Rewrite proxy** (`web/next.config.ts`) — only browser→backend boundary; no Next Route Handlers exist for agent/token logic.

## Tech decisions

- **Single process, two concerns** — simplifies deployment: one port, one tunnel.
- **Rewrites, not Route Handlers** — hides backend placement behind `/api/*`; same client works locally and deployed.
- **Cascading STT→LLM** — Deepgram STT transcribes user speech into text before the custom endpoint is called; the endpoint receives the conversation history.
- **`CUSTOM_LLM_URL` required + public** — no localhost default; a localhost URL would silently fail cloud-side.

## Related Deep Dives

- [custom_llm_config](L2/custom_llm_config.md) — full `CustomLLM` vendor build, vendors chain, VAD, and session options.
- [audio_endpoint_contract](L2/audio_endpoint_contract.md) — SSE format, PCM16 spec, transcript requirement, and mock replacement guide.
- [session_lifecycle](L2/session_lifecycle.md) — browser orchestration of config + start/stop, RTC/RTM, transcript mapping.
