# 07 · Gotchas

> Non-obvious pitfalls specific to the custom-llm-tts recipe. Read before changing the agent, env, audio endpoint, or verify scripts.

## `CUSTOM_LLM_URL` must be public (no localhost default)

Agora cloud (not your backend) calls `CUSTOM_LLM_URL`. A `localhost` or `127.0.0.1` URL lets the agent "start" while the LLM calls silently fail cloud-side. There is intentionally **no localhost default** — `Agent.__init__` raises `ValueError` if `CUSTOM_LLM_URL` is unset. Use ngrok or another tunnel for local dev.

`doctor:local` warns (but does not fail) if `CUSTOM_LLM_URL` contains `localhost` or `127.0.0.1`.

## Keep `.with_tts()` — the inert TTS vendor is required

`agent.py` calls `.with_tts(MiniMaxTTS(...))`. With `output_modalities=["audio"]`, the TTS vendor is **never invoked** at runtime — the PCM audio from your endpoint plays directly. However, the agora-agents builder **requires** a TTS in cascading mode (both 1.4 and 2.0 raise "TTS configuration is required" without it). Do not remove `.with_tts()`.

## The transcript chunk is required

The first SSE chunk must include `delta.audio.transcript`. Agora cloud stores it as the agent's conversation context. Omitting it means the agent has no memory of what it said — responses lose context across turns.

## `server/src/llm.py` must not import `agora_agent`

`llm.py` is the provider-agnostic component developers replace. `test_llm_mount.py` checks this via AST inspection — any `agora*` import causes the test to fail.

## Token endpoints are publicly reachable

The backend must be public so Agora cloud can reach `/audio`. This also makes `/get_config`, `/startAgent`, and `/stopAgent` publicly reachable. They are **unauthenticated** in this recipe. Add auth/rate-limiting before any real deployment.

## Do not put `PORT` in `server/.env.example`

`verify:local:fastapi` and `verify:local:llm` inject a random `PORT` and load env with `load_dotenv(override=True)`. A `PORT` line in `.env.example` (copied to `.env.local`) would clobber the injected port and break the smoke tests.

## Keep `/api/*` ownership in rewrites

Adding `web/app/api/**/route.ts` for agent/token logic breaks the boundary — `verify-api-contracts.ts` explicitly fails if a `route.ts` exists under `app/api`. Token logic belongs in `server/`.

## camelCase request fields

`StartAgentRequest` uses `channelName`, `rtcUid`, `userUid` (camelCase) to match the browser client. Renaming one side without the other breaks the contract tests.

## Audio format is PCM16, 16 kHz, mono

Base64-encoded audio chunks in `delta.audio.data` must be PCM16 (16-bit signed little-endian), 16 kHz sample rate, mono. The wrong format causes garbled or silent audio. The mock uses 1280-byte (~40 ms) chunks.

## Local calls under a global proxy

Global proxies (Clash, etc.) can break `localhost`/RFC-1918 traffic. Configure the proxy to send `127.0.0.1`, `localhost`, and private ranges DIRECT, or use `socksio` (in `requirements.txt`) with `all_proxy` to route through SOCKS.

## Related Deep Dives

- [custom_llm_config](L2/custom_llm_config.md) — correct vendor chain wiring.
- [audio_endpoint_contract](L2/audio_endpoint_contract.md) — SSE format, PCM spec, transcript requirement.
