# Agent Development Guide

For coding agents working in `recipe-agent-custom-llm-tts`. This repository is the
**custom-llm-tts** recipe in the Agora Conversational AI recipes family.

## How to Load

This repository uses progressive disclosure documentation. Docs live under
`docs/ai/` in three levels.

1. Read [docs/ai/L0_repo_card.md](docs/ai/L0_repo_card.md) to identify the repo.
2. This repo declares `Recipe Role: base`; read [docs/ai/RECIPE.md](docs/ai/RECIPE.md) before changing reusable recipe contracts.
3. Load ALL 8 files in [docs/ai/L1/](docs/ai/L1/). They are small — load all upfront.
4. Follow L2 deep-dive links only when L1 isn't detailed enough. The index is at [docs/ai/L1/L2/_index.md](docs/ai/L1/L2/_index.md).

The sections below remain the canonical contributor handbook for hands-on work;
the `docs/ai/` tree is the structured summary used by AI agents.

## System shape

- **`server/`** — Python FastAPI backend (:8000), a **single process**. Owns Agora
  token generation and agent lifecycle, and **mounts the custom audio endpoint at
  `/audio`** (`server/src/llm.py`, OpenAI-compatible `POST /audio/chat/completions`
  returning transcript + base64 PCM16/16kHz audio). Uses
  `CustomLLM(output_modalities=["audio"])`; no TTS is *used* at runtime, but an
  **inert TTS vendor is still configured** because the agora-agents builder requires
  `.with_tts()` in cascading mode (1.4 and 2.0 alike). SDK: `agora-agents>=2.3.0`
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

## Commands

```bash
bun run setup
bun run dev
bun run doctor
bun run doctor:local
bun run verify         # web-only, no creds
bun run verify:local   # full local gate
```

Narrower checks: `bun run verify:backend`, `bun run verify:backend:pytest`,
`bun run verify:local:fastapi`, `bun run verify:local:llm`, `bun run verify:web:proxy`.
Backend tests: `cd server && pytest tests -v`.

## Done criteria

1. Run the narrowest relevant verify command.
2. Web changes: `bun run verify:web` passes.
3. Backend changes: `bun run verify:local` (or narrower `verify:local:fastapi` /
   `verify:local:llm` / `verify:backend`) passes.
4. If you change env vars or setup steps, update the root README, the module README,
   and the `.env.example` files together.
5. If the change touches workflows, interfaces, gotchas, or security details,
   update the matching file under [docs/ai/L1/](docs/ai/L1/) and bump
   `Last Reviewed` in [docs/ai/L0_repo_card.md](docs/ai/L0_repo_card.md).

## Git Conventions

### Commit messages — conventional commits

- **Format:** `type: description` or `type(scope): description`
- **Types:** `feat:` (new feature), `fix:` (bug fix), `chore:` (maintenance, version bumps), `test:` (test additions/changes), `docs:` (documentation)
- **Scoped variant:** `feat(scope):`, `fix(scope):` — e.g. `fix(server): validate custom llm url`
- **Lowercase after prefix** — `feat: add feature`, not `feat: Add feature`
- **Present tense** — "add feature", not "added feature"

### Branch names

- **Format:** `type/short-description` — lowercase, hyphen-separated
- **Types match commit types:** `feat/`, `fix/`, `chore/`, `test/`, `docs/`
- **Examples:** `feat/real-tts-endpoint`, `fix/transcript-missing`, `docs/progressive-disclosure`

### General rules

- **Repo-local `AGENTS.md` is the authoritative source for repo conventions.**
- **No AI tool names** — never mention claude, cursor, copilot, cody, aider, gemini, codex, chatgpt, or gpt-3/4 in commit messages or PR descriptions.
- **No Co-Authored-By trailers** — omit AI attribution lines.
- **No `--no-verify`** — let git hooks run normally.
- **No git config changes** — do not modify `user.name` or `user.email`.

## Doc Commands

| Command       | When to use                                                                  |
| ------------- | ---------------------------------------------------------------------------- |
| generate docs | No `docs/ai/` directory exists yet                                           |
| update docs   | Code changed since the `Last Reviewed` date in L0                            |
| test docs     | Verify docs give agents the right context (writes `docs/ai/test-results.md`) |
| fix docs      | Close findings from a docs review or test run                                |

See the [progressive disclosure standard](https://github.com/AgoraIO-Community/ai-devkit/blob/main/docs/standard/progressive-disclosure-standard.md) and [workflows](https://github.com/AgoraIO-Community/ai-devkit/blob/main/docs/workflows/progressive-disclosure-docs.md) for the full specification.
