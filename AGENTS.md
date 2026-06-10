# Agent Development Guide

For coding agents working in `recipe-agent-custom-llm-tts`. This repository is the
**custom-llm-tts** recipe (`Recipe Role: custom-llm-tts`) in the Agora Conversational
AI recipes family, derived from the base `agent-quickstart-python` template via the
`recipe-agent-custom-llm` recipe.

## System shape

- **`server/`** — Python FastAPI agent backend (:8000). Owns Agora token generation
  and agent lifecycle. Uses `CustomLLM(output_modalities=["audio"])`; no TTS is
  *used* at runtime, but an **inert TTS vendor is still configured** because the
  agora-agents 2.0 builder requires `.with_tts()` in cascading mode.
  SDK: `agora-agents>=2.0.0` (`import agora_agent`).
- **`llm/`** — Python FastAPI custom **audio** endpoint (:8001). OpenAI-compatible
  `POST /audio/chat/completions` returning transcript + base64 PCM16/16kHz audio. No
  `agora-agents` dependency. This is the component a developer replaces.
- **`web/`** — Next.js frontend (:3000), resynced from the base quickstart with
  custom-llm-tts branding; pipeline metrics show STT + Custom LLM (audio), no TTS.
- Auth: Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.

## Routing / ownership

- UI and RTC/RTM lifecycle live in `web/`; `/api/*` are Next rewrites to the backend.
- Token generation and agent lifecycle live in `server/src/`.
- The audio `/audio/chat/completions` contract lives in `llm/src/`.

## Patterns / invariants

- The endpoint returns **audio** (`delta.audio.data`, base64 PCM16/16kHz/mono); no
  TTS is used at runtime (`output_modalities=["audio"]`). A TTS vendor is still
  configured (inert) only to satisfy the 2.0 builder — see anti-patterns.
- The **transcript** (`delta.audio.transcript`) is required — it is stored as agent
  context; omitting it loses conversation memory.
- `CUSTOM_LLM_URL` is required, must be public, and ends in `/audio/chat/completions`
  (no localhost default). `CUSTOM_LLM_API_KEY` is required by `CustomLLM`.
- Keep the `llm/` endpoint free of `agora-agents`.

## Anti-patterns

- Do not REMOVE `.with_tts()` — the agora-agents 2.0 builder raises "TTS
  configuration is required" without it in cascading mode. The TTS is inert
  (`output_modalities=["audio"]` means there is no text for it to synthesize);
  it exists only to satisfy the builder.
- Do not drop the transcript chunk from the endpoint.
- Do not add `agora-agents` to `llm/`.
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
