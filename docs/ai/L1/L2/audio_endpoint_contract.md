# Deep Dive — Audio Endpoint Contract

> **When to Read This:** You are replacing the mock audio endpoint with a real model, debugging audio or context issues, or changing the SSE output format. For the high-level wiring, see [02_architecture](../02_architecture.md).

The custom audio endpoint (`server/src/llm.py`) is the component you replace with your own model. It is mounted at `/audio` in the FastAPI server, making its public path `POST /audio/chat/completions`. Agora cloud calls it directly.

## Route

```
POST /audio/chat/completions   (mounted at /audio; server.py: app.mount("/audio", llm_app))
GET  /audio/health
```

## Request format

Agora cloud sends an OpenAI-compatible body:

```json
{
  "model": "audio-mock",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user",  "content": "..."},
    {"role": "assistant", "audio": {"id": "...", "transcript": "..."}},
    ...
  ],
  "modalities": ["text", "audio"],
  "stream": true
}
```

- `stream` is always `true` (Agora cloud only calls in streaming mode). Return 400 if `stream=false`.
- `Authorization: Bearer <CUSTOM_LLM_API_KEY>` header is forwarded. The mock does not validate it; a production endpoint should.

## SSE response format

Three-phase SSE stream:

```
data: {"id":"chatcmpl-<id>","choices":[{"index":0,"delta":{"audio":{"id":"<audio_id>","transcript":"<text>"}},"finish_reason":null}]}

data: {"id":"chatcmpl-<id>","choices":[{"index":0,"delta":{"audio":{"id":"<audio_id>","data":"<base64_pcm>"}},"finish_reason":null}]}
... (more audio chunks)

data: [DONE]
```

| Phase | Field             | Required | Description                                         |
| ----- | ----------------- | :------: | --------------------------------------------------- |
| 1     | `delta.audio.transcript` | ✅ | Text of the response. Agora stores it as agent context. |
| 2     | `delta.audio.data`       | ✅ | Base64-encoded PCM16 audio chunks.                  |
| 3     | `[DONE]` sentinel        | ✅ | Terminates the SSE stream.                          |

## Audio format

| Attribute    | Value    |
| ------------ | -------- |
| Encoding     | PCM16 (signed 16-bit little-endian) |
| Sample rate  | 16,000 Hz |
| Channels     | Mono (1 channel) |
| Chunk size   | 1,280 bytes (~40 ms) |

Wrong encoding or sample rate causes garbled or silent audio. The chunk size is recommended but not strictly enforced.

## Why the transcript is required

Agora cloud stores `audio.transcript` as the agent's conversation history. Without it:

- The assistant's previous turns appear empty in the messages sent to subsequent requests.
- The agent has no memory of what it said; context is lost after one turn.

Always include the transcript even if you generate it from TTS metadata or approximate it.

## Replacing the mock

1. Find `generate_tone()` in `server/src/llm.py` — this is the only function to replace for a basic swap.
2. Produce your audio as `bytes` (PCM16, 16 kHz, mono).
3. Use `split_into_chunks()` (or your own chunker) to split into ~1280-byte pieces.
4. Stream: transcript chunk first, then audio chunks, then `data: [DONE]`.
5. Keep `llm.py` free of `agora_agent` imports.
6. Run `cd server && pytest tests -v` to verify the SSE contract + import boundary.

## Import boundary

`llm.py` must **not** import `agora_agent` or any `agora_*` package. `test_llm_mount.py` checks this via Python AST inspection. Docstrings or string literals mentioning "agora" are fine; import statements are not.

## Health check

`GET /audio/health` is used by `verify:local:llm` to confirm the backend started before running SSE assertions.

## Related L1

- [02_architecture](../02_architecture.md) · [06_interfaces](../06_interfaces.md) · [07_gotchas](../07_gotchas.md)
