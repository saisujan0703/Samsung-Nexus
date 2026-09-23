"""
NEXUS Interruption Manager — Classifies and routes user interruptions.

Determines the type of interruption and what impact it should have
on the current execution plan.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from backend.providers.base import LLMProvider, Classification
from backend.realtime.events import EventBus, EventType


class InterruptionType(str, Enum):
    BACKCHANNEL = "BACKCHANNEL"
    CORRECTION = "CORRECTION"
    QUESTION = "QUESTION"
    CONSTRAINT_CHANGE = "CONSTRAINT_CHANGE"
    GOAL_CHANGE = "GOAL_CHANGE"
    TASK_CANCELLATION = "TASK_CANCELLATION"
    NEW_GOAL = "NEW_GOAL"


class Interruption(BaseModel):
    """A classified user interruption."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: InterruptionType
    raw_text: str
    confidence: float = 1.0
    reasoning: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_was_speaking: bool = False
    agent_was_executing: bool = False


class InterruptionManager:
    """
    Classifies user interruptions and determines their impact.

    Does NOT directly modify the task graph or goal — it classifies
    the interruption and returns structured information for the
    orchestrator to act on.
    """

    CATEGORIES = [
        "BACKCHANNEL",
        "CORRECTION",
        "QUESTION",
        "CONSTRAINT_CHANGE",
        "GOAL_CHANGE",
        "TASK_CANCELLATION",
        "NEW_GOAL",
    ]

    def __init__(
        self,
        llm_provider: LLMProvider,
        event_bus: EventBus,
        session_id: str = "",
    ) -> None:
        self.llm = llm_provider
        self.event_bus = event_bus
        self.session_id = session_id
        self.history: list[Interruption] = []

    async def classify_interruption(
        self,
        text: str,
        agent_was_speaking: bool = False,
        agent_was_executing: bool = False,
        current_goal: str = "",
    ) -> Interruption:
        """
        Classify a user utterance that occurred during agent activity.

        Returns a structured Interruption with type, confidence, and details.
        """
        await self.event_bus.emit(
            EventType.INTERRUPTION_DETECTED,
            session_id=self.session_id,
            text=text,
            agent_was_speaking=agent_was_speaking,
            agent_was_executing=agent_was_executing,
        )

        # Use LLM to classify
        classification = await self.llm.classify(
            text=text,
            categories=self.CATEGORIES,
            context=current_goal,
        )

        interruption = Interruption(
            type=InterruptionType(classification.category),
            raw_text=text,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            details=classification.details,
            agent_was_speaking=agent_was_speaking,
            agent_was_executing=agent_was_executing,
        )

        self.history.append(interruption)

        await self.event_bus.emit(
            EventType.INTERRUPTION_CLASSIFIED,
            session_id=self.session_id,
            interruption_id=interruption.id,
            type=interruption.type.value,
            confidence=interruption.confidence,
            reasoning=interruption.reasoning,
            details=interruption.details,
            text=text,
        )

        return interruption

    def get_history(self) -> list[Interruption]:
        return list(self.history)

    def get_interruption_count(self) -> int:
        return len(self.history)
