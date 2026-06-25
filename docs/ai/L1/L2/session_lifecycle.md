# Deep Dive — Session Lifecycle

> **When to Read This:** You are touching client-side join, token renewal, RTC/RTM wiring, transcript handling, or mid-call control. For the contracts these calls hit, see [06_interfaces](../06_interfaces.md).

The browser owns the full RTC/RTM client lifecycle; the backend owns tokens and the agent session. The two meet only at `/api/*`.

## End-to-end flow

1. **Config** — `LandingPage.tsx` calls `getConfig()` (`web/src/services/api.ts`) → `GET /api/get_config`. Backend mints a Token007 (RTC+RTM, 3600s) for a concrete non-zero UID and returns `{ app_id, token, uid, channel_name, agent_uid }`.
2. **Join** — `ConversationComponent.tsx` joins the RTC channel with the returned token/UID, publishes the microphone, and logs in to RTM.
3. **Start agent** — `startAgent(channelName, rtcUid, userUid)` → `POST /api/startAgent`. Backend validates inputs, builds the CustomLLM vendor chain, starts the async session, and returns `agent_id`.
4. **Converse** — user audio flows to Deepgram STT; transcript text is sent to the custom audio endpoint; PCM audio is returned and streamed to the RTC channel. RTM delivers transcript + metrics.
5. **Stop** — `stopAgent(agentId)` → `POST /api/stopAgent`. The client also releases RTC/RTM media on end-call.

## Backend session bookkeeping

`Agent` (`server/src/agent.py`) keeps an in-memory map `self._sessions[agent_id] = session`.

- `stop(agent_id)` pops the session and calls `session.stop()`.
- If the session is missing (e.g. process restarted), it falls back to `self.client.stop_agent(agent_id)` — the stateless cloud path. Stop is robust across restarts but `_sessions` is **not** a durable store.

## Transcript handling (`web/src/lib/conversation.ts`)

- `normalizeTranscript(transcript, localUid)` — maps `uid === '0'` to the local UID and runs `normalizeTranscriptSpacing` on text.
- `normalizeTimestampMs(ts)` — promotes second-precision timestamps to ms.
- `getMessageList` / `getCurrentInProgressMessage` — split finalized vs in-progress turns (by `TurnStatus.IN_PROGRESS`).
- `mapAgentVisualizerState(agentState, isConnected, connectionState)` — maps SDK state → UIKit visualizer state (`joining`, `listening`, `analyzing`, `talking`, `ambient`, `disconnected`).

The pipeline metrics displayed in the UI show STT + Custom LLM (audio); there is no TTS metric because TTS is not used at runtime.

## Token renewal

Tokens expire at 3600s. The client re-fetches config / renews as needed in `LandingPage.tsx`; renewal uses the same `get_config` contract. Keep renewal client-side — the backend stays stateless about who is connected.

## What stays where

- **Client owns:** RTC join, mic publish, RTM login, transcript/metrics/state listeners, token renewal, explicit end-call media release.
- **Backend owns:** token minting, vendor chain build, session start/stop.
- Do not move token logic into the web app or add Route Handlers for it (see [07_gotchas](../07_gotchas.md)).

## Related L1

- [02_architecture](../02_architecture.md) · [03_code_map](../03_code_map.md) · [06_interfaces](../06_interfaces.md)
