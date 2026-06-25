# Progressive Disclosure — Test Results

> Test run for `recipe-agent-custom-llm-tts` progressive disclosure docs.
> Date: 2026-06-25 · Standard: AgoraIO-Community/ai-devkit progressive-disclosure.

## Step 1 — Structural checks

| Check                                              | Result |
| -------------------------------------------------- | ------ |
| `L0_repo_card.md` ≤ 50 lines                       | Pass (36) |
| All 8 L1 files present                             | Pass |
| Each L1 has purpose blockquote + Related Deep Dives| Pass (8/8) |
| L1 line counts in 80–200 target                    | **Partial** (48–91) — see note |
| L2 `_index.md` present                             | Pass |
| Each L2 deep dive opens with "When to Read This" callout | Pass (3/3) |
| Relative links resolve (`docs/ai/` + AGENTS.md)    | Pass (51/51, 0 broken) |
| AGENTS.md has How to Load / Git Conventions / Doc Commands | Pass |

**Note on L1 line counts:** Files are table-dense and information-complete, running
48–91 lines. The standard favors tables over prose and warns against bloat, so files
were left concise rather than padded. `01_setup.md` (83) and `06_interfaces.md` (91)
are within target; others are slightly below at 48–74. Accepted deviation; revisit if
a section needs more depth.

## Step 2 — Backend tests

```
cd server && pytest tests -q
5 passed, 1 warning in 2.81s
```

Tests run in a throwaway venv (`python3 -m venv /tmp/v_custom_llm_tts`). No cloud,
no tunnel, no real credentials required. Venv deleted after run.

## Step 3 — Question runs

Questions span the five standard categories. Each answer was checked against the
repo source before being marked Pass. "Level" is the lowest disclosure level
that fully answers the question.

### Setup & Build

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 1 | How do I install and run it locally? | `bun run setup`, expose backend via ngrok, set `CUSTOM_LLM_URL`, then `bun run dev`. | `L1/01_setup.md` ↔ `README.md`, `package.json` | L1 | Pass |
| 2 | Which env vars are required? | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, `CUSTOM_LLM_API_KEY`. | `L1/01_setup.md`, `06_interfaces.md` ↔ `agent.py`, `.env.example` | L1 | Pass |
| 3 | Why does `CUSTOM_LLM_URL` have no localhost default? | Agora cloud (not the local backend) calls it; a localhost URL silently fails cloud-side. | `L1/07_gotchas.md` ↔ `agent.py`, `README.md` | L1 | Pass |

### Test & Run

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 4 | How do I run backend tests without cloud creds? | `cd server && pytest tests -v`; `conftest.py` fakes env + SDK session + neutralizes dotenv. | `L1/04_conventions.md`, `01_setup.md` ↔ `tests/conftest.py` | L1 | Pass (ran: 5 passed) |
| 5 | What's the narrowest gate for a web-only change? | `bun run verify:web`. | `L1/05_workflows.md` ↔ `package.json` | L1 | Pass |
| 6 | What does `verify:local:llm` do? | Spawns real FastAPI with `FakeAgent`, calls `POST /audio/chat/completions`, asserts SSE contract (transcript + PCM + `[DONE]`) and rejects non-streaming. | `L1/03_code_map.md`, `05_workflows.md` ↔ `web/scripts/verify-local-llm.ts` | L1 | Pass |

### Conventions

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 7 | What response shape do backend routes use? | `{ code, msg, data }`; `data` only when there's a payload. | `L1/04_conventions.md`, `06_interfaces.md` ↔ `server.py` | L1 | Pass |
| 8 | Why must `llm.py` not import `agora_agent`? | It is the provider-agnostic component developers replace; `test_llm_mount.py` enforces the boundary via AST. | `L1/04_conventions.md` ↔ `tests/test_llm_mount.py` | L1 | Pass |
| 9 | What are the commit/branch conventions? | Conventional commits `type: description`; branches `type/short-description`; no AI tool names; no Co-Authored-By. | `AGENTS.md` Git Conventions | L0/AGENTS | Pass |

### Development

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 10 | How do I replace the mock with a real model? | Replace `generate_tone()` in `llm.py`; keep SSE contract (transcript chunk → PCM chunks → `[DONE]`); keep `llm.py` free of `agora_agent`; run `pytest tests`. | `L1/05_workflows.md` ↔ `server/src/llm.py`, `README.md` | L1 | Pass |
| 11 | Where is the `/api/*` boundary defined and what must I not add? | Rewrites in `web/next.config.ts`; never add `app/api/**/route.ts` for agent/token logic. | `L1/04_conventions.md`, `07_gotchas.md` ↔ `next.config.ts`, `verify-api-contracts.ts` | L1 | Pass |
| 12 | Why does `agent.py` still call `.with_tts()` if TTS is never used? | The agora-agents builder requires a TTS in cascading mode (both 1.4 and 2.0) even when `output_modalities=["audio"]` means the TTS is never invoked. | `L1/07_gotchas.md` ↔ `agent.py`, `ARCHITECTURE.md` | L1 | Pass |

### Deep Dive

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 13 | What is the exact SSE format the audio endpoint must return? | 1) transcript chunk (`delta.audio.transcript`), 2) base64 PCM16/16kHz/mono chunks (`delta.audio.data`), 3) `data: [DONE]`. | `L2/audio_endpoint_contract.md` ↔ `llm.py`, `test_llm_mount.py` | L2 | Pass |
| 14 | How is VAD configured and where does it differ from the realtime recipe? | VAD is set on `AgoraAgent` directly (cascading mode) with `start_of_speech`/`end_of_speech` VAD dicts; not vendor-owned as in the realtime MLLM recipe. | `L2/custom_llm_config.md` ↔ `agent.py` | L2 | Pass |
| 15 | How does stop survive a backend restart? | `_sessions` is in-memory; missing session falls back to `client.stop_agent(agent_id)`. | `L2/session_lifecycle.md` ↔ `agent.py` | L2 | Pass |

## Step 4 — Analysis

- All 15 questions answered at the expected disclosure level (12 at L1, 3 at L2).
  No "correct but needed L2 unnecessarily" or "wrong/missing L2" cases.
- No missing-coverage findings; no broken references (51 checked, 0 broken).
- One soft deviation: L1 line counts below the 80–200 target for 6 of 8 files
  (accepted; concise/table-dense).

## Step 5 — Summary

| Category       | Questions | Pass | Notes |
| -------------- | :-------: | :--: | ----- |
| Setup & Build  | 3 | 3 | — |
| Test & Run     | 3 | 3 | backend tests executed: 5 passed |
| Conventions    | 3 | 3 | — |
| Development    | 3 | 3 | — |
| Deep Dive      | 3 | 3 | resolved at L2 as designed |
| **Total**      | **15** | **15** | — |

## Step 6 — Fixes / Retest

No failing questions; no fixes required. Evidence executed during this run:

- `pytest tests -q` → `5 passed`.
- Relative link check → `51 checked, 0 broken`.
