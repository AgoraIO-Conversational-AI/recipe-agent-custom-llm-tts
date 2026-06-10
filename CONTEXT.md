# Context — recipe-agent-custom-llm-tts

A glossary of the domain language for this repository. Implementation details do not belong here.

## Terms

### Custom LLM-TTS recipe
The recipe in this repository. A custom endpoint that returns **audio directly**,
playing both the LLM and TTS roles. Derived from the base Agora Conversational AI
quickstart and structured like the [[custom-llm-recipe]]; `Recipe Role: custom-llm-tts`.

### Audio modality (audio output)
The agent mode in which the LLM stage emits audio instead of text, set by
`output_modalities=["audio"]`. When pure audio, **no TTS module is configured** —
the audio from the custom endpoint plays directly over RTC.

### Custom audio endpoint
The FastAPI service in `llm/` (port 8001). An OpenAI-compatible
`POST /audio/chat/completions` server that Agora cloud calls. Returns SSE where
`delta.audio.data` is base64 PCM16/16 kHz/mono audio. Must be **publicly reachable**
(Agora cloud is the caller). This is the component a developer replaces.

### Transcript (audio context)
The `delta.audio.transcript` field in the endpoint's response. Beyond UI display,
it is **functionally required for conversation memory**: transcript content
automatically enters the agent's context, and its absence blocks context storage.
Distinct from `words` (optional word-level timestamps for caption alignment, not
used by this recipe).

### Greeting (audio modality)
A supported opening line in audio mode. It flows through the messages protocol: a
final `role: "assistant"` message in the request is converted to audio and played
directly. It does **not** require a TTS stage — so `AGENT_GREETING` remains a valid
knob in this recipe, unlike a naive assumption that "no TTS means no greeting".
