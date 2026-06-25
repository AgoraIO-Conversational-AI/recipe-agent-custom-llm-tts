# 06 · Interfaces

> Boundary contracts: backend routes, the `/api/*` rewrite map, env vars, the response envelope, and the audio SSE contract.

## Backend routes (port 8000)

The browser calls the agent routes as `/api/<name>`; Next rewrites to the backend `/<name>`. Agora cloud calls the audio route directly at its public URL.

### `GET /get_config`

- Query (optional): `channel?: string`, `uid?: int` (≤ 0 or missing → backend generates one).
- Returns `data`: `{ app_id, token, uid (string), channel_name, agent_uid (string) }`.
- Token is a Token007 RTC+RTM token, expiry 3600s, for a concrete non-zero UID.

### `POST /startAgent`

- Body: `{ channelName: string, rtcUid: int, userUid: int, parameters?: object }`.
  - `parameters.output_audio_codec?: string` is the only honored parameter field.
- Returns `data`: `{ agent_id, channel_name, status: "started" }`.
- 400 if `channelName`/`rtcUid`/`userUid` invalid.
- 500 if `Agent()` failed to initialize (missing env vars).

### `POST /stopAgent`

- Body: `{ agentId: string }`.
- Returns `{ code: 0, msg: "success" }` (no `data`).

### `POST /audio/chat/completions` (mounted)

Agora cloud calls this endpoint at `<CUSTOM_LLM_URL>` with `Authorization: Bearer <CUSTOM_LLM_API_KEY>`. See [audio_endpoint_contract](L2/audio_endpoint_contract.md) for the full SSE format.

- Body: OpenAI-compatible `ChatCompletionRequest` with `modalities: ["text", "audio"]` and `stream: true`.
- Returns: `text/event-stream`. Non-streaming requests → 400.
- SSE order: 1) transcript chunk, 2) PCM audio chunks, 3) `data: [DONE]`.

### `GET /audio/health`

- Returns `{ status: "ok", service: "custom-llm-tts-mock" }`.

## Response envelope

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` omitted when the route has no payload. Non-zero `code` or missing `data` = error on the client side.

## Rewrite map (`web/next.config.ts`)

| Browser path        | Backend destination |
| ------------------- | ------------------- |
| `/api/get_config`   | `/get_config`       |
| `/api/startAgent`   | `/startAgent`       |
| `/api/stopAgent`    | `/stopAgent`        |

`rewrites()` returns `[]` when `AGENT_BACKEND_URL` is unset. The contract is asserted by `verify-api-contracts.ts` and exercised by `verify-local-proxy.ts`.

## Browser API client (`web/src/services/api.ts`)

- `getConfig({ channel?, uid? }) → GetConfigResponse`
- `startAgent(channelName, rtcUid, userUid) → agent_id`
- `stopAgent(agentId) → void`

## Environment variables

| Variable                | Scope         | Required | Default                               |
| ----------------------- | ------------- | :------: | ------------------------------------- |
| `AGORA_APP_ID`          | backend       |    ✅    | —                                     |
| `AGORA_APP_CERTIFICATE` | backend       |    ✅    | —                                     |
| `CUSTOM_LLM_URL`        | backend       |    ✅    | — (no localhost default; must be public) |
| `CUSTOM_LLM_API_KEY`    | backend       |    ✅    | `any-key-here`                        |
| `CUSTOM_LLM_MODEL`      | backend       |          | `audio-mock`                          |
| `AGENT_GREETING`        | backend       |          | `Hi there! I'm a custom audio agent.` |
| `AGENT_BACKEND_URL`     | web (deploy)  |    ✅\*  | `http://localhost:8000` (dev)         |
| `PORT`                  | backend (env) |          | `8000` — do **not** put in `.env.example` |

\* Required wherever the web app is deployed; rewrites are empty without it.

## `CustomLLM` vendor config (`agent.py`)

`CustomLLM(base_url, api_key, model, output_modalities=["audio"], greeting_message, failure_message, max_history)`:

- `base_url` = `CUSTOM_LLM_URL`
- `api_key` = `CUSTOM_LLM_API_KEY`
- `model` = `CUSTOM_LLM_MODEL` (default `audio-mock`)
- `output_modalities=["audio"]` — tells Agora the endpoint returns audio; no TTS synthesis.

## Related Deep Dives

- [custom_llm_config](L2/custom_llm_config.md) — full vendor chain and session options.
- [audio_endpoint_contract](L2/audio_endpoint_contract.md) — detailed SSE format and PCM spec.
