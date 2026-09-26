"""
NEXUS Event System — Structured event bus for observability and UI synchronization.

Every significant agent action emits a typed event. The frontend subscribes to
these events via WebSocket to drive its UI — there is no separate "UI state".
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field


class EventType(str, Enum):
    # Session lifecycle
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_ENDED = "SESSION_ENDED"

    # User interaction
    USER_SPEECH_STARTED = "USER_SPEECH_STARTED"
    USER_SPEECH_ENDED = "USER_SPEECH_ENDED"
    USER_TEXT_INPUT = "USER_TEXT_INPUT"
    USER_IMAGE_UPLOAD = "USER_IMAGE_UPLOAD"
    IMAGE_RECEIVED = "IMAGE_RECEIVED"
    IMAGE_PROCESSING = "IMAGE_PROCESSING"
    IMAGE_CONTEXT_READY = "IMAGE_CONTEXT_READY"

    # Agent state
    AGENT_STATE_CHANGED = "AGENT_STATE_CHANGED"
    AGENT_SPEAKING = "AGENT_SPEAKING"
    AGENT_RESPONSE_CHUNK = "AGENT_RESPONSE_CHUNK"
    AGENT_RESPONSE_COMPLETE = "AGENT_RESPONSE_COMPLETE"
    AGENT_RESUMED = "AGENT_RESUMED"

    # Interruption
    INTERRUPTION_DETECTED = "INTERRUPTION_DETECTED"
    INTERRUPTION_CLASSIFIED = "INTERRUPTION_CLASSIFIED"

    # Goal & Planning
    GOAL_SET = "GOAL_SET"
    GOAL_CHANGED = "GOAL_CHANGED"
    PLAN_CREATED = "PLAN_CREATED"
    PLAN_UPDATED = "PLAN_UPDATED"
    PLAN_DIFF_COMPUTED = "PLAN_DIFF_COMPUTED"

    # Task execution
    TASK_CREATED = "TASK_CREATED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_FAILED = "TASK_FAILED"
    TASK_PROGRESS = "TASK_PROGRESS"

    # Tools
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_PROGRESS = "TOOL_PROGRESS"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"

    # Context
    CONTEXT_UPDATED = "CONTEXT_UPDATED"
    CONTEXT_PRESERVED = "CONTEXT_PRESERVED"

    # Errors
    ERROR = "ERROR"


class NexusEvent(BaseModel):
    """A structured event in the NEXUS system."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    type: EventType
    session_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: dict[str, Any] = Field(default_factory=dict)

    def to_ws_message(self) -> dict:
        """Format for WebSocket transmission."""
        return {
            "type": "event",
            "payload": self.model_dump(),
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


# Type alias for event handlers
EventHandler = Callable[[NexusEvent], Awaitable[None]]


class EventBus:
    """
    Async publish/subscribe event bus.

    - Components publish events as they happen
    - The WebSocket layer subscribes to forward events to the frontend
    - Events are also logged for observability and evaluation
    """

    def __init__(self) -> None:
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []
        self._event_log: list[NexusEvent] = []
        self._max_log_size: int = 10000

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe to a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to ALL events."""
        self._global_handlers.append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h is not handler
            ]

    def unsubscribe_all(self, handler: EventHandler) -> None:
        self._global_handlers = [h for h in self._global_handlers if h is not handler]

    async def publish(self, event: NexusEvent) -> None:
        """Publish an event to all subscribed handlers."""
        # Log the event
        self._event_log.append(event)
        if len(self._event_log) > self._max_log_size:
            self._event_log = self._event_log[-self._max_log_size:]

        # Dispatch to type-specific handlers
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"[EventBus] Handler error for {event.type}: {e}")

        # Dispatch to global handlers
        for handler in self._global_handlers:
            try:
                await handler(event)
            except Exception as e:
                print(f"[EventBus] Global handler error: {e}")

    async def emit(
        self,
        event_type: EventType,
        session_id: str = "",
        **data: Any,
    ) -> NexusEvent:
        """Convenience: create and publish an event in one call."""
        event = NexusEvent(type=event_type, session_id=session_id, data=data)
        await self.publish(event)
        return event

    def get_events(
        self,
        session_id: str | None = None,
        event_type: EventType | None = None,
        limit: int = 100,
    ) -> list[NexusEvent]:
        """Query the event log."""
        events = self._event_log
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def clear_session_events(self, session_id: str) -> None:
        self._event_log = [e for e in self._event_log if e.session_id != session_id]

    def clear_all(self) -> None:
        self._event_log.clear()
