# recipe-agent-custom-llm-tts — Repo Card

> Next.js web client + Python FastAPI backend for an Agora Conversational AI voice agent using a cascading STT → Custom LLM (audio output) pipeline. The custom LLM endpoint returns PCM audio directly, bypassing TTS. A zero-key sine-wave mock is included for immediate local testing.

## Identity

| Field          | Value                                                                            |
| -------------- | -------------------------------------------------------------------------------- |
| Repo           | `AgoraIO-Conversational-AI/recipe-agent-custom-llm-tts`                          |
| Type           | `distributed-system` (single repo, two co-located processes)                    |
| Language       | Python 3.10+ (FastAPI + uvicorn) backend + Next.js 16 / React 19 web            |
| Deploy Target  | `web/` as Next.js app, `server/` as a reachable FastAPI service (must be public) |
| Owner          | Agora Conversational AI DevEx                                                    |
| Last Reviewed  | 2026-06-25                                                                       |
| Recipe Role    | `base`                                                                           |
| Recipe Version | `1.0.0`                                                                          |
| Recipe Status  | `experimental`                                                                   |

## L1 — Summaries

The Audience column helps agents prioritise: **Use** = consuming the recipe's behavior, **Maintain** = modifying internals.

| File                                     | Purpose                                                                                      | Audience       |
| ---------------------------------------- | -------------------------------------------------------------------------------------------- | -------------- |
| [01_setup](L1/01_setup.md)               | bun + venv + pip setup, env vars (incl. tunnel requirement), commands                        | Use & Maintain |
| [02_architecture](L1/02_architecture.md) | Two-process topology, single-backend dual-concern, cascading STT→CustomLLM request lifecycle | Maintain       |
| [03_code_map](L1/03_code_map.md)         | `web/` and `server/` trees with key file responsibilities                                    | Maintain       |
| [04_conventions](L1/04_conventions.md)   | Python async + FastAPI patterns, Biome, JSON envelope, import boundary                       | Maintain       |
| [05_workflows](L1/05_workflows.md)       | Replace mock, add a route, change LLM config, verify, deploy                                 | Use            |
| [06_interfaces](L1/06_interfaces.md)     | FastAPI route contracts, rewrites, env vars, audio endpoint SSE contract                     | Use & Maintain |
| [07_gotchas](L1/07_gotchas.md)           | Tunnel requirement, inert TTS, transcript required, PORT in env, localhost CUSTOM_LLM_URL    | Maintain       |
| [08_security](L1/08_security.md)         | Token007, App Certificate server-only, unauthenticated token endpoints, CORS, Bearer         | Maintain       |

## Recipe Profile

This repo declares `Recipe Role: base`. See [RECIPE.md](RECIPE.md) for extension points, invariants, and stable contracts before changing reusable surfaces.
