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
