"""
Agent — Custom LLM-TTS Recipe

High-level API for managing Agora Conversational AI Agents whose LLM stage
returns AUDIO directly (output_modalities=["audio"]), bypassing TTS.

The agent uses the CustomLLM vendor pointed at your own OpenAI-compatible
audio endpoint (the llm/ server). Agora cloud calls that endpoint and plays
the returned PCM audio straight to the user over RTC — there is no TTS step.
"""
import logging
import os
import time
from typing import Any, Dict, Optional

from agora_agent import Area, AsyncAgora
from agora_agent.agentkit import Agent as AgoraAgent
from agora_agent.agentkit.vendors import CustomLLM, DeepgramSTT, MiniMaxTTS

logger = logging.getLogger("uvicorn.error")

AUDIO_AGENT_PROMPT = """You are a helpful AI assistant that responds with audio. \
Keep responses brief and conversational."""


class Agent:
    """
    High-level wrapper for Agora Conversational AI Agent with audio output.

    The key difference from the quickstart is the LLM stage: this uses the
    CustomLLM vendor with `output_modalities=["audio"]`, pointed at your own
    OpenAI-compatible audio endpoint (the custom_llm_server.py mock). Agora
    cloud calls that endpoint and plays the returned PCM audio directly over
    RTC — there is no TTS step.

    IMPORTANT: The custom LLM URL must be publicly accessible for the Agora
    Conversational AI Engine (cloud) to reach it. For local development, use
    a tunnel (ngrok, Cloudflare Tunnel) or GitHub Codespaces with public ports.
    """

    def __init__(self):
        self.app_id = os.getenv("AGORA_APP_ID")
        self.app_certificate = os.getenv("AGORA_APP_CERTIFICATE")
        self.greeting = os.getenv(
            "AGENT_GREETING",
            "Hi there! I'm a custom audio agent.",
        )

        # Custom LLM configuration.
        # CUSTOM_LLM_URL is the FULL OpenAI-compatible chat-completions URL and must be
        # PUBLICLY reachable: Agora cloud (not this backend) calls it. For local dev,
        # expose the llm/ server on port 8001 via ngrok and paste that URL here.
        # There is intentionally no localhost default: a localhost URL would let the
        # agent "start" while its LLM calls silently fail cloud-side.
        self.custom_llm_url = os.getenv("CUSTOM_LLM_URL")
        self.custom_llm_api_key = os.getenv("CUSTOM_LLM_API_KEY", "any-key-here")
        self.custom_llm_model = os.getenv("CUSTOM_LLM_MODEL", "audio-mock")

        if not self.app_id or not self.app_certificate:
            raise ValueError("AGORA_APP_ID and AGORA_APP_CERTIFICATE are required")

        if not self.custom_llm_url:
            raise ValueError(
                "CUSTOM_LLM_URL is required (the public chat-completions URL of your "
                "custom LLM endpoint, e.g. https://<tunnel>/chat/completions)"
            )

        if not self.custom_llm_api_key:
            # CustomLLM rejects a missing api_key, and base_url is only valid with a key.
            raise ValueError(
                "CUSTOM_LLM_API_KEY is required when using a custom LLM endpoint"
            )

        self.client = AsyncAgora(
            area=Area.US,
            app_id=self.app_id,
            app_certificate=self.app_certificate,
        )

        # Track active sessions by agent_id
        self._sessions: Dict[str, Any] = {}

    async def start(
        self,
        channel_name: str,
        agent_uid: int,
        user_uid: int,
        output_audio_codec: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start agent with Custom LLM vendor chain."""
        if not channel_name or not str(channel_name).strip():
            raise ValueError("channel_name is required and cannot be empty")
        if agent_uid <= 0:
            raise ValueError("agent_uid is required and cannot be empty")
        if user_uid <= 0:
            raise ValueError("user_uid is required and cannot be empty")

        name = f"agent_{channel_name}_{agent_uid}_{int(time.time())}"

        # ============================================================
        # KEY DIFFERENCE: CustomLLM with output_modalities=["audio"]
        # ============================================================
        # The base quickstart uses a managed text LLM + MiniMax TTS. This
        # recipe instead points the LLM stage at our own OpenAI-compatible
        # endpoint via CustomLLM AND sets output_modalities=["audio"], which
        # tells Agora cloud the endpoint returns audio directly — the PCM
        # audio from your endpoint plays straight to the user over RTC.
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

        # STT transcribes the user's speech into text for the LLM.
        stt = DeepgramSTT(model="nova-3", language="en")

        # A TTS vendor is still configured because the agora-agents 2.0 builder
        # REQUIRES one in cascading mode (it raises "TTS configuration is
        # required" otherwise). It is effectively INERT: with
        # output_modalities=["audio"] the LLM returns audio directly, so there
        # is no text for the TTS to synthesize and Agora plays the endpoint's
        # audio. We keep it only to satisfy the builder.
        tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")

        parameters = {
            "data_channel": "rtm",
            "enable_error_message": True,
            "enable_metrics": True,
        }
        if isinstance(output_audio_codec, str) and output_audio_codec.strip():
            parameters["output_audio_codec"] = output_audio_codec.strip()

        agora_agent = AgoraAgent(
            name=name,
            instructions=AUDIO_AGENT_PROMPT,
            greeting=self.greeting,
            failure_message="Please wait a moment.",
            max_history=50,
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
            advanced_features={"enable_rtm": True},
            parameters=parameters,
        )

        agora_agent = (
            agora_agent
            .with_stt(stt)
            .with_llm(llm)
            .with_tts(tts)
        )

        session = agora_agent.create_async_session(
            client=self.client,
            channel=channel_name,
            agent_uid=str(agent_uid),
            remote_uids=[str(user_uid)],
            enable_string_uid=False,
            idle_timeout=30,
            expires_in=3600,
        )

        logger.info(
            "Starting Custom LLM agent channel=%s agent_uid=%s user_uid=%s llm_url=%s",
            channel_name,
            agent_uid,
            user_uid,
            self.custom_llm_url,
        )

        try:
            agent_id = await session.start()
        except Exception:
            logger.exception(
                "Failed to start Custom LLM agent channel=%s agent_uid=%s user_uid=%s",
                channel_name,
                agent_uid,
                user_uid,
            )
            raise

        # Save session for later stop
        self._sessions[agent_id] = session

        logger.info(
            "Started Custom LLM agent agent_id=%s channel=%s",
            agent_id,
            channel_name,
        )

        return {
            "agent_id": agent_id,
            "channel_name": channel_name,
            "status": "started",
        }

    async def stop(self, agent_id: str) -> None:
        """Stop a running agent. Falls back to the stateless client path."""
        if not agent_id or not str(agent_id).strip():
            raise ValueError("agent_id is required and cannot be empty")

        session = self._sessions.pop(agent_id, None)
        if session:
            try:
                await session.stop()
                logger.info("Stopped agent from active session agent_id=%s", agent_id)
                return
            except Exception:
                logger.warning(
                    "Failed to stop agent from active session; falling back agent_id=%s",
                    agent_id,
                    exc_info=True,
                )

        logger.info("Stopping agent through client.stop_agent agent_id=%s", agent_id)
        await self.client.stop_agent(agent_id)
