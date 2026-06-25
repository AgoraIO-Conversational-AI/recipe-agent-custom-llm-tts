# 03 · Code Map

> Where things live. Two top-level modules: `web/` (Next.js client) and `server/` (FastAPI backend). Orchestration is in the root `package.json`.

## Root

| Path                  | Responsibility                                                        |
| --------------------- | --------------------------------------------------------------------- |
| `package.json`        | Bun workspace; `setup`, `dev`, `doctor*`, `verify*`, `clean` scripts. |
| `README.md`           | Setup, run modes, env, troubleshooting.                               |
| `ARCHITECTURE.md`     | System shape and component boundaries.                                |
| `AGENTS.md`           | Coding-agent handbook + How to Load / Git Conventions / Doc Commands. |
| `Dockerfile`          | Backend-only image (`:8000`).                                         |
| `.github/workflows/`  | `ci.yml` (backend pytest matrix + web verify), `docker.yml`, `nightly.yml`. |

## `server/` — FastAPI backend (:8000)

| Path                              | Responsibility                                                              |
| --------------------------------- | --------------------------------------------------------------------------- |
| `src/server.py`                   | FastAPI app, CORS, route handlers, error mapping, mounts `llm.app` at `/audio`, uvicorn entrypoint. |
| `src/agent.py`                    | `Agent` class: `AsyncAgora` client, `CustomLLM`/`DeepgramSTT`/`MiniMaxTTS` vendors, `start()`/`stop()`, `_sessions`. |
| `src/llm.py`                      | Standalone FastAPI app (`llm.app`). OpenAI-compatible audio endpoint: `POST /chat/completions` + `GET /health`. No `agora_agent` import. |
| `scripts/run_fake_server.py`      | Boots `server.app` with a `FakeAgent` for the local FastAPI and LLM smoke tests. |
| `tests/test_agent_construction.py`| Builds the real `AgoraAgent`, fakes the SDK session, asserts start/stop shape. |
| `tests/test_llm_mount.py`         | Asserts the `/audio` mount, SSE contract (transcript + PCM chunks + `[DONE]`), and no-`agora_agent` import boundary. |
| `tests/conftest.py`               | `fake_env` fixture + `FakeAgent`; no cloud, no tunnel, no real creds.      |
| `.env.example`                    | Env template (do not add `PORT`).                                           |
| `requirements*.txt`               | Runtime + dev (pytest, httpx) deps.                                         |

## `server/src/server.py` routes

- `GET /get_config` — token + channel/UID config.
- `POST /startAgent` — start the agent session.
- `POST /stopAgent` — stop by `agent_id`.
- `POST /audio/chat/completions` — mounted from `llm.py`.
- `GET /audio/health` — mounted from `llm.py`.

## `web/` — Next.js client (:3000)

| Path                                      | Responsibility                                                     |
| ----------------------------------------- | ------------------------------------------------------------------ |
| `next.config.ts`                          | `/api/*` rewrites to `AGENT_BACKEND_URL`; strict mode; Turbopack root. |
| `src/services/api.ts`                     | Browser API client: `getConfig`, `startAgent`, `stopAgent`.        |
| `src/lib/conversation.ts`                 | Transcript normalization, timestamp/UID mapping, visualizer state. |
| `src/lib/agora.ts`                        | Agora RTC/RTM helpers.                                             |
| `src/components/LandingPage.tsx`          | Conversation entry: config fetch, agent start, RTM login, teardown.|
| `src/components/ConversationComponent.tsx`| RTC join, mic publish, transcript/metrics/state listeners.         |
| `src/components/Quickstart*.tsx`          | Pre-call, transcript, metrics, layout panels.                      |
| `scripts/verify-api-contracts.ts`         | Asserts rewrites + client paths + response envelope (no network).  |
| `scripts/verify-local-proxy.ts`           | Stub backend; proxies `/api/*` through the rewrite map.            |
| `scripts/verify-local-fastapi.ts`         | Spawns real FastAPI with `FakeAgent`; proxies agent routes end-to-end. |
| `scripts/verify-local-llm.ts`             | Spawns real FastAPI with `FakeAgent`; exercises `POST /audio/chat/completions` end-to-end. |
| `scripts/doctor.ts`                       | Web prerequisite check.                                            |

## Related Deep Dives

- None. For runtime flow see [02_architecture](02_architecture.md); for contracts see [06_interfaces](06_interfaces.md).
