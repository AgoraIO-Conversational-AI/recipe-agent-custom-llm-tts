# Deep Dives Index

| Document                                                    | Summary                                                                            | Load When                                                                      |
| ----------------------------------------------------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [custom_llm_config.md](custom_llm_config.md)                | Full `CustomLLM` vendor build, vendor chain (STT + inert TTS), VAD, and session options | Changing the vendor config, STT, TTS, VAD, codec, or session parameters   |
| [audio_endpoint_contract.md](audio_endpoint_contract.md)    | SSE format, PCM16 spec, transcript requirement, and mock replacement guide         | Replacing the mock, debugging audio issues, or changing the SSE output format  |
| [session_lifecycle.md](session_lifecycle.md)                | Browser orchestration of get_config + start/stop, RTC/RTM, transcript mapping     | Touching client-side join, token renewal, or mid-call control                  |
