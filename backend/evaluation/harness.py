"""
SURU AI Evaluation Harness — Main suite execution manager.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Awaitable
from backend.evaluation.scenarios import (
    ScenarioResult,
    run_scenario_1_basic_goal,
    run_scenario_2_constraint_change,
    run_scenario_3_question_interruption,
    run_scenario_4_task_cancellation,
    run_scenario_5_goal_pivot,
    run_scenario_6_rapid_interruptions,
    run_scenario_7_voice_interruption,
    run_scenario_8_multimodal,
    run_scenario_9_reconnect,
)


SCENARIO_RUNNERS: dict[str, Callable[[], Awaitable[ScenarioResult]]] = {
    "scenario_1": run_scenario_1_basic_goal,
    "scenario_2": run_scenario_2_constraint_change,
    "scenario_3": run_scenario_3_question_interruption,
    "scenario_4": run_scenario_4_task_cancellation,
    "scenario_5": run_scenario_5_goal_pivot,
    "scenario_6": run_scenario_6_rapid_interruptions,
    "scenario_7": run_scenario_7_voice_interruption,
    "scenario_8": run_scenario_8_multimodal,
    "scenario_9": run_scenario_9_reconnect,
}


class EvaluationHarness:
    """Manager for executing scenario-based evaluation benchmarks."""

    async def run_scenario(self, scenario_id: str) -> ScenarioResult | None:
        key = scenario_id.lower()
        if not key.startswith("scenario_"):
            key = f"scenario_{key}"
        runner = SCENARIO_RUNNERS.get(key)
        if not runner:
            return None
        return await runner()

    async def run_all(self) -> list[ScenarioResult]:
        results = []
        for key, runner in SCENARIO_RUNNERS.items():
            res = await runner()
            results.append(res)
        return results


# Global singleton harness instance
evaluation_harness = EvaluationHarness()
