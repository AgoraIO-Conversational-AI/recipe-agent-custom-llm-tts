# 08 · Security

> Trust boundaries, secret handling, and auth for the custom-llm-tts recipe.

## Trust boundaries

| Hop                              | Auth                                                                              |
| -------------------------------- | --------------------------------------------------------------------------------- |
| Browser → agent backend          | None in local dev (the `/api/*` rewrite is same-origin).                          |
| Agent backend → Agora cloud      | Token007, generated from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.                |
| Agora cloud → custom audio endpoint | `Authorization: Bearer <CUSTOM_LLM_API_KEY>` forwarded by Agora cloud.        |
| Token endpoints (deployed)       | **Unauthenticated** — add auth/rate-limiting before production use.               |

## Secret handling

- **Server-only secrets:** `AGORA_APP_CERTIFICATE` lives only in `server/.env.local` and never crosses a wire (used only in-memory to mint tokens). It is never sent to the browser.
- `CUSTOM_LLM_API_KEY` is stored in `server/.env.local` and passed to `CustomLLM`; Agora cloud forwards it as `Authorization: Bearer`.
- The browser receives a short-lived Token007 (3600s), never the certificate or API keys.
- `server/.env.local` is gitignored; `server/.env.example` ships placeholders only.

## CORS

The backend sets `CORSMiddleware` with `allow_origins=["*"]` — open by design for a local/dev recipe. The `llm.app` (mounted at `/audio`) also sets `allow_origins=["*"]`. **Lock both down to known origins before any production deployment.**

## Unauthenticated token endpoints (deployment concern)

Because Agora cloud must reach `/audio` publicly, the entire backend is public. `/get_config`, `/startAgent`, and `/stopAgent` have **no auth** in this recipe. Anyone with the backend URL can call them. Mitigations before production:

- Put an auth-checking reverse proxy or API gateway in front.
- Add rate limiting to prevent token/session abuse.
- Restrict allowed origins at the CORS layer.

## Validation

- `Agent.__init__` validates `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, and `CUSTOM_LLM_API_KEY` at boot — the server fails to start if any required var is missing.
- `Agent.start()` rejects empty `channel_name` and non-positive `agent_uid`/`user_uid` before issuing tokens or starting a session.
- Route errors are sanitized: `_log_route_error` logs only non-`None` context; exceptions map to 400/500 without leaking internals to the client.
- The mock audio endpoint does **not** validate the `Authorization: Bearer` header — a production endpoint should.

## Deployment notes

- Set `AGENT_BACKEND_URL` only to a backend you control.
- The published Docker image is **backend-only** (`:8000`); it does not bundle secrets.
- `CUSTOM_LLM_URL` is the public URL Agora cloud uses; ensure it points to your controlled endpoint.

## Related Deep Dives

- None.
