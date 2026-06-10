# Architecture — Custom LLM-TTS Recipe

Three processes. The browser talks only to Next.js `/api/*`, which rewrites to the
agent backend. The agent backend owns Agora tokens and agent lifecycle. The custom
audio endpoint is a separate service that **Agora cloud** calls directly.

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
Custom audio endpoint (llm/, :8001, public via tunnel)
  │  returns transcript + base64 PCM audio (SSE)
  ▼
Agora ConvoAI Cloud streams that audio to RTC directly — NO TTS
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## Why audio output (no TTS)

`output_modalities=["audio"]` tells Agora cloud the LLM stage returns audio, so no
TTS module is configured — your endpoint's PCM plays straight to RTC. The transcript
in each response (`audio.transcript`) is stored as the agent's conversation context.

## Why two backends

`server/` and `llm/` are split because of an **exposure asymmetry**: `llm/` must be
reachable by Agora cloud over the **public internet** (hence the tunnel); `server/`
only needs to be reachable by the web tier and holds the App Certificate + token
logic. In production they may be co-deployed; kept separate here to make the boundary
explicit.

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
