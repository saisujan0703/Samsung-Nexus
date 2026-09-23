"""
NEXUS Session Memory — In-memory session registry and cache.

Maintains active Orchestrator instances and metadata keyed by session_id.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from backend.agent.orchestrator import Orchestrator
from backend.config import settings
from backend.providers.base import LLMProvider, create_provider
from backend.realtime.events import EventBus
from backend.tools.base import ToolRegistry, create_default_registry


class SessionInfo:
    """Metadata container for an active session."""

    def __init__(self, session_id: str, orchestrator: Orchestrator, event_bus: EventBus) -> None:
        self.session_id = session_id
        self.orchestrator = orchestrator
        self.event_bus = event_bus
        self.created_at = time.time()
        self.last_active_at = time.time()

    def touch(self) -> None:
        self.last_active_at = time.time()


class SessionMemory:
    """
    In-memory registry managing the lifecycle of agent sessions.
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._sessions: dict[str, SessionInfo] = {}
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
        self._tools = create_default_registry()
        self._provider = create_provider(settings.LLM_PROVIDER)

    async def get_or_create(self, session_id: str) -> tuple[Orchestrator, EventBus, bool]:
        """
        Retrieve existing session or instantiate a new Orchestrator and EventBus.
        Returns: (orchestrator, event_bus, is_new)
        """
        async with self._lock:
            info = self._sessions.get(session_id)
            if info:
                info.touch()
                return info.orchestrator, info.event_bus, False

            # Create new session components
            event_bus = EventBus()
            orchestrator = Orchestrator(
                session_id=session_id,
                llm_provider=self._provider,
                tool_registry=self._tools,
                event_bus=event_bus,
            )

            info = SessionInfo(session_id, orchestrator, event_bus)
            self._sessions[session_id] = info
            return orchestrator, event_bus, True

    async def get(self, session_id: str) -> tuple[Orchestrator, EventBus] | tuple[None, None]:
        async with self._lock:
            info = self._sessions.get(session_id)
            if info:
                info.touch()
                return info.orchestrator, info.event_bus
            return None, None

    async def delete(self, session_id: str) -> bool:
        async with self._lock:
            info = self._sessions.pop(session_id, None)
            if info:
                await info.orchestrator.executor.stop()
                return True
            return False

    async def list_sessions(self) -> list[dict[str, Any]]:
        async with self._lock:
            result = []
            for sid, info in self._sessions.items():
                result.append({
                    "session_id": sid,
                    "created_at": info.created_at,
                    "last_active_at": info.last_active_at,
                    "state": info.orchestrator.state.value,
                })
            return result


# Global singleton session memory
session_memory = SessionMemory(ttl_seconds=settings.SESSION_TTL_SECONDS)
