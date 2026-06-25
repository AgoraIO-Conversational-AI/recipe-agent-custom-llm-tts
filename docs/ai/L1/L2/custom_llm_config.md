# Deep Dive — Custom LLM Config

> **When to Read This:** You are changing the `CustomLLM` vendor, STT settings, VAD configuration, session parameters, or the inert TTS vendor. For the high-level picture, start at [02_architecture](../02_architecture.md).

This recipe uses a cascading STT → CustomLLM pipeline. The custom LLM endpoint returns audio directly — no TTS synthesis occurs at runtime. All three vendors (`DeepgramSTT`, `CustomLLM`, `MiniMaxTTS`) are assembled in `Agent.start()` in `server/src/agent.py`.

## The vendor chain

```python
llm = CustomLLM(
    base_url=self.custom_llm_url,       # CUSTOM_LLM_URL (public URL)
    api_key=self.custom_llm_api_key,    # CUSTOM_LLM_API_KEY
    model=self.custom_llm_model,        # CUSTOM_LLM_MODEL, default "audio-mock"
    output_modalities=["audio"],        # tells Agora: endpoint returns audio, skip TTS
    greeting_message=self.greeting,
    failure_message="Please wait a moment.",
    max_history=10,
)

stt = DeepgramSTT(model="nova-3", language="en")

# Inert — required by the agora-agents builder in cascading mode,
# but never invoked because output_modalities=["audio"].
tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")

agora_agent = (
    AgoraAgent(...)
    .with_stt(stt)
    .with_llm(llm)
    .with_tts(tts)
)
```

## Why `output_modalities=["audio"]`

When `output_modalities=["audio"]`, Agora ConvoAI cloud knows the custom endpoint returns raw PCM audio. It skips the TTS step and streams the audio directly to the RTC channel. The inert `MiniMaxTTS` vendor has nothing to synthesize and is never called.

## Why `.with_tts()` must stay

The agora-agents builder (both 1.4 and 2.0) requires `.with_tts()` in cascading mode — it raises "TTS configuration is required" without it. The TTS vendor is safe to configure with any voice/model because it is never invoked. Do not remove it.

## VAD (turn detection)

Turn detection is configured on `AgoraAgent` directly (cascading mode, not vendor-owned):

```python
turn_detection={
    "config": {
        "speech_threshold": 0.5,
        "start_of_speech": {
            "mode": "vad",
            "vad_config": {
                "interrupt_duration_ms": 160,
                "prefix_padding_ms": 300,
            },
        },
        "end_of_speech": {
            "mode": "vad",
            "vad_config": {
                "silence_duration_ms": 480,
            },
        },
    },
},
```

Adjust these values to change how aggressively the agent interrupts or waits for silence.

## Session `parameters`

Passed to `AgoraAgent` and forwarded to the Agora cloud:

| Key                    | Value    | Why                                              |
| ---------------------- | -------- | ------------------------------------------------ |
| `audio_scenario`       | `chorus` | Ultra-low-latency profile for web clients.       |
| `data_channel`         | `rtm`    | Transcript + metrics delivered over RTM.         |
| `enable_error_message` | `true`   | Surface agent-side errors to the client.         |
| `enable_metrics`       | `true`   | Emit pipeline metrics to the UI.                 |
| `output_audio_codec`   | optional | Forwarded from `POST /startAgent` `parameters`.  |

## Session creation

```python
session = agora_agent.create_async_session(
    channel=channel_name,
    agent_uid=str(agent_uid),
    remote_uids=[str(user_uid)],
    enable_string_uid=False,
    idle_timeout=30,
    expires_in=3600,
)
agent_id = await session.start()   # stored in self._sessions[agent_id]
```

## `CustomLLM` `max_history`

`max_history=10` on `CustomLLM` limits the conversation history sent to the custom endpoint. `AgoraAgent` itself uses `max_history=50` (the agent context). These are independent settings.

## Related L1

- [02_architecture](../02_architecture.md) · [06_interfaces](../06_interfaces.md) · [07_gotchas](../07_gotchas.md)
