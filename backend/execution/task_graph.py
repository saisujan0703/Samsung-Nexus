"""
NEXUS Task Graph — Core data structure for the interruptible agent.

This module implements:
- Task status state machine with enforced valid transitions
- Task data model with full lifecycle tracking
- TaskGraph: DAG of tasks with dependency resolution, concurrent scheduling,
  selective cancellation, and plan-diff support
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class PlanDiffAction(str, Enum):
    KEEP = "KEEP"
    CANCEL = "CANCEL"
    MODIFY = "MODIFY"
    ADD = "ADD"


# Valid state transitions
VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),  # terminal
    TaskStatus.CANCELLED: set(),  # terminal
    TaskStatus.FAILED: {TaskStatus.PENDING},  # retry
    TaskStatus.BLOCKED: {TaskStatus.PENDING, TaskStatus.CANCELLED},
}


# ---------------------------------------------------------------------------
# Task Model
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """A single unit of work in the agent's execution plan."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    tool: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] | None = None
    dependencies: list[str] = Field(default_factory=list)
    priority: int = 0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    cancellation_reason: str | None = None
    affected_by: str | None = None  # interruption ID
    diff_action: PlanDiffAction | None = None  # set during replanning

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        return new_status in VALID_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: TaskStatus, reason: str | None = None) -> None:
        if not self.can_transition_to(new_status):
            raise InvalidTransitionError(
                f"Cannot transition task '{self.name}' from {self.status} to {new_status}"
            )
        self.status = new_status
        now = datetime.now(timezone.utc).isoformat()
        if new_status == TaskStatus.RUNNING:
            self.started_at = now
        elif new_status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
            self.completed_at = now
        if new_status == TaskStatus.CANCELLED and reason:
            self.cancellation_reason = reason

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED)

    @property
    def is_active(self) -> bool:
        return self.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.BLOCKED)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class InvalidTransitionError(Exception):
    pass


# ---------------------------------------------------------------------------
# Task Graph
# ---------------------------------------------------------------------------

class TaskGraph:
    """
    Directed Acyclic Graph of tasks.

    Supports:
    - Dependency-aware scheduling
    - Concurrent task identification
    - Selective cancellation (plan diff)
    - State queries
    """

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._version: int = 0

    # -- Mutation ----------------------------------------------------------

    def add_task(self, task: Task) -> Task:
        """Add a task to the graph. Validates dependency references."""
        for dep_id in task.dependencies:
            if dep_id not in self._tasks:
                raise ValueError(f"Dependency '{dep_id}' not found in graph")
        self._tasks[task.id] = task
        self._version += 1
        return task

    def add_tasks(self, tasks: list[Task]) -> list[Task]:
        """Add multiple tasks, resolving dependencies in order."""
        added = []
        for task in tasks:
            self.add_task(task)
            added.append(task)
        return added

    def remove_task(self, task_id: str) -> Task | None:
        task = self._tasks.pop(task_id, None)
        if task:
            self._version += 1
        return task

    def update_task_status(
        self, task_id: str, new_status: TaskStatus, reason: str | None = None
    ) -> Task:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Task '{task_id}' not found")
        task.transition_to(new_status, reason)
        self._version += 1
        return task

    def set_task_output(self, task_id: str, output: dict[str, Any]) -> Task:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Task '{task_id}' not found")
        task.output = output
        return task

    # -- Queries -----------------------------------------------------------

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        return [t for t in self._tasks.values() if t.status == status]

    def get_ready_tasks(self) -> list[Task]:
        """Return PENDING tasks whose dependencies are all COMPLETED."""
        ready = []
        for task in self._tasks.values():
            if task.status != TaskStatus.PENDING:
                continue
            deps_met = all(
                self._tasks.get(dep_id) is not None
                and self._tasks[dep_id].status == TaskStatus.COMPLETED
                for dep_id in task.dependencies
            )
            if deps_met:
                ready.append(task)
        return sorted(ready, key=lambda t: t.priority, reverse=True)

    def get_dependents(self, task_id: str) -> list[Task]:
        """Get all tasks that depend on the given task (direct dependents)."""
        return [t for t in self._tasks.values() if task_id in t.dependencies]

    def get_downstream(self, task_id: str) -> list[Task]:
        """Get all transitive dependents of a task."""
        visited: set[str] = set()
        result: list[Task] = []

        def _walk(tid: str) -> None:
            for t in self.get_dependents(tid):
                if t.id not in visited:
                    visited.add(t.id)
                    result.append(t)
                    _walk(t.id)

        _walk(task_id)
        return result

    @property
    def is_complete(self) -> bool:
        """True if all tasks are in a terminal state."""
        return all(t.is_terminal for t in self._tasks.values())

    @property
    def has_running_tasks(self) -> bool:
        return any(t.status == TaskStatus.RUNNING for t in self._tasks.values())

    @property
    def active_task_count(self) -> int:
        return sum(1 for t in self._tasks.values() if t.is_active)

    @property
    def has_active_tasks(self) -> bool:
        return self.active_task_count > 0

    @property
    def version(self) -> int:
        return self._version

    # -- Cancellation ------------------------------------------------------

    def cancel_task(self, task_id: str, reason: str = "plan_change") -> list[Task]:
        """
        Cancel a task and all its downstream dependents.
        Returns list of all cancelled tasks.
        """
        cancelled: list[Task] = []
        task = self.get_task(task_id)
        if task is None or task.is_terminal:
            return cancelled

        if task.can_transition_to(TaskStatus.CANCELLED):
            task.transition_to(TaskStatus.CANCELLED, reason)
            cancelled.append(task)
            self._version += 1

        # Cancel downstream tasks
        for downstream in self.get_downstream(task_id):
            if downstream.can_transition_to(TaskStatus.CANCELLED):
                downstream.transition_to(TaskStatus.CANCELLED, f"upstream_{task_id}_cancelled")
                cancelled.append(downstream)

        return cancelled

    def cancel_all_active(self, reason: str = "goal_change") -> list[Task]:
        """Cancel all non-terminal tasks."""
        cancelled: list[Task] = []
        for task in self._tasks.values():
            if task.is_active and task.can_transition_to(TaskStatus.CANCELLED):
                task.transition_to(TaskStatus.CANCELLED, reason)
                cancelled.append(task)
        if cancelled:
            self._version += 1
        return cancelled

    # -- Serialization -----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "tasks": [t.model_dump() for t in self._tasks.values()],
            "version": self._version,
        }

    def clear(self) -> None:
        self._tasks.clear()
        self._version += 1

    def __len__(self) -> int:
        return len(self._tasks)

    def __repr__(self) -> str:
        statuses = {}
        for t in self._tasks.values():
            statuses[t.status] = statuses.get(t.status, 0) + 1
        return f"TaskGraph(tasks={len(self)}, {statuses})"
