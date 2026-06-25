# 05 · Workflows

> Step-by-step guides for the common changes in this recipe. Each ends with the narrowest verify command to run.

## Replace the mock with a real audio endpoint

The mock (`server/src/llm.py`, `generate_tone()`) emits a sine-wave tone. To swap in a real model:

1. Replace `generate_tone()` (and `split_into_chunks`) with your real audio source.
2. Keep the SSE contract: transcript chunk first, then base64 PCM16/16kHz/mono chunks, then `data: [DONE]`.
3. Include `audio.transcript` in the first chunk — Agora stores it as conversation context.
4. Keep `llm.py` free of `agora_agent` imports.
5. Verify: `cd server && pytest tests -v` (SSE contract + import boundary tests still pass).

## Add or change a browser-facing route

1. Add the FastAPI handler in `server/src/server.py` (return the `{ code, msg, data }` envelope).
2. Add the `/api/<name>` → `/<name>` mapping in `web/next.config.ts` `rewrites()`.
3. Add a client helper in `web/src/services/api.ts`.
4. Extend `web/scripts/verify-api-contracts.ts` with the new path + envelope assertions.
5. Verify: `bun run verify:web` (and `bun run verify:local:fastapi` if the route should go through the real backend).

## Change the agent prompt / greeting / model name

1. Greeting: set `AGENT_GREETING` (env) or edit the default in `server/src/agent.py`.
2. Model name: set `CUSTOM_LLM_MODEL` (default `audio-mock`); passed to the custom endpoint as `model`.
3. Verify: `bun run verify:backend` (compile) + `cd server && pytest tests -v`.

## Change LLM or STT vendor config

1. Edit `Agent.start()` in `server/src/agent.py` — `CustomLLM`, `DeepgramSTT`, or `MiniMaxTTS` constructors.
2. Do **not** remove `.with_tts()` — see [07_gotchas](07_gotchas.md).
3. Verify: `cd server && pytest tests -v`.

## Adjust session parameters (codec, scenario)

1. Edit the `parameters` dict in `Agent.start()` (`audio_scenario`, `data_channel`, `enable_metrics`, etc.). `output_audio_codec` is also accepted per-request via `parameters` on `POST /startAgent`.
2. Verify: `bun run verify:local:fastapi`.

## Run / debug locally

```bash
bun run dev              # both processes; needs tunnel running + CUSTOM_LLM_URL set
bun run doctor:local     # check creds + .env.local + CUSTOM_LLM_URL before a live call
```

## Verify before finishing

| Change touches…                    | Run                                                                               |
| ---------------------------------- | --------------------------------------------------------------------------------- |
| Web only                           | `bun run verify:web`                                                               |
| Backend logic / vendor config      | `bun run verify:backend` + `cd server && pytest tests -v`                          |
| Audio endpoint SSE contract        | `bun run verify:local:llm` (or `cd server && pytest tests -v`)                    |
| Route/proxy boundary               | `bun run verify:web:proxy` and/or `bun run verify:local:fastapi`                  |
| Anything end-to-end (local)        | `bun run verify:local`                                                             |

## Deploy

1. Deploy `web/` as a Next.js app.
2. Deploy `server/` on a host that is **publicly reachable** (Agora cloud calls `/audio/chat/completions`). The published backend-only image is built via `docker.yml` on `v*` tags.
3. Set `AGENT_BACKEND_URL` in the web deployment so rewrites reach the backend.
4. Set `CUSTOM_LLM_URL` to the public URL of your deployed backend `/audio/chat/completions`.
5. Add auth/rate-limiting in front of the token endpoints before production use (see [08_security](08_security.md)).

## Related Deep Dives

- [custom_llm_config](L2/custom_llm_config.md) — CustomLLM build details, vendor chain, session options.
- [audio_endpoint_contract](L2/audio_endpoint_contract.md) — SSE format, PCM spec, transcript requirement, mock replacement guide.
- [session_lifecycle](L2/session_lifecycle.md) — client-side join/teardown.
