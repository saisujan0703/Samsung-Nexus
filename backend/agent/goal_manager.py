"""
NEXUS Goal Manager — Tracks current goal, constraints, and goal history.

Detects whether user input represents a constraint change, goal modification,
or completely new goal.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.realtime.events import EventBus, EventType


import re


class Goal(BaseModel):
    """Represents a user's current goal."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    summary: str = ""
    raw_input: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    version: int = 1
    parent_goal_id: str | None = None
    status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETE, PARTIAL, FAILED


class GoalManager:
    """
    Manages the user's current goal and constraint history.

    Responsibilities:
    - Set and update goals
    - Track constraint changes with versioning
    - Detect what changed between old and new goals
    - Maintain goal history for context preservation
    """

    def __init__(self, event_bus: EventBus, session_id: str = "") -> None:
        self.event_bus = event_bus
        self.session_id = session_id
        self.current_goal: Goal | None = None
        self.goal_history: list[Goal] = []

    async def set_goal(self, summary: str, constraints: dict[str, Any], raw_input: str = "") -> Goal:
        """Set a brand new goal, preserving and extracting initial constraints."""
        if self.current_goal:
            self.goal_history.append(self.current_goal)

        final_constraints = dict(constraints)
        text_source = f"{raw_input} {summary}".strip()
        text_lower = text_source.lower()

        # Check if this is a travel planning goal (and NOT a pivot away from travel)
        is_cancelling_travel = any(p in text_lower for p in ["forget the trip", "forget about the trip", "cancel the trip", "stop the trip", "no trip", "forget trip"])
        is_travel = not is_cancelling_travel and any(k in text_lower for k in ["trip", "travel", "tour", "hotel", "itinerary", "vacation"])

        if is_travel:
            # Extract city
            if "city" not in final_constraints:
                for c in ["chennai", "bangalore", "delhi", "mumbai", "goa", "jaipur", "hyderabad", "kolkata", "pune", "kochi", "tokyo", "paris"]:
                    if c in text_lower:
                        final_constraints["city"] = c
                        break

            # Extract duration
            if "duration_days" not in final_constraints:
                m_days = re.search(r"(\d+)\s*[- ]?day", text_lower)
                if m_days:
                    final_constraints["duration_days"] = int(m_days.group(1))
                else:
                    final_constraints["duration_days"] = 3

            # Extract group size
            if "num_people" not in final_constraints:
                m_people = re.search(r"(\d+)\s*(?:people|person|pax|traveller|traveler)", text_lower)
                if m_people:
                    final_constraints["num_people"] = int(m_people.group(1))
                else:
                    final_constraints["num_people"] = 1

            # Extract budget
            if "budget" not in final_constraints:
                m_budget = re.search(r"(?:₹|\brs\.?|\binr)\s*(\d[\d,]*)", text_lower)
                if not m_budget:
                    m_budget = re.search(r"\bbudget\b.*?(\d[\d,]*)", text_lower)
                if m_budget:
                    cleaned_val = m_budget.group(1).replace(",", "")
                    if cleaned_val.isdigit():
                        final_constraints["budget"] = int(cleaned_val)

        goal = Goal(
            summary=summary,
            raw_input=raw_input,
            constraints=final_constraints,
            status="IN_PROGRESS",
        )
        self.current_goal = goal

        await self.event_bus.emit(
            EventType.GOAL_SET,
            session_id=self.session_id,
            goal_id=goal.id,
            summary=goal.summary,
            constraints=goal.constraints,
        )

        return goal

    async def update_constraints(self, changes: dict[str, Any], reason: str = "") -> dict[str, Any]:
        """
        Update constraints on the current goal while strictly preserving existing constraints.

        Returns a dict of what actually changed (old_value → new_value).
        """
        if not self.current_goal:
            return {}

        actual_changes: dict[str, Any] = {}
        old_constraints = dict(self.current_goal.constraints)

        # Ensure base travel constraints are not lost if this is a travel goal
        full_text = f"{self.current_goal.raw_input} {self.current_goal.summary}".lower()
        is_cancelling = any(p in full_text for p in ["forget the trip", "forget about the trip", "cancel the trip", "stop the trip", "no trip"])
        if not is_cancelling and any(k in full_text for k in ["trip", "travel", "chennai", "bangalore", "delhi", "mumbai"]):
            if "city" not in self.current_goal.constraints:
                for c in ["chennai", "bangalore", "delhi", "mumbai", "goa", "jaipur", "hyderabad"]:
                    if c in full_text:
                        self.current_goal.constraints["city"] = c
                        break
                if "city" not in self.current_goal.constraints:
                    self.current_goal.constraints["city"] = "chennai"

            if "duration_days" not in self.current_goal.constraints:
                m_days = re.search(r"(\d+)\s*[- ]?day", full_text)
                self.current_goal.constraints["duration_days"] = int(m_days.group(1)) if m_days else 3

            if "num_people" not in self.current_goal.constraints:
                m_people = re.search(r"(\d+)\s*(?:people|person|pax|traveller|traveler)", full_text)
                self.current_goal.constraints["num_people"] = int(m_people.group(1)) if m_people else 1

        for key, new_value in changes.items():
            old_value = self.current_goal.constraints.get(key)

            if key == "num_people_delta":
                # Special handling: delta change
                current_people = self.current_goal.constraints.get("num_people", 1)
                new_people = current_people + new_value
                self.current_goal.constraints["num_people"] = new_people
                actual_changes["num_people"] = {"old": current_people, "new": new_people, "reason": changes.get("reason", reason)}
            elif old_value != new_value:
                self.current_goal.constraints[key] = new_value
                actual_changes[key] = {"old": old_value, "new": new_value}

        if actual_changes:
            self.current_goal.version += 1

            # Update goal summary if travel constraints are active
            c = self.current_goal.constraints
            city = str(c.get("city") or "Chennai").title()
            is_travel_summary = "trip" in (self.current_goal.summary or "").lower() or bool(c.get("city"))

            if is_travel_summary:
                days = c.get("duration_days", 3)
                people = c.get("num_people", 1)
                budget = c.get("budget", 15000)
                walking = c.get("max_walking", None)

                people_text = "1 person" if people == 1 else f"{people} people"
                if isinstance(budget, (int, float)):
                    summary_parts = [f"Plan a {days}-day {city} trip for {people_text} under ₹{int(budget):,}"]
                else:
                    summary_parts = [f"Plan a {days}-day {city} trip for {people_text}"]

                if walking:
                    summary_parts.append(f"(max walking: {walking})")
                self.current_goal.summary = " ".join(summary_parts)

            await self.event_bus.emit(
                EventType.GOAL_CHANGED,
                session_id=self.session_id,
                goal_id=self.current_goal.id,
                changes=actual_changes,
                new_constraints=self.current_goal.constraints,
                new_summary=self.current_goal.summary,
                version=self.current_goal.version,
            )

        return actual_changes

    def get_constraints(self) -> dict[str, Any]:
        return self.current_goal.constraints if self.current_goal else {}

    def get_goal_summary(self) -> str:
        return self.current_goal.summary if self.current_goal else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_goal": self.current_goal.model_dump() if self.current_goal else None,
            "history_count": len(self.goal_history),
        }
