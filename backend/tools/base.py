"""
NEXUS Tool Framework — Abstract base and registry for agent tools.

Every tool:
- Accepts a cancel_event for cooperative cancellation
- Returns a structured ToolResult
- Has deterministic mock fallbacks
- Reports progress via events
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Standardised output from a tool execution."""

    success: bool = True
    data: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    error: str | None = None


class BaseTool(ABC):
    """Abstract base class for all NEXUS tools."""

    name: str = ""
    description: str = ""
    category: str = "GENERAL"  # SEARCH, DATABASE, CALCULATOR, VISION, API

    @abstractmethod
    async def execute(
        self, params: dict[str, Any], cancel_event: asyncio.Event
    ) -> ToolResult:
        """Execute the tool. Check cancel_event periodically for cooperative cancellation."""
        ...

    def validate_params(self, params: dict[str, Any]) -> bool:
        """Validate input parameters. Override in subclasses."""
        return True

    async def _check_cancelled(self, cancel_event: asyncio.Event) -> None:
        """Raise CancelledError if cancel_event is set."""
        if cancel_event.is_set():
            raise asyncio.CancelledError(f"Tool {self.name} cancelled")

    async def _simulate_latency(
        self, seconds: float, cancel_event: asyncio.Event, steps: int = 10
    ) -> None:
        """Simulate realistic async latency with cancellation checkpoints."""
        step_time = seconds / steps
        for _ in range(steps):
            await self._check_cancelled(cancel_event)
            await asyncio.sleep(step_time)


class ToolRegistry:
    """Registry of available tools, keyed by name."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": t.name, "description": t.description, "category": t.category}
            for t in self._tools.values()
        ]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())


def create_default_registry() -> ToolRegistry:
    """Create a registry with all built-in tools."""
    from backend.tools.search import DestinationSearchTool, HotelSearchTool, ActivitySearchTool
    from backend.tools.calculator import BudgetCalculatorTool
    from backend.tools.database import DatabaseQueryTool
    from backend.tools.vision import VisionAnalysisTool

    registry = ToolRegistry()
    registry.register(DestinationSearchTool())
    registry.register(HotelSearchTool())
    registry.register(ActivitySearchTool())
    registry.register(BudgetCalculatorTool())
    registry.register(DatabaseQueryTool())
    registry.register(VisionAnalysisTool())
    return registry
