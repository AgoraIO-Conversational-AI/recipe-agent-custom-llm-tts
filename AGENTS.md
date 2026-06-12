# Agent Development Guide

For coding agents working in `recipe-agent-custom-llm-tts`. This repository is the
**custom-llm-tts** recipe (`Recipe Role: custom-llm-tts`) in the Agora Conversational
AI recipes family, derived from the base `agent-quickstart-python` template via the
`recipe-agent-custom-llm` recipe.

## System shape

- **`server/`** — Python FastAPI backend (:8000), a **single process**. Owns Agora
  token generation and agent lifecycle, and **mounts the custom audio endpoint at
  `/audio`** (`server/src/llm.py`, OpenAI-compatible `POST /audio/chat/completions`
  returning transcript + base64 PCM16/16kHz audio). Uses
  `CustomLLM(output_modalities=["audio"])`; no TTS is *used* at runtime, but an
  **inert TTS vendor is still configured** because the agora-agents builder requires
  `.with_tts()` in cascading mode (1.4 and 2.0 alike). SDK: `agora-agents>=2.0.0`
  (`import agora_agent`) — but `server/src/llm.py` itself stays free of it
  (provider-agnostic; the component a developer replaces). Because Agora cloud reaches
  `/audio` over the public internet, the whole backend is public, so the token
  endpoints are co-public and unauthenticated — see ARCHITECTURE.md.
- **`web/`** — Next.js frontend (:3000), resynced from the base quickstart with
  custom-llm-tts branding; pipeline metrics show STT + Custom LLM (audio), no TTS.
- Auth: Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.

## Routing / ownership

- UI and RTC/RTM lifecycle live in `web/`; `/api/*` are Next rewrites to the backend.
- Token generation and agent lifecycle live in `server/src/`.
- The audio `/audio/chat/completions` contract lives in `server/src/llm.py`, mounted
  at `/audio` by `server/src/server.py`.

## Patterns / invariants

- The endpoint returns **audio** (`delta.audio.data`, base64 PCM16/16kHz/mono); no
  TTS is used at runtime (`output_modalities=["audio"]`). A TTS vendor is still
  configured (inert) only to satisfy the builder — see anti-patterns.
- The **transcript** (`delta.audio.transcript`) is required — it is stored as agent
  context; omitting it loses conversation memory.
- `CUSTOM_LLM_URL` is required, must be public, and ends in `/audio/chat/completions`
  (no localhost default). `CUSTOM_LLM_API_KEY` is required by `CustomLLM`.
- Keep `server/src/llm.py` free of `agora-agents` (enforced by
  `server/tests/test_llm_mount.py`).

## Anti-patterns

- Do not REMOVE `.with_tts()` — the agora-agents builder (1.4 and 2.0 alike) raises
  "TTS configuration is required" without it in cascading mode. The TTS is inert
  (`output_modalities=["audio"]` means there is no text for it to synthesize);
  it exists only to satisfy the builder.
- Do not drop the transcript chunk from the endpoint.
- Do not add `agora-agents` to `server/src/llm.py` (the import-boundary test fails).
- Do not default `CUSTOM_LLM_URL` to localhost.
- Do not put `PORT` in `server/.env.example` (it would clobber the random port the
  fastapi smoke test injects via `load_dotenv(override=True)`).
- Do not link to `docs/ai/` — that progressive-disclosure tree is not present.

## Commands

```bash
bun run setup
bun run dev
bun run doctor
bun run doctor:local
bun run verify         # web-only, no creds
bun run verify:local   # full local gate
```

## Done criteria

1. Run the narrowest relevant verify command.
2. Web changes: `bun run verify:web` passes.
3. Backend changes: `bun run verify:local` (or narrower `verify:local:fastapi` /
   `verify:local:llm` / `verify:backend`) passes.
4. If you change env vars or setup steps, update the root README, the module README,
   and the `.env.example` files together.

## Git conventions

- Conventional Commits (`feat`/`fix`/`chore`/`test`/`docs`), lowercase after prefix,
  present tense. No AI tool names, no `Co-Authored-By`, no `--no-verify`.
- Branch names: `type/short-description`.
