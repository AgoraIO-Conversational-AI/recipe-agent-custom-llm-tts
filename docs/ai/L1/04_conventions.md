# 04 · Conventions

> Coding patterns shared across `server/` and `web/`. Follow these to keep local and deployed modes aligned.

## Boundary ownership

- Browser code calls only `/api/*`. Backend placement is hidden behind Next rewrites (`web/next.config.ts`).
- **Never** add `web/app/api/**/route.ts` for agent/token logic — `verify-api-contracts.ts` fails the build if a `route.ts` appears under `app/api`.
- Token generation and the App Certificate stay in `server/`.
- `server/src/llm.py` stays **free of `agora_agent` imports** — it is the provider-agnostic part developers replace. `test_llm_mount.py` enforces this via AST inspection.

## Backend (Python / FastAPI)

- Async throughout: route handlers are `async def`; the agent uses `AsyncAgora` and `create_async_session`.
- Request bodies are Pydantic models (`StartAgentRequest`, `StopAgentRequest`). Field names are **camelCase** (`channelName`, `rtcUid`, `userUid`) to match the browser client.
- Error mapping is centralized: `_to_http_error()` maps `ValueError → 400`, `RuntimeError → 500`, else 500. `_log_route_error()` logs with safe context + traceback. Raise plain `ValueError`/`RuntimeError`; let the route convert.
- Logging via `logging.getLogger("uvicorn.error")`.
- Env read with `os.getenv`; `.env.local` then `.env` loaded with `override=True`.
- `Agent.__init__` validates `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, and `CUSTOM_LLM_API_KEY` — the server fails to boot if any is missing.

## Response envelope

All backend JSON responses use:

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` is present only when the route returns a payload. The browser client treats `code !== 0` (or missing `data`) as an error.

## Audio endpoint (`llm.py`)

- `POST /chat/completions` (mounted at `/audio/chat/completions`) is SSE-only (`stream: true` required; 400 otherwise).
- SSE order: **1)** transcript chunk (`delta.audio.transcript`), **2)** PCM audio chunks (`delta.audio.data`, base64), **3)** `data: [DONE]`.
- Audio format: PCM16, 16 kHz, mono, 1280-byte chunks (~40 ms each).
- The transcript chunk is **required** — Agora cloud stores it as agent context; omitting it loses conversation memory.
- Keep `llm.py` free of `agora_agent` (import-boundary test fails if violated).

## Vendor chain

- `CustomLLM(output_modalities=["audio"])` is the key vendor. It tells Agora cloud the LLM returns audio; no TTS synthesis occurs.
- `DeepgramSTT(model="nova-3")` transcribes user speech before the custom endpoint is called.
- `MiniMaxTTS` is wired via `.with_tts()` but is **inert** — required by the builder, never invoked at runtime.
- Do not remove `.with_tts()` — the agora-agents builder raises "TTS configuration is required" without it in cascading mode.

## Web (TypeScript / Next.js)

- Lint/format with Biome (`bun run lint`, `bun run lint:fix` in `web/`).
- RTC client creation must be StrictMode-safe (strict mode is on).
- Transcript speaker mapping uses real UIDs (`normalizeTranscript` maps `uid === '0'` to the local UID).
- API client lives in `src/services/api.ts`; UI never calls `fetch` to the backend directly.

## Testing approach

- Backend: `pytest` in `server/`, standalone — `conftest.py` fakes env and SDK session; no cloud, tunnel, or real creds needed.
- Web: contract/proxy/fastapi/llm smoke scripts under `web/scripts/` run without live Agora calls.
- Run the **narrowest** relevant verify command before finishing (see [05_workflows](05_workflows.md)).

## Doc upkeep

When you change request/response contracts, env vars, audio SSE format, or workflow, update all affected modules, READMEs, `.env.example`, **and** the matching `docs/ai/L1/` file together, then bump `Last Reviewed` in [L0](../L0_repo_card.md).

## Related Deep Dives

- None.
