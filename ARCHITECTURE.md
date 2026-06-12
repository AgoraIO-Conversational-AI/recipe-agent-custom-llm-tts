# Architecture — Custom LLM-TTS Recipe

Two processes: the Next.js frontend and a single FastAPI backend. The browser talks
only to Next.js `/api/*`, which rewrites to the backend. The backend owns Agora
tokens and agent lifecycle, and also serves the custom audio endpoint (mounted at
`/audio`) that **Agora cloud** calls directly.

## Request flow

```
Browser
  │  GET /api/get_config            → token + channel/UIDs
  │  POST /api/startAgent           → start agent session
  ▼
Next.js  (rewrites /api/* → AGENT_BACKEND_URL)
  ▼
Agent backend (server/, :8000)
  │  CustomLLM(base_url=CUSTOM_LLM_URL, output_modalities=["audio"])
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT (managed) → text
  │  POST <CUSTOM_LLM_URL>   (Authorization: Bearer)   # URL already ends in /audio/chat/completions
  ▼
Custom audio endpoint (mounted at /audio in server/, same :8000, public via tunnel)
  │  returns transcript + base64 PCM audio (SSE)
  ▼
Agora ConvoAI Cloud streams that audio to RTC directly — NO TTS
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## Why audio output (no TTS)

`output_modalities=["audio"]` tells Agora cloud the LLM stage returns audio, so no
TTS is used — your endpoint's PCM plays straight to RTC. The transcript in each
response (`audio.transcript`) is stored as the agent's conversation context.

> Note: `server/src/agent.py` still calls `.with_tts()` with an **inert** TTS
> vendor. The agora-agents builder requires a TTS in cascading mode — in both 1.4
> and 2.0 (it raises
> "TTS configuration is required" otherwise); with `["audio"]` output there is no
> text for it to synthesize, so it is never used.

## One process, two concerns

`server/` runs a single process that serves both the token/agent endpoints and,
mounted at `/audio`, the OpenAI-compatible custom audio endpoint (`server/src/llm.py`).

The two concerns live in separate files with a one-directional dependency
(`server.py` imports `llm`, never the reverse), and `llm.py` has no `agora_agent`
import — it is the provider-agnostic part you replace with your own model.

Merging them onto one public surface is a deliberate trade. The Agora App Certificate
is only ever used in-memory to mint tokens — it never crosses a wire — so co-locating
the public `/audio` route with the token endpoints does not expose the certificate. It
does, however, make the token-minting endpoints (`/get_config`, `/startAgent`,
`/stopAgent`) publicly reachable. They are unauthenticated in this recipe; put auth /
rate-limiting in front of them (ingress, gateway, or a proxy) before any real
deployment.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.
- Agora cloud → custom audio endpoint: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`
  (the mock does not validate it; a production endpoint should).
