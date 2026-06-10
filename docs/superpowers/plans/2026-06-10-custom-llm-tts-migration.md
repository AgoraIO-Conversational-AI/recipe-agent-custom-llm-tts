# Custom LLM-TTS Recipe Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the **custom-llm-tts** recipe in `recipe-agent-custom-llm-tts` by seeding from the finished `recipe-agent-custom-llm` template and swapping its text-LLM behavior for **audio-output** behavior (the custom endpoint returns PCM audio directly; no TTS).

**Architecture:** Same three-process shape as the template — `server/` (FastAPI agent backend :8000, `CustomLLM` vendor with `output_modalities=["audio"]`, no TTS), `llm/` (FastAPI audio endpoint :8001 serving `POST /audio/chat/completions`), `web/` (shared Next.js frontend). Most files are copied verbatim from the template; only the audio-specific files change.

**Tech Stack:** Python 3.8+, FastAPI, uvicorn, `agora-agents>=2.0.0` (`CustomLLM`); Next.js/React/TypeScript; Bun; ngrok for the public endpoint.

**Spec:** `docs/superpowers/specs/2026-06-10-custom-llm-tts-migration-design.md`
**Audio contract reference:** Agora ConvoAI [Audio Modality guide](https://doc.shengwang.cn/doc/convoai/restful/user-guides/audio-modality).

**Paths:**
- New repo (work here): `/Users/zhangqianze/Documents/recipe-agent-custom-llm-tts` — referred to as `$NEW`.
- Template (seed source): `/Users/zhangqianze/Documents/agent-recipes-python` — the `recipe-agent-custom-llm` clone, on branch `feat/custom-llm-refactor` — referred to as `$TPL`.

---

## Conventions

- Conventional Commits, lowercase after prefix, present tense, **no AI attribution / no `Co-Authored-By`**, no `--no-verify`.
- All work happens in `$NEW` on branch `feat/custom-llm-tts` (already created; the spec + `CONTEXT.md` are already committed there).
- "Tests" are the `verify:*` scripts + `py_compile`. Run them as written and confirm the stated output before committing.
- Under a global loopback proxy (e.g. Clash), prefix verify commands with `NO_PROXY=127.0.0.1,localhost,::1 no_proxy=127.0.0.1,localhost,::1` so localhost smoke tests bypass the proxy.

---

## Task 0: Confirm branch and seed source

**Files:** none (checks only)

- [ ] **Step 1: Confirm you are in `$NEW` on the feature branch with the spec committed**

Run:
```bash
cd /Users/zhangqianze/Documents/recipe-agent-custom-llm-tts
git rev-parse --abbrev-ref HEAD
git log --oneline -2
ls docs/superpowers/specs/ CONTEXT.md
```
Expected: branch `feat/custom-llm-tts`; the two `docs:` commits for the spec + CONTEXT; `CONTEXT.md` present.

- [ ] **Step 2: Confirm the template seed source exists and is clean**

Run:
```bash
git -C /Users/zhangqianze/Documents/agent-recipes-python rev-parse --abbrev-ref HEAD
git -C /Users/zhangqianze/Documents/agent-recipes-python status --short
```
Expected: branch `feat/custom-llm-refactor`; clean (or only ignored files). If the template lives elsewhere, adjust `$TPL` in all later commands.

---

## Task 1: Seed the repo from the template

**Files:**
- Adds (from template): `server/`, `llm/`, `web/`, `package.json`, `bun.lock`, `.gitignore`, `README.md`, `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md` (and `LICENSE`, overwriting the existing identical MIT one)
- Untouched: the already-committed `docs/superpowers/**` and `CONTEXT.md` (not present in the template archive)

`git archive` extracts only **tracked** template files (no venvs, no `node_modules`, no `.env.local`, no `__pycache__`, no `docs/superpowers/`, no `CONTEXT.md` — those were removed from the template branch).

- [ ] **Step 1: Extract the template's tracked files into the new repo**

```bash
cd /Users/zhangqianze/Documents/recipe-agent-custom-llm-tts
git -C /Users/zhangqianze/Documents/agent-recipes-python archive feat/custom-llm-refactor | tar -x
```
Expected: no errors. `server/`, `llm/`, `web/`, root configs/docs now exist.

- [ ] **Step 2: Verify the seed landed and the spec/CONTEXT survived**

Run:
```bash
ls server/src llm/src web/scripts package.json README.md AGENTS.md
ls docs/superpowers/specs/ CONTEXT.md
test ! -e server/.env.local && test ! -e llm/.env.local && echo "no leaked .env.local (good)"
test ! -d server/venv && test ! -d node_modules && echo "no venvs/node_modules (good)"
```
Expected: all listed paths exist; the spec + CONTEXT are intact; no `.env.local`, no venvs/node_modules.

- [ ] **Step 3: Commit the seed (still pure custom-llm content at this point)**

```bash
git add -A
git commit -m "chore: seed from recipe-agent-custom-llm template"
```

---

## Task 2: `server/src/agent.py` — audio output (CustomLLM + output_modalities, no TTS)

**Files:**
- Modify: `server/src/agent.py`

- [ ] **Step 1: Update the module docstring**

Replace:
```python
"""
Agent — Custom LLM Recipe

High-level API for managing Agora Conversational AI Agents with a Custom LLM.

Instead of using the built-in OpenAI vendor, this recipe configures the agent
to use a custom LLM endpoint (your own proxy server) that is compatible with
the OpenAI Chat Completions API format.
"""
```
with:
```python
"""
Agent — Custom LLM-TTS Recipe

High-level API for managing Agora Conversational AI Agents whose LLM stage
returns AUDIO directly (output_modalities=["audio"]), bypassing TTS.

The agent uses the CustomLLM vendor pointed at your own OpenAI-compatible
audio endpoint (the llm/ server). Agora cloud calls that endpoint and plays
the returned PCM audio straight to the user over RTC — there is no TTS step.
"""
```

- [ ] **Step 2: Drop the `MiniMaxTTS` import**

Replace:
```python
from agora_agent.agentkit.vendors import CustomLLM, DeepgramSTT, MiniMaxTTS
```
with:
```python
from agora_agent.agentkit.vendors import CustomLLM, DeepgramSTT
```

- [ ] **Step 3: Replace the prompt constant**

Replace:
```python
CUSTOM_LLM_PROMPT = """You are a helpful AI assistant powered by a custom LLM integration \
with Agora's Conversational AI Engine.

You can answer questions, have conversations, and help users with various tasks. \
Keep most replies to one or two sentences unless the user explicitly asks for more detail.
"""
```
with:
```python
AUDIO_AGENT_PROMPT = """You are a helpful AI assistant that responds with audio. \
Keep responses brief and conversational."""
```

- [ ] **Step 4: Update the greeting default**

Replace:
```python
        self.greeting = os.getenv(
            "AGENT_GREETING",
            "Hi there! I'm your AI assistant powered by a custom LLM. How can I help?",
        )
```
with:
```python
        self.greeting = os.getenv(
            "AGENT_GREETING",
            "Hi there! I'm a custom audio agent.",
        )
```

- [ ] **Step 5: Update the model default**

Replace:
```python
        self.custom_llm_model = os.getenv("CUSTOM_LLM_MODEL", "mock-model")
```
with:
```python
        self.custom_llm_model = os.getenv("CUSTOM_LLM_MODEL", "audio-mock")
```

- [ ] **Step 6: Switch the LLM block to audio output and drop the TTS vendor**

Replace:
```python
        # ============================================================
        # KEY DIFFERENCE: Use the SDK's CustomLLM vendor
        # ============================================================
        # The base quickstart uses a managed `OpenAI(model="gpt-4o-mini")`.
        # This recipe instead points the LLM stage at our own OpenAI-compatible
        # endpoint (the llm/ server) via the purpose-built `CustomLLM` vendor.
        # CustomLLM stamps `vendor: "custom"` in the wire config and requires
        # both base_url and api_key. Your endpoint can then:
        # - Add custom preprocessing (RAG, context injection)
        # - Route to different models dynamically
        # - Add logging and analytics
        # - Implement custom tool calling
        # ============================================================
        llm = CustomLLM(
            base_url=self.custom_llm_url,
            api_key=self.custom_llm_api_key,
            model=self.custom_llm_model,
            greeting_message=self.greeting,
            failure_message="Please wait a moment.",
            max_history=15,
            max_tokens=1024,
            temperature=0.7,
            top_p=0.95,
        )

        # STT and TTS remain the same as the quickstart
        stt = DeepgramSTT(model="nova-3", language="en")
        tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")
```
with:
```python
        # ============================================================
        # KEY DIFFERENCE: CustomLLM with output_modalities=["audio"]
        # ============================================================
        # The base quickstart uses a managed text LLM + MiniMax TTS. This
        # recipe instead points the LLM stage at our own OpenAI-compatible
        # endpoint via CustomLLM AND sets output_modalities=["audio"], which
        # tells Agora cloud the endpoint returns audio directly. With pure
        # ["audio"] output, NO TTS module is configured — the PCM audio from
        # your endpoint plays straight to the user over RTC.
        # ============================================================
        llm = CustomLLM(
            base_url=self.custom_llm_url,
            api_key=self.custom_llm_api_key,
            model=self.custom_llm_model,
            output_modalities=["audio"],
            greeting_message=self.greeting,
            failure_message="Please wait a moment.",
            max_history=10,
        )

        # STT still transcribes the user's speech into text for the LLM.
        stt = DeepgramSTT(model="nova-3", language="en")
        # No TTS — audio comes directly from the LLM endpoint.
```

- [ ] **Step 7: Point `instructions` at the new prompt and drop `enable_tools`**

Replace:
```python
            instructions=CUSTOM_LLM_PROMPT,
```
with:
```python
            instructions=AUDIO_AGENT_PROMPT,
```

Then replace:
```python
            advanced_features={"enable_rtm": True, "enable_tools": True},
```
with:
```python
            advanced_features={"enable_rtm": True},
```

- [ ] **Step 8: Remove `.with_tts(tts)` from the builder chain**

Replace:
```python
        agora_agent = (
            agora_agent
            .with_stt(stt)
            .with_llm(llm)
            .with_tts(tts)
        )
```
with:
```python
        agora_agent = (
            agora_agent
            .with_stt(stt)
            .with_llm(llm)
        )
```

- [ ] **Step 9: Compile-check and confirm no TTS references remain**

Run:
```bash
python3 -m py_compile server/src/agent.py && echo COMPILE_OK
grep -n "MiniMaxTTS\|with_tts\|CUSTOM_LLM_PROMPT\|enable_tools" server/src/agent.py || echo "no stale refs (good)"
grep -n "output_modalities" server/src/agent.py
```
Expected: `COMPILE_OK`; "no stale refs (good)"; one `output_modalities=["audio"]` line.

- [ ] **Step 10: Commit**

```bash
git add server/src/agent.py
git commit -m "feat(server): return audio via CustomLLM(output_modalities=[audio]), drop TTS"
```

---

## Task 3: `server/src/server.py` — title and channel prefix

**Files:**
- Modify: `server/src/server.py`

- [ ] **Step 1: Update the FastAPI title**

Replace:
```python
    title="Agora Custom LLM Recipe Service",
```
with:
```python
    title="Agora Custom LLM-TTS Recipe Service",
```

- [ ] **Step 2: Update the channel prefix**

Replace:
```python
    return f"custom-llm-{int(time.time())}-{random.randint(1000, 9999)}"
```
with:
```python
    return f"custom-llm-tts-{int(time.time())}-{random.randint(1000, 9999)}"
```

- [ ] **Step 3: Compile-check and commit**

```bash
python3 -m py_compile server/src/server.py && echo COMPILE_OK
git add server/src/server.py
git commit -m "chore(server): retitle service and channel prefix for custom-llm-tts"
```

---

## Task 4: `llm/src/custom_llm_server.py` — rewrite as the audio endpoint

**Files:**
- Overwrite: `llm/src/custom_llm_server.py`

- [ ] **Step 1: Replace the file with the audio endpoint**

Overwrite `llm/src/custom_llm_server.py` with exactly:

```python
"""
Custom Audio LLM Server — Mock (custom-llm-tts recipe)

An OpenAI-compatible audio-modalities endpoint for Agora Conversational AI.
Instead of returning text (delta.content), this endpoint returns AUDIO
directly (delta.audio), bypassing TTS entirely.

Contract — POST /audio/chat/completions, streaming SSE:
  1. Transcript chunk:  choices[0].delta.audio = {"id": <id>, "transcript": <text>}
  2. Audio chunks:      choices[0].delta.audio = {"id": <id>, "data": <base64 PCM>}
  3. Terminates with:   data: [DONE]

Audio format: PCM16, 16 kHz, mono, 1280-byte (40 ms) chunks.

IMPORTANT: the transcript is NOT just for display. Agora cloud stores it as the
agent's conversation context; omitting `audio.transcript` means the agent will
not remember what it said.

This mock generates a sine-wave tone (pure stdlib). Replace the audio source
with your own model / TTS / pre-recorded clips, keeping the PCM format. A
production endpoint should also validate the `Authorization: Bearer` header
that Agora cloud forwards.
"""
import asyncio
import base64
import json
import logging
import math
import os
import struct
import uuid
from typing import Dict, List, Optional, Union

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load environment variables.
# override=False so an explicitly-exported value (e.g. CUSTOM_LLM_PORT injected by
# the verify:local:llm harness, or a process manager) takes precedence over a
# checked-in .env.local. In normal `dev` no port is exported, so .env.local wins.
_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_base_dir, ".env.local"), override=False)
load_dotenv(os.path.join(_base_dir, ".env"), override=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Custom Audio LLM Server (Mock)",
    description=(
        "OpenAI-compatible audio-modalities endpoint for Agora Conversational AI. "
        "Returns audio directly (delta.audio), bypassing TTS."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request models — match what Agora ConvoAI Engine sends for audio modalities
# =============================================================================

class TextContent(BaseModel):
    type: str = "text"
    text: str


class SystemMessage(BaseModel):
    role: str = "system"
    content: Union[str, List[str]]


class UserMessage(BaseModel):
    role: str = "user"
    content: Union[str, List[Union[TextContent, Dict]]]


class AssistantMessage(BaseModel):
    role: str = "assistant"
    content: Union[str, List[TextContent], None] = None
    audio: Optional[Dict[str, str]] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[Union[SystemMessage, UserMessage, AssistantMessage]]
    modalities: List[str] = ["text", "audio"]
    audio: Optional[Dict[str, str]] = None
    stream: bool = True
    stream_options: Optional[Dict] = None


# =============================================================================
# Mock audio generation — sine-wave tone (pure stdlib)
# =============================================================================
# Replace this with your real audio source. Keep PCM16 / 16 kHz / mono.
# =============================================================================

SAMPLE_RATE = 16000      # 16 kHz
BYTES_PER_SAMPLE = 2     # PCM16
CHUNK_DURATION_MS = 40   # 40 ms per chunk
CHUNK_SIZE = int(SAMPLE_RATE * BYTES_PER_SAMPLE * CHUNK_DURATION_MS / 1000)  # 1280 bytes

MOCK_TRANSCRIPT = "This is a mock audio response from the custom LLM-TTS endpoint."


def generate_tone(duration_seconds: float = 2.0, frequency: float = 440.0) -> bytes:
    """Generate a mono PCM16 sine-wave tone with a short fade in/out envelope."""
    num_samples = int(SAMPLE_RATE * duration_seconds)
    fade = SAMPLE_RATE * 0.05  # 50 ms fade
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        envelope = min(1.0, i / fade) * min(1.0, (num_samples - i) / fade)
        value = int(16000 * envelope * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack("<h", max(-32768, min(32767, value))))
    return b"".join(samples)


def split_into_chunks(audio: bytes) -> List[bytes]:
    """Split PCM audio into fixed-size streaming chunks."""
    return [audio[i:i + CHUNK_SIZE] for i in range(0, len(audio), CHUNK_SIZE)]


@app.post("/audio/chat/completions")
async def audio_chat_completions(
    request: ChatCompletionRequest,
    authorization: Optional[str] = Header(None, alias="Authorization"),
):
    """
    OpenAI-compatible audio-modalities endpoint that Agora cloud calls.
    Streams a transcript chunk followed by base64 PCM audio chunks.
    """
    logger.info(
        "Received audio request: model=%s, modalities=%s, messages=%d",
        request.model, request.modalities, len(request.messages),
    )

    if not request.stream:
        raise HTTPException(status_code=400, detail="Only streaming mode is supported. Set stream=true.")

    audio_id = uuid.uuid4().hex
    message_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    chunks = split_into_chunks(generate_tone())

    async def generate():
        # 1) Transcript chunk — REQUIRED: Agora cloud stores it as agent context.
        yield "data: " + json.dumps({
            "id": message_id,
            "choices": [{
                "index": 0,
                "delta": {"audio": {"id": audio_id, "transcript": MOCK_TRANSCRIPT}},
                "finish_reason": None,
            }],
        }) + "\n\n"

        # 2) Audio chunks — base64-encoded PCM, ~40 ms real-time pacing.
        for chunk in chunks:
            yield "data: " + json.dumps({
                "id": message_id,
                "choices": [{
                    "index": 0,
                    "delta": {"audio": {"id": audio_id, "data": base64.b64encode(chunk).decode("utf-8")}},
                    "finish_reason": None,
                }],
            }) + "\n\n"
            await asyncio.sleep(CHUNK_DURATION_MS / 1000)

        # 3) Done.
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "custom-llm-tts-mock"}


if __name__ == "__main__":
    port = int(os.getenv("CUSTOM_LLM_PORT", "8001"))
    logger.info("Starting Custom Audio LLM Server (Mock) on port %d", port)
    logger.info("Endpoint: http://0.0.0.0:%d/audio/chat/completions", port)
    uvicorn.run(app, host="0.0.0.0", port=port)
```

- [ ] **Step 2: Compile-check**

Run: `python3 -m py_compile llm/src/custom_llm_server.py && echo COMPILE_OK`
Expected: `COMPILE_OK`.

- [ ] **Step 3: Smoke the endpoint manually (no agora deps needed)**

Run:
```bash
cd /Users/zhangqianze/Documents/recipe-agent-custom-llm-tts
python3 -m venv /tmp/llmtts && /tmp/llmtts/bin/pip -q install fastapi uvicorn python-dotenv >/dev/null
CUSTOM_LLM_PORT=43185 /tmp/llmtts/bin/python llm/src/custom_llm_server.py >/tmp/audio.log 2>&1 &
P=$!; sleep 3
curl -s --noproxy '*' -X POST http://127.0.0.1:43185/audio/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"audio-mock","messages":[{"role":"user","content":"hi"}],"stream":true,"modalities":["text","audio"]}' \
  | head -c 300; echo
kill $P 2>/dev/null; rm -rf /tmp/llmtts
```
Expected: SSE output whose first line is a `data: {...}` chunk containing `"transcript"` inside `delta.audio`, followed by chunks containing `"data"`.

- [ ] **Step 4: Commit**

```bash
git add llm/src/custom_llm_server.py
git commit -m "feat(llm): serve /audio/chat/completions returning PCM audio (sine-wave mock)"
```

---

## Task 5: Backend env + READMEs for audio

**Files:**
- Modify: `server/.env.example`, `server/README.md`, `llm/README.md`
- Verify-only (already correct from seed): `llm/.env.example`, `llm/requirements.txt`, `server/requirements.txt`

- [ ] **Step 1: Update `server/.env.example`** — overwrite with:

```
AGORA_APP_ID=your_agora_app_id
AGORA_APP_CERTIFICATE=your_agora_app_certificate
AGENT_GREETING=Hi there! I'm a custom audio agent.
CUSTOM_LLM_URL=https://your-tunnel.ngrok-free.dev/audio/chat/completions
CUSTOM_LLM_API_KEY=any-key-here
CUSTOM_LLM_MODEL=audio-mock
```

- [ ] **Step 2: Overwrite `server/README.md`** with:

```markdown
# Agora Agent Backend — Custom LLM-TTS Recipe

FastAPI service that owns Agora token generation and agent session lifecycle for
the custom-llm-tts recipe (port 8000). It is the service the web client reaches
through the Next.js `/api/*` rewrite proxy.

## What's different from the base quickstart

The LLM stage uses `CustomLLM` with `output_modalities=["audio"]`, pointed at your
own endpoint (the `llm/` server). Agora cloud calls that endpoint and plays the
returned PCM audio directly over RTC — **there is no TTS stage**. STT (Deepgram)
still transcribes the user's speech into text for the LLM.

## Run

Use the repo-root `README.md` for the full local flow (`bun run dev`). To work on
this module directly:

```bash
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/server.py
```

## Environment

`server/.env.example` is the template. Required:

- `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE` — Agora project credentials.
- `CUSTOM_LLM_URL` — the **public** URL of your `llm/` endpoint, ending in
  `/audio/chat/completions`. Agora cloud calls it, so it cannot be `localhost`.
- `CUSTOM_LLM_API_KEY` — forwarded by Agora cloud as `Authorization: Bearer`.
  Required by the `CustomLLM` vendor.

Optional: `CUSTOM_LLM_MODEL` (default `audio-mock`), `AGENT_GREETING`, `PORT`
(default `8000`).

## API

- `GET /get_config` — token + channel/UID config
- `POST /startAgent` — start an agent session
- `POST /stopAgent` — stop an agent session

`bun run verify:local:fastapi` exercises these routes through the Next proxy with
a fake agent — no live Agora session required.
```

- [ ] **Step 3: Overwrite `llm/README.md`** with:

```markdown
# Custom Audio LLM Endpoint — Mock

An OpenAI-compatible `POST /audio/chat/completions` server (port 8001) that Agora
cloud calls during a conversation. Instead of text, it returns **audio directly**
(`delta.audio`), which Agora plays over RTC with **no TTS step**. This mock emits a
sine-wave tone so you can exercise the full pipeline with **no API key**.

It has no `agora-agents` dependency — a plain FastAPI app, the boundary you replace
with your own audio source.

## The contract

`POST /audio/chat/completions`, streaming SSE:

1. **Transcript chunk** — `choices[0].delta.audio = {"id": <id>, "transcript": <text>}`.
2. **Audio chunks** — `choices[0].delta.audio = {"id": <id>, "data": <base64 PCM>}`.
3. Terminate with `data: [DONE]`.

Audio format: **PCM16, 16 kHz, mono, 1280-byte (40 ms) chunks**. Non-streaming
requests are rejected with HTTP 400.

> **The transcript is functionally required, not cosmetic.** Agora cloud stores
> `audio.transcript` as the agent's conversation context; if you omit it, the agent
> will not remember what it said. (Word-level `words` timestamps are optional and not
> emitted by this mock.)

## Run

```bash
cd llm
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/custom_llm_server.py     # serves on CUSTOM_LLM_PORT (default 8001)
```

## Expose it publicly

Agora cloud — not the browser — calls this server, so it must be reachable from the
public internet:

```bash
ngrok http 8001
```

Then set `CUSTOM_LLM_URL=https://<tunnel>/audio/chat/completions` in `server/.env.local`.

## Auth

This mock does **not** authenticate. A production endpoint should validate the
`Authorization: Bearer <CUSTOM_LLM_API_KEY>` header Agora cloud forwards.

## Replace the mock

Replace `generate_tone()` in `src/custom_llm_server.py` with your real audio source
(a TTS engine, your own model, or pre-recorded PCM), keeping the PCM format and the
transcript chunk.
```

- [ ] **Step 4: Verify the seeded files are already correct (no change needed)**

Run:
```bash
cat llm/.env.example        # expect: CUSTOM_LLM_PORT=8001
cat llm/requirements.txt    # expect: fastapi / uvicorn / python-dotenv (no agora, no aiofiles)
grep agora-agents server/requirements.txt   # expect: agora-agents>=2.0.0
```
Expected: as noted. If `llm/requirements.txt` somehow lists `aiofiles` or `pydantic`, remove those lines (the audio mock needs only `fastapi`, `uvicorn`, `python-dotenv`).

- [ ] **Step 5: Commit**

```bash
git add server/.env.example server/README.md llm/README.md
git commit -m "docs(server,llm): audio-modality env + module READMEs"
```

---

## Task 6: `web/` branding + pipeline metrics

**Files:**
- Modify: `web/app/layout.tsx`, `web/src/components/QuickstartPreCallCard.tsx`, `web/src/components/QuickstartPipelineMetrics.tsx`

- [ ] **Step 1: Page title + description** (`web/app/layout.tsx`)

Replace:
```tsx
	title: "Custom LLM Recipe | Agora Conversational AI",
	description:
		"Recipe: Bring your own LLM to Agora Conversational AI Engine via a custom OpenAI-compatible proxy.",
```
with:
```tsx
	title: "Custom LLM-TTS Recipe | Agora Conversational AI",
	description:
		"Recipe: Bring your own audio-generating endpoint (LLM + TTS combined) to Agora Conversational AI Engine — your endpoint returns audio directly, bypassing TTS.",
```

- [ ] **Step 2: Pre-call card copy** (`web/src/components/QuickstartPreCallCard.tsx`)

Replace:
```tsx
			<h1 className="text-[28px] font-medium leading-[1.2] text-white">
				Custom LLM Recipe
			</h1>
			<p className="mt-[14px] text-sm font-medium leading-6 text-muted-foreground">
				Bring your own LLM to Agora&apos;s Conversational AI Engine via a custom
				OpenAI-compatible proxy server.
			</p>
```
with:
```tsx
			<h1 className="text-[28px] font-medium leading-[1.2] text-white">
				Custom LLM-TTS Recipe
			</h1>
			<p className="mt-[14px] text-sm font-medium leading-6 text-muted-foreground">
				Bring your own audio-generating endpoint to Agora&apos;s Conversational AI
				Engine. Your endpoint returns audio directly — no separate TTS step.
			</p>
```

- [ ] **Step 3: Drop the TTS row from the pipeline metrics** (`web/src/components/QuickstartPipelineMetrics.tsx`)

Replace:
```tsx
const PIPELINE = [
	{ key: "stt", label: "Deepgram STT", metricTypes: ["stt", "asr"] },
	{ key: "llm", label: "Custom LLM", metricTypes: ["llm", "mllm"] },
	{ key: "tts", label: "MiniMax TTS", metricTypes: ["tts"] },
] as const;
```
with:
```tsx
const PIPELINE = [
	{ key: "stt", label: "Deepgram STT", metricTypes: ["stt", "asr"] },
	{ key: "llm", label: "Custom LLM (audio)", metricTypes: ["llm", "mllm"] },
] as const;
```

- [ ] **Step 4: Commit**

```bash
git add web/app/layout.tsx web/src/components/QuickstartPreCallCard.tsx web/src/components/QuickstartPipelineMetrics.tsx
git commit -m "chore(web): custom-llm-tts branding and audio-only pipeline metrics"
```

---

## Task 7: `web/scripts/verify-local-llm.ts` — audio contract

**Files:**
- Modify: `web/scripts/verify-local-llm.ts`

The seeded harness targets the text `/chat/completions` contract. Retarget it to the audio endpoint and assertions.

- [ ] **Step 1: Point the request at the audio endpoint with audio modalities**

Replace:
```ts
    const response = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer any-key-here',
      },
      body: JSON.stringify({
        model: 'mock-model',
        messages: [{ role: 'user', content: 'Hello' }],
        stream: true,
      }),
    })

    assert(response.status === 200, 'POST /chat/completions should return 200 for a streaming request')
    assert(
      (response.headers.get('content-type') ?? '').includes('text/event-stream'),
      'POST /chat/completions should return a text/event-stream response',
    )

    const body = await response.text()
    assert(
      body.includes('"role": "assistant"') || body.includes('"role":"assistant"'),
      'SSE stream should open with an assistant role delta',
    )
    assert(
      body.includes('"finish_reason": "stop"') || body.includes('"finish_reason":"stop"'),
      'SSE stream should close the choice with finish_reason "stop"',
    )
    assert(
      body.trimEnd().endsWith('data: [DONE]'),
      'SSE stream should terminate with data: [DONE]',
    )

    const nonStream = await fetch(`${baseUrl}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'mock-model',
        messages: [{ role: 'user', content: 'Hi' }],
        stream: false,
      }),
    })
    assert(nonStream.status === 400, 'Non-streaming requests should be rejected with 400')

    console.log('Custom LLM endpoint contract check passed')
```
with:
```ts
    const response = await fetch(`${baseUrl}/audio/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer any-key-here',
      },
      body: JSON.stringify({
        model: 'audio-mock',
        messages: [{ role: 'user', content: 'Hello' }],
        stream: true,
        modalities: ['text', 'audio'],
      }),
    })

    assert(response.status === 200, 'POST /audio/chat/completions should return 200 for a streaming request')
    assert(
      (response.headers.get('content-type') ?? '').includes('text/event-stream'),
      'POST /audio/chat/completions should return a text/event-stream response',
    )

    const body = await response.text()
    assert(
      body.includes('"transcript"'),
      'SSE stream should include a delta.audio transcript chunk (required for agent context)',
    )
    assert(
      body.includes('"data"'),
      'SSE stream should include at least one delta.audio base64 PCM data chunk',
    )
    assert(
      body.trimEnd().endsWith('data: [DONE]'),
      'SSE stream should terminate with data: [DONE]',
    )

    const nonStream = await fetch(`${baseUrl}/audio/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'audio-mock',
        messages: [{ role: 'user', content: 'Hi' }],
        stream: false,
        modalities: ['text', 'audio'],
      }),
    })
    assert(nonStream.status === 400, 'Non-streaming requests should be rejected with 400')

    console.log('Custom audio LLM endpoint contract check passed')
```

- [ ] **Step 2: Confirm no stale `/chat/completions` (text) reference remains**

Run: `grep -n "chat/completions" web/scripts/verify-local-llm.ts`
Expected: every match is `/audio/chat/completions` (no bare `/chat/completions`).

- [ ] **Step 3: Commit**

```bash
git add web/scripts/verify-local-llm.ts
git commit -m "test(web): assert the audio /audio/chat/completions SSE contract"
```

---

## Task 8: `package.json` name + root docs

**Files:**
- Modify: `package.json`, `README.md`, `ARCHITECTURE.md`, `AGENTS.md`
- Unchanged from seed: `CLAUDE.md` (already points at `AGENTS.md`)

- [ ] **Step 1: Rename the workspace** (`package.json`)

Replace:
```json
  "name": "agora-conversational-ai-recipe-custom-llm",
```
with:
```json
  "name": "agora-conversational-ai-recipe-custom-llm-tts",
```

- [ ] **Step 2: Overwrite `README.md`** with:

````markdown
# Agora Conversational AI — Custom LLM-TTS Recipe (Python)

The **custom-llm-tts** recipe in the Agora Conversational AI recipes family. Your
endpoint returns **audio directly** — playing both the LLM and TTS roles — so Agora
plays it over RTC with **no separate TTS step**. STT (Deepgram) still transcribes the
user's speech for your endpoint.

This repo ships a **zero-key mock** that emits a sine-wave tone, so you can run the
full STT → custom audio endpoint → RTC pipeline immediately, then replace the mock.

## Prerequisites

- [Python 3.8+](https://www.python.org/)
- [Bun](https://bun.sh/)
- [ngrok](https://ngrok.com/) (or any tunnel to expose localhost)
- Agora App ID + App Certificate (the [Agora CLI](https://github.com/AgoraIO/cli) makes this easy)

## Run it

```bash
# 1. Install + create both Python venvs
bun run setup

# 2. Add Agora credentials (CLI), or edit server/.env.local by hand
agora login
agora project use <your-project>
agora project env write server/.env.local

# 3. Expose the custom audio endpoint publicly (Agora cloud calls it directly)
ngrok http 8001

# 4. Add the tunnel URL (note the /audio path) to server/.env.local
#    CUSTOM_LLM_URL=https://<your-tunnel>.ngrok-free.dev/audio/chat/completions

# 5. Run all three services
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) → **Start Conversation** → speak.
You'll hear the mock tone as the agent's reply.

## Architecture

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js  ──rewrite──▶  Agent backend  (server/, localhost:8000)
                          │  CustomLLM(output_modalities=["audio"])
                          ▼
                       Agora ConvoAI Cloud
                          │  POST <CUSTOM_LLM_URL>   (Authorization: Bearer)
                          ▼
                       Custom audio endpoint  (llm/, localhost:8001)
                          │  returns transcript + PCM audio (SSE)
                          ▲  public via ngrok tunnel
                       (no TTS — audio plays straight to RTC)
```

See [ARCHITECTURE.md](./ARCHITECTURE.md).

## Project structure

```
recipe-agent-custom-llm-tts/
├── server/   # Agent backend (:8000) — CustomLLM(output_modalities=["audio"]), no TTS
│   ├── src/{server.py, agent.py}
│   └── scripts/run_fake_server.py
├── llm/      # Custom audio endpoint (:8001) — POST /audio/chat/completions, no agora deps
│   └── src/custom_llm_server.py
├── web/      # Shared Next.js frontend (:3000)
└── package.json
```

## Environment variables

Backend env file: [`server/.env.example`](server/.env.example).

| Variable | Required | Default | Notes |
| --- | :---: | :---: | --- |
| `AGORA_APP_ID` | ✅ | — | Agora Console → Project → App ID |
| `AGORA_APP_CERTIFICATE` | ✅ | — | Agora Console → Project → App Certificate (server only) |
| `CUSTOM_LLM_URL` | ✅ | — | **Public** URL of your `llm/` endpoint, ending in `/audio/chat/completions`. Agora cloud calls it; cannot be `localhost`. |
| `CUSTOM_LLM_API_KEY` | ✅ | `any-key-here` | Forwarded by Agora cloud as `Authorization: Bearer`. Required by the `CustomLLM` vendor. |
| `CUSTOM_LLM_MODEL` |  | `audio-mock` | Model name passed to your endpoint |
| `AGENT_GREETING` |  | built-in | Opening line (supported in audio mode via the messages protocol) |
| `PORT` |  | `8000` | Agent backend port |
| `CUSTOM_LLM_PORT` |  | `8001` | Port for the custom audio endpoint — lives in **`llm/.env.local`** |
| `AGENT_BACKEND_URL` (web deploy) | ✅ | — | Required in a deployed `web` app when proxying to the backend |

## Commands

```bash
bun run setup            # install web deps + create server/ and llm/ venvs
bun run dev              # run llm (:8001) + backend (:8000) + web (:3000)

bun run doctor           # prerequisite check (no creds needed)
bun run doctor:local     # + .env.local + credentials + CUSTOM_LLM_URL checks

bun run verify           # web-only gate (no Agora creds needed)
bun run verify:local     # full local gate: backend compile + smoke tests + web build
bun run clean            # remove venvs and build artifacts
```

## Replacing the mock

Replace `generate_tone()` in [`llm/src/custom_llm_server.py`](llm/src/custom_llm_server.py)
with your real audio source. Keep the SSE contract (transcript chunk + base64 PCM16/16kHz
chunks + `[DONE]`) — the transcript is required for agent context. See [`llm/README.md`](llm/README.md).

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Agent joins but no audio / garbled audio | `CUSTOM_LLM_URL` must be public and end in `/audio/chat/completions`; audio must be PCM16/16kHz/mono. |
| Agent doesn't remember context | Your endpoint must include `audio.transcript` in the first chunk. |
| `doctor:local` warns about localhost | Replace the local URL with your public tunnel URL. |
| Local calls fail under a global proxy (Clash, etc.) | Route `127.0.0.1`/`localhost`/RFC-1918 DIRECT in your proxy (don't disable it). |
| `Missing llm/venv` during verify | Run `bun run setup`. |

## License

MIT
````

- [ ] **Step 3: Overwrite `ARCHITECTURE.md`** with:

```markdown
# Architecture — Custom LLM-TTS Recipe

Three processes. The browser talks only to Next.js `/api/*`, which rewrites to the
agent backend. The agent backend owns Agora tokens and agent lifecycle. The custom
audio endpoint is a separate service that **Agora cloud** calls directly.

## Request flow

```
Browser
  │  GET /api/get_config            → token + channel/UIDs
  │  POST /api/startAgent           → start agent session
  ▼
Next.js  (rewrites /api/* → AGENT_BACKEND_URL)
  ▼
Agent backend (server/, :8000)
  │  CustomLLM(base_url=CUSTOM_LLM_URL, output_modalities=["audio"])
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT (managed) → text
  │  POST <CUSTOM_LLM_URL>/audio/chat/completions   (Authorization: Bearer)
  ▼
Custom audio endpoint (llm/, :8001, public via tunnel)
  │  returns transcript + base64 PCM audio (SSE)
  ▼
Agora ConvoAI Cloud streams that audio to RTC directly — NO TTS
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## Why audio output (no TTS)

`output_modalities=["audio"]` tells Agora cloud the LLM stage returns audio, so no
TTS module is configured — your endpoint's PCM plays straight to RTC. The transcript
in each response (`audio.transcript`) is stored as the agent's conversation context.

## Why two backends

`server/` and `llm/` are split because of an **exposure asymmetry**: `llm/` must be
reachable by Agora cloud over the **public internet** (hence the tunnel); `server/`
only needs to be reachable by the web tier and holds the App Certificate + token
logic. In production they may be co-deployed; kept separate here to make the boundary
explicit.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.
- Agora cloud → custom audio endpoint: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`
  (the mock does not validate it; a production endpoint should).
```

- [ ] **Step 4: Overwrite `AGENTS.md`** with:

```markdown
# Agent Development Guide

For coding agents working in `recipe-agent-custom-llm-tts`. This repository is the
**custom-llm-tts** recipe (`Recipe Role: custom-llm-tts`) in the Agora Conversational
AI recipes family, derived from the base `agent-quickstart-python` template via the
`recipe-agent-custom-llm` recipe.

## System shape

- **`server/`** — Python FastAPI agent backend (:8000). Owns Agora token generation
  and agent lifecycle. Uses `CustomLLM(output_modalities=["audio"])` and **no TTS**.
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

- The endpoint returns **audio** (`delta.audio.data`, base64 PCM16/16kHz/mono); there
  is no TTS stage (`output_modalities=["audio"]`).
- The **transcript** (`delta.audio.transcript`) is required — it is stored as agent
  context; omitting it loses conversation memory.
- `CUSTOM_LLM_URL` is required, must be public, and ends in `/audio/chat/completions`
  (no localhost default). `CUSTOM_LLM_API_KEY` is required by `CustomLLM`.
- Keep the `llm/` endpoint free of `agora-agents`.

## Anti-patterns

- Do not add a TTS vendor or `.with_tts()` — audio comes from the endpoint.
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
```

- [ ] **Step 5: Validate, confirm no doc references the absent `docs/ai/`, commit**

```bash
node -e "JSON.parse(require('fs').readFileSync('package.json','utf8')); console.log('package.json OK')"
grep -rn "docs/ai" README.md ARCHITECTURE.md AGENTS.md CLAUDE.md && echo "FOUND docs/ai (fix it)" || echo "no docs/ai links (good)"
git add package.json README.md ARCHITECTURE.md AGENTS.md
git commit -m "docs: rename workspace and rewrite root docs for custom-llm-tts"
```
Expected: `package.json OK`; "no docs/ai links (good)".

---

## Task 9: Full setup + verification gate

**Files:** none (runs the suite). Fix failures in the relevant file before committing.

- [ ] **Step 1: Install everything**

Run: `cd /Users/zhangqianze/Documents/recipe-agent-custom-llm-tts && bun run setup`
Expected: web deps install; `server/venv` + `llm/venv` created and deps installed; "Setup complete" message.

- [ ] **Step 2: Provide local credentials for the local gate**

`doctor:local` + smoke tests need `server/.env.local` and `llm/.env.local` (created by `setup` from the examples, which carry non-empty placeholders incl. a non-localhost `CUSTOM_LLM_URL`). With real creds, instead run `agora project use <project> && agora project env write server/.env.local` and add the `CUSTOM_LLM_*` lines.

- [ ] **Step 3: Backend compile check**

Run: `bun run verify:backend`
Expected: exit 0 (compiles `server/src/server.py`, `server/src/agent.py`, `llm/src/custom_llm_server.py`).

- [ ] **Step 4: Audio contract check**

Run: `NO_PROXY=127.0.0.1,localhost,::1 no_proxy=127.0.0.1,localhost,::1 bun run verify:local:llm`
Expected: `Custom audio LLM endpoint contract check passed`.

- [ ] **Step 5: FastAPI route smoke + web checks**

Run:
```bash
export NO_PROXY=127.0.0.1,localhost,::1 no_proxy=127.0.0.1,localhost,::1
bun run verify:local:fastapi
bun run verify:web:api && bun run verify:web:proxy
```
Expected: `Local FastAPI app proxy smoke check passed`; the web checks print their pass messages.

- [ ] **Step 6: Full local gate**

Run: `NO_PROXY=127.0.0.1,localhost,::1 no_proxy=127.0.0.1,localhost,::1 bun run verify:local`
Expected: doctor:local (all checks), backend compile, both smoke checks, web proxy, and the Next build all succeed.

> If a build error mentions a stray `tts` symbol in `QuickstartPipelineMetrics`, confirm Step 3 of Task 6 removed the `tts` row cleanly.

- [ ] **Step 7: Commit any fixes**

```bash
git add -A
git commit -m "chore: pass full local verification gate" || echo "nothing to commit"
```

---

## Task 10: PR to main

**Files:** none (git only)

- [ ] **Step 1: Push the branch**

```bash
cd /Users/zhangqianze/Documents/recipe-agent-custom-llm-tts
git push -u origin feat/custom-llm-tts
```

- [ ] **Step 2: Open the PR** (REST API — the GraphQL `gh pr create` path may 401 under a lapsed SSO session; REST works)

```bash
REPO=AgoraIO-Conversational-AI/recipe-agent-custom-llm-tts
gh api -X POST "repos/$REPO/pulls" \
  -f title="feat: custom-llm-tts recipe (audio-output, migrated from audio-modalities)" \
  -f head="feat/custom-llm-tts" \
  -f base="main" \
  -f body="Seeds from the recipe-agent-custom-llm template and swaps text→audio: CustomLLM(output_modalities=[\"audio\"]) with no TTS, an /audio/chat/completions endpoint returning PCM audio (sine-wave mock), audio-contract verify harness, and retargeted docs. Verified with bun run verify:local." \
  --jq '{number, url: .html_url, state}'
```
Expected: a JSON object with the new PR number + URL.

---

## Self-Review notes (for the implementer)

- The "tests" are `verify:*` + `py_compile`; the new audio logic is covered by `verify:local:llm` (boots the real audio mock, asserts the SSE audio contract) and `verify:local:fastapi` (route wiring).
- `docs/superpowers/**` and `CONTEXT.md` are committed already; the seed (Task 1) does not touch them because they aren't in the template archive.
- If `git archive | tar -x` is unavailable, substitute: `rsync -a --exclude .git --exclude 'venv' --exclude node_modules --exclude .next --exclude dist --exclude '*.env.local' --exclude __pycache__ --exclude .agora $TPL/ .` — but `git archive` is preferred (tracked files only).
```