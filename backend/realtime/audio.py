"""
NEXUS Audio Layer — Audio chunk handling and speech state events.

Processes incoming audio streams, coordinates speech start/end signals,
and provides integration hooks for browser Web Speech or Cloud STT/TTS.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Awaitable
from pydantic import BaseModel, Field

from backend.realtime.events import EventBus, EventType


class AudioChunk(BaseModel):
    session_id: str
    chunk_index: int = 0
    data_b64: str = ""
    is_final: bool = False
    timestamp: float = 0.0


class AudioHandler:
    """
    Manages speech activity detection and audio forwarding.
    """

    def __init__(self, event_bus: EventBus, session_id: str = "") -> None:
        self.event_bus = event_bus
        self.session_id = session_id
        self.is_recording = False

    async def on_speech_started(self) -> None:
        """Called when Voice Activity Detection detects user speech onset."""
        self.is_recording = True
        await self.event_bus.emit(
            EventType.USER_SPEECH_STARTED,
            session_id=self.session_id,
        )

    async def on_speech_ended(self, transcript: str = "") -> None:
        """Called when user pauses/stops speaking."""
        self.is_recording = False
        await self.event_bus.emit(
            EventType.USER_SPEECH_ENDED,
            session_id=self.session_id,
            transcript=transcript,
        )

    async def process_audio_chunk(self, chunk: AudioChunk) -> None:
        """Process incoming raw audio frames."""
        # Ready for direct streaming STT piping (Deepgram/Google)
        pass
