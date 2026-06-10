# Custom LLM-TTS Recipe Migration — Design

**Date:** 2026-06-10
**Status:** Approved
**Template repo:** `recipe-agent-custom-llm` (`git@github.com:AgoraIO-Conversational-AI/recipe-agent-custom-llm.git`) — the finished custom-llm recipe, used as the structural template.
**Source of the recipe logic:** the `audio-modalities` recipe, preserved on the `backup/main-multi-recipe` branch of the original `agent-recipes-python` repo.
**Base quickstart (grandparent):** `agent-quickstart-python`.
**Authoritative reference:** Agora ConvoAI [Audio Modality guide](https://doc.shengwang.cn/doc/convoai/restful/user-guides/audio-modality) — confirms the config, response format, no-TTS behavior, transcript-as-context, and greeting protocol below.

## Goal

Build the **custom-llm-tts** recipe in the (currently near-empty) `recipe-agent-custom-llm-tts` repo by cloning the finished `recipe-agent-custom-llm` recipe and swapping its text-LLM behavior for **audio-output** behavior: the custom endpoint returns synthesized **audio directly** (playing both the LLM and TTS roles), bypassing Agora's TTS stage.

## Recipe Identity

- The endpoint emits audio directly; `output_modalities=["audio"]`; **no Agora TTS step**.
- Conceptually the same as the old `audio-modalities` recipe, rebranded as **custom-llm-tts**: "your endpoint is the LLM + TTS combined."
- Pipeline: `STT (Deepgram) → your /audio/chat/completions (returns PCM audio) → RTC`.

## Locked Decisions

1. **Seed from the template:** copy `recipe-agent-custom-llm` wholesale, then apply the audio deltas. Inherits all scaffolding, scripts, web, root-doc structure, the dark-theme fix, the proxy-aware docs, and the verify-harness pattern.
2. **SDK:** `agora-agents>=2.0.0`, `CustomLLM` vendor — same as the template. Audio is enabled by adding `output_modalities=["audio"]` (the SDK's `OpenAIOptions`/`CustomLLMOptions` support it; `to_config()` emits it).
3. **Env var names:** keep `CUSTOM_LLM_URL` / `CUSTOM_LLM_API_KEY` / `CUSTOM_LLM_MODEL` (template parity; the recipe *is* "custom-llm-tts"). The URL value points at the `/audio/chat/completions` path.
4. **Mock audio:** sine-wave tone generated in pure Python stdlib (`math`/`struct`/`base64`). **No binary assets** — the old recipe's `file.pcm`/`file.txt` (leftover test data) are dropped.
5. **Endpoint dir name:** keep **`llm/`** (the endpoint is still the LLM stage, now audio-emitting; keeps `web/scripts` `../llm` paths and template parity intact).
6. **Why not `OpenAIRealtime`:** that vendor is WebSocket-based (the OpenAI Realtime protocol). Our endpoint is HTTP SSE chat-completions-shaped, so `CustomLLM` is the correct vendor.

## Git Plan

The target repo currently has only `main` + `LICENSE`.
1. Work in a local clone of `recipe-agent-custom-llm-tts` on branch `feat/custom-llm-tts`.
2. Seed it from `recipe-agent-custom-llm` (exclude `.git`, `venv/`, `node_modules/`, `.next/`, `*.env.local`), preserving the existing `LICENSE`.
3. Apply the audio deltas (below).
4. PR `feat/custom-llm-tts` → `main`. No backup branch needed (fresh repo).

## Target Structure (identical to the template)

```
recipe-agent-custom-llm-tts/
├── server/                     # Agent backend :8000
│   ├── src/{__init__.py, server.py, agent.py}
│   └── scripts/run_fake_server.py
│   ├── .env.example · requirements.txt · .gitignore · README.md
├── llm/                        # Audio endpoint :8001 — POST /audio/chat/completions
│   ├── src/{__init__.py, custom_llm_server.py}
│   └── .env.example · requirements.txt · .gitignore · README.md
├── web/                        # Shared Next.js frontend
├── package.json · README.md · ARCHITECTURE.md · AGENTS.md · CLAUDE.md · LICENSE
```

## Component Deltas vs the custom-llm template

### `server/src/agent.py`

- Build the LLM with `CustomLLM` **plus `output_modalities=["audio"]`**, and **no TTS**:
  ```python
  from agora_agent.agentkit.vendors import CustomLLM, DeepgramSTT   # drop MiniMaxTTS

  llm = CustomLLM(
      base_url=self.custom_llm_url,        # CUSTOM_LLM_URL → .../audio/chat/completions
      api_key=self.custom_llm_api_key,     # required (CustomLLM needs base_url+api_key)
      model=self.custom_llm_model,
      output_modalities=["audio"],          # ← the audio switch
      greeting_message=self.greeting or None,
      failure_message="Please wait a moment.",
      max_history=10,
  )
  stt = DeepgramSTT(model="nova-3", language="en")
  # ... .with_stt(stt).with_llm(llm)   — NO .with_tts()
  ```
- Keep the template's validation: `CUSTOM_LLM_URL` required (no localhost default), `CUSTOM_LLM_API_KEY` required, `AGORA_APP_ID`/`AGORA_APP_CERTIFICATE` required.
- Prompt: a brief "respond with audio, keep it conversational" instruction (`AUDIO_AGENT_PROMPT`).
- **Keep the greeting.** Per the Audio Modality guide, the greeting is supported in audio mode through the messages protocol (a final `role: "assistant"` message is converted to audio and played directly) — it does **not** require TTS. So retain `AGENT_GREETING` and `greeting_message=`/`greeting=` in `agent.py`; the mock returns its tone for the greeting turn like any other.
- `advanced_features={"enable_rtm": True}` (drop `enable_tools` — not used for the audio path).
- Update the "KEY DIFFERENCE" comment to explain `output_modalities=["audio"]` + no TTS.
- `server.py` is unchanged from the template except: title "Agora Custom LLM-TTS Recipe Service" and channel prefix `custom-llm-tts-`.

### `llm/src/custom_llm_server.py` (the audio endpoint)

- Serve **`POST /audio/chat/completions`** (and `GET /health`). Streaming SSE:
  1. First chunk: transcript — `choices[0].delta.audio = {"id": <audio_id>, "transcript": <text>}`.
  2. Subsequent chunks: audio — `choices[0].delta.audio = {"id": <audio_id>, "data": <base64 PCM>}`.
  3. Terminate with `data: [DONE]`. (No `finish_reason:"stop"` chunk — the audio contract goes straight to `[DONE]` after the data chunks; all chunks carry `finish_reason: null`.)
- **Reject non-streaming** requests with HTTP 400 (carried from the working recipe).
- **The transcript is functionally required, not just cosmetic.** Per the guide, transcript content automatically enters the agent's context; **omitting `audio.transcript` blocks context storage** (the agent loses memory of what it said). So the mock always emits the transcript chunk, and the README/docstring state this explicitly.
- **`words` (word-level timestamps) are intentionally omitted** — transcript-only. They are an optional enhancement for caption alignment and not needed for this recipe.
- **Audio format:** PCM16, 16 kHz, mono; 1280-byte (40 ms) chunks; ~40 ms pacing between chunks (near real-time).
- **Mock source:** generate a sine-wave tone (e.g. 440 Hz, ~2 s, with a short fade in/out envelope) in stdlib (`math`/`struct`/`base64`); split into 1280-byte chunks; base64-encode each. No `file.pcm`/`file.txt`, no `aiofiles` (the old recipe listed `aiofiles` but never used it — it read files with sync `open()`).
- Load dotenv with `override=False` (same lesson as the template — lets the verify harness inject `CUSTOM_LLM_PORT`).
- Module docstring documents the audio SSE contract, the transcript-as-context requirement, and how to swap the mock for a real audio source.

### `llm/` support files

- `requirements.txt`: `fastapi`, `uvicorn`, `python-dotenv` (sine-wave needs only stdlib — no `aiofiles`, no `pydantic` extra).
- `.env.example`: `CUSTOM_LLM_PORT=8001`.
- `README.md`: the audio SSE contract, ngrok exposure, swap-the-mock guidance, "authenticate the Bearer header in production" note.

### `server/` support files

- `.env.example` (no `PORT` line — same rationale as the template):
  ```
  AGORA_APP_ID=your_agora_app_id
  AGORA_APP_CERTIFICATE=your_agora_app_certificate
  AGENT_GREETING=Hi there! I'm a custom audio agent.
  CUSTOM_LLM_URL=https://your-tunnel.ngrok-free.dev/audio/chat/completions
  CUSTOM_LLM_API_KEY=any-key-here
  CUSTOM_LLM_MODEL=audio-mock
  ```
- `requirements.txt`, `.gitignore`, `scripts/run_fake_server.py`: unchanged from the template.
- `README.md`: retargeted — the LLM stage returns audio (`output_modalities=["audio"]`), no TTS.

### `web/` deltas

- **Branding:** page title/description → "Custom LLM-TTS Recipe"; pre-call card copy → "bring your own audio-generating endpoint (LLM + TTS in one)".
- **`QuickstartPipelineMetrics`:** remove the **TTS row** — there is no separate TTS stage. Pipeline becomes `Deepgram STT` → `Custom LLM (audio)`. (Template had stt/llm/tts; drop tts, relabel llm.)
- `ConversationErrorCard.tsx` is left **unchanged** — its generic `llm:/asr:/tts:` error parsing is harmless in a no-TTS pipeline (a `tts:` error simply never arises). The only web changes are branding + the pipeline-metrics row.
- Everything else in `web/` is unchanged (RTC plays the agent's audio identically whether it came from TTS or directly from the endpoint). The dark-theme fix and all infra carry over.

### `web/scripts/verify-local-llm.ts` (audio contract harness)

- Boot the mock on a random `CUSTOM_LLM_PORT`, POST to **`/audio/chat/completions`** with `{model, messages, stream:true, modalities:["text","audio"]}`, and assert:
  - HTTP 200 and `content-type: text/event-stream`,
  - the stream contains a transcript delta (`"transcript"` inside `delta.audio`),
  - the stream contains at least one audio data delta (`"data"` inside `delta.audio`, non-empty base64),
  - the stream terminates with `data: [DONE]`.

### `package.json`

- `name`: `agora-conversational-ai-recipe-custom-llm-tts`.
- All scripts unchanged from the template (`setup`/`dev`/`doctor`/`doctor:local`/`verify*`/`clean`). `verify:backend` py_compiles `server/src/{server,agent}.py` + `llm/src/custom_llm_server.py`. `doctor:local` still checks `CUSTOM_LLM_URL` (+ localhost warning).

### Root docs

- `README.md`: retargeted to custom-llm-tts — onboarding (CLI + tunnel; `CUSTOM_LLM_URL` ends in `/audio/chat/completions`), env table, architecture, troubleshooting (incl. the proxy/loopback note and "agent joins but no audio → check the endpoint/URL"). Frames it as the custom-llm-tts recipe.
- `ARCHITECTURE.md`: three-process flow with the audio path (`… → Agora cloud POST <CUSTOM_LLM_URL> → endpoint returns PCM audio → RTC`, **no TTS**) and the same exposure-asymmetry rationale for two backends.
- `AGENTS.md`: retargeted; `Recipe Role: custom-llm-tts`; documents the audio contract and the `output_modalities=["audio"]` / no-TTS invariant. No `docs/ai/` links (that tree is deferred, same as the template).
- `CLAUDE.md`: pointer to `AGENTS.md`.
- `docs/ai/` progressive-disclosure tree is **deferred** (same as the template).

## Request Flow (target)

```
1. Browser GET /api/get_config            → FastAPI :8000 → Token007 + channel/UIDs
2. Browser POST /api/startAgent           → CustomLLM(base_url=CUSTOM_LLM_URL, output_modalities=["audio"])
3. Conversation:
     user audio → Agora cloud Deepgram STT (managed)
       → Agora cloud POST <CUSTOM_LLM_URL>  (Bearer)  → llm :8001 returns transcript + PCM audio SSE
       → Agora cloud streams that audio to RTC directly (NO TTS)
       → RTM transcript/metrics → web UI
4. Browser POST /api/stopAgent            → stop session
```

## Error Handling

- `server.py`: same `_log_route_error` / `_to_http_error` / `{code,msg,data}` envelope as the template.
- `llm/`: streaming SSE; **rejects non-streaming requests with HTTP 400**, matching the working recipe.

## Testing / Verification

- `bun run verify:backend` — py_compile `server/src` + `llm/src`.
- `bun run verify:local:fastapi` — server routes through the Next proxy with the fake agent (no live Agora).
- `bun run verify:local:llm` — boots the real audio mock and asserts the **audio** SSE contract (no keys needed).
- `bun run verify:web` / `verify:web:proxy` / `verify:web:build` — web contract + build.
- `bun run verify:local` — the full local gate.
- **Live check (manual):** real Agora creds + ngrok tunnel; start a conversation and confirm the agent's **audio** plays (the mock tone), with the transcript shown in the UI.

Definition of done: `bun run verify:local` passes and the README onboarding is consistent with `package.json` + `.env.example`.

## Risks / Notes

- The audio chunk shape (`delta.audio.{transcript,data}`) and PCM format (16 kHz / 16-bit / mono / 1280-byte chunks) are a **stable contract that does not change across the 1.4 → 2.0 SDK** (confirmed by the maintainer). They are carried verbatim from the working `audio-modalities` recipe, so this is not a migration risk — only the vendor wiring (`OpenAI` → `CustomLLM`) and SDK version change.
- `verify-local-llm.ts` resolves `../llm` from `web/`; unchanged because the dir stays `llm/`.
- Under a global loopback proxy, `verify` needs loopback routed DIRECT (documented in README troubleshooting, inherited from the template).
```