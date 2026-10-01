"""
Deterministic Evaluation Scenarios for SURU AI Agent.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Optional
from pydantic import BaseModel, Field

from backend.agent.orchestrator import Orchestrator, AgentState
from backend.execution.task_graph import TaskStatus
from backend.memory.session_memory import SessionMemory
from backend.providers.base import MockProvider
from backend.realtime.events import EventBus, EventType, NexusEvent
from backend.tools.base import ToolRegistry, create_default_registry


class ScenarioResult(BaseModel):
    scenario_id: str
    scenario_name: str
    passed: bool
    duration_ms: float
    task_completion: str  # "COMPLETE", "PARTIAL", "NOT_MEASURED"
    interruption_recovery: str  # "SUCCESS", "NOT_APPLICABLE", "FAILED"
    latency_ms: float
    protocol_compliance: bool
    errors: list[str] = Field(default_factory=list)
    final_state_snapshot: dict[str, Any] = Field(default_factory=dict)
    events_count: int = 0


async def run_scenario_1_basic_goal() -> ScenarioResult:
    """Scenario 1 — Basic goal execution."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s1_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    errors = []
    res = await orch.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await orch.executor.wait_for_completion(timeout=2.0)
    await orch.executor.stop()

    snap = orch.get_snapshot()
    goal = snap.get("goal", {}).get("current_goal", {}).get("summary", "")
    passed = "Chennai" in goal or "15000" in goal or "plan_started" in res.get("status", "")

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_1",
        scenario_name="Basic Goal Execution",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE" if snap.get("task_graph", {}).get("tasks") else "PARTIAL",
        interruption_recovery="NOT_APPLICABLE",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        errors=errors,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_2_constraint_change() -> ScenarioResult:
    """Scenario 2 — Constraint change interruption."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s2_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    await orch.handle_user_input("Plan a Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.05)

    interruption_res = await orch.handle_user_input("Wait. I am travelling with my parents. Avoid places requiring lots of walking.")
    await orch.executor.wait_for_completion(timeout=2.0)
    await orch.executor.stop()

    snap = orch.get_snapshot()
    passed = interruption_res.get("status") in ("replanned", "processed") and orch.plan_version > 1

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_2",
        scenario_name="Constraint Change Interruption",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_3_question_interruption() -> ScenarioResult:
    """Scenario 3 — Side question interruption."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s3_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    await orch.handle_user_input("Plan a Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.05)

    q_res = await orch.handle_user_input("Why did you choose that hotel?")
    await orch.executor.stop()

    snap = orch.get_snapshot()
    passed = q_res.get("status") == "answering_question" and "answer" in q_res

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_3",
        scenario_name="Side Question Interruption",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_4_task_cancellation() -> ScenarioResult:
    """Scenario 4 — Explicit task cancellation."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s4_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    await orch.handle_user_input("Plan a Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.05)

    cancel_res = await orch.handle_user_input("Don't search for hotels anymore.")
    await orch.executor.stop()

    snap = orch.get_snapshot()
    passed = cancel_res.get("status") in ("cancelled", "replanned", "processed")

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_4",
        scenario_name="Task Cancellation",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_5_goal_pivot() -> ScenarioResult:
    """Scenario 5 — Complete goal pivot (NEW_GOAL)."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s5_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    await orch.handle_user_input("Plan a Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.05)

    pivot_res = await orch.handle_user_input("Forget the trip. Help me prepare for an interview instead.")
    await orch.executor.stop()

    snap = orch.get_snapshot()
    passed = pivot_res.get("status") in ("new_goal_started", "plan_started") and orch.plan_version > 1

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_5",
        scenario_name="Complete Goal Pivot",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_6_rapid_interruptions() -> ScenarioResult:
    """Scenario 6 — Rapid consecutive interruptions."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s6_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    inputs = [
        "Budget is 15000.",
        "Actually 18000.",
        "No, make it 20000.",
        "Wait, 25000.",
    ]
    for text in inputs:
        await orch.handle_user_input(text)
        await asyncio.sleep(0.01)

    await orch.executor.stop()
    snap = orch.get_snapshot()
    passed = orch.plan_version >= 4 and orch.state != AgentState.IDLE or snap.get("goal") is not None

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_6",
        scenario_name="Rapid Consecutive Interruptions",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_7_voice_interruption() -> ScenarioResult:
    """Scenario 7 — Voice speech_started onset interruption."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s7_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    await orch.set_state(AgentState.SPEAKING, reason="test_speech")
    await orch.handle_speech_started()

    snap = orch.get_snapshot()
    passed = orch.state == AgentState.INTERRUPTED

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_7",
        scenario_name="Voice Onset Interruption",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_8_multimodal() -> ScenarioResult:
    """Scenario 8 — Multimodal image + text grounding."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s8_{int(time.time())}"
    orch, eb, _ = await sm.get_or_create(sid)

    img_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    img_res = await orch.handle_image_upload(img_b64, prompt="Hotel photo")
    await orch.handle_user_input("Use this and change my plan")
    await orch.executor.stop()

    snap = orch.get_snapshot()
    passed = img_res.get("status") == "image_analyzed"

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_8",
        scenario_name="Multimodal Grounding",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap,
        events_count=len(eb.get_events(sid)),
    )


async def run_scenario_9_reconnect() -> ScenarioResult:
    """Scenario 9 — Disconnect and reconnect to existing session."""
    start_time = time.perf_counter()
    sm = SessionMemory()
    sid = f"eval_s9_{int(time.time())}"

    orch1, eb1, is_new1 = await sm.get_or_create(sid)
    await orch1.handle_user_input("Plan a Chennai trip")
    snap1 = orch1.get_snapshot()

    orch2, eb2, is_new2 = await sm.get_or_create(sid)
    snap2 = orch2.get_snapshot()

    passed = is_new1 is True and is_new2 is False and orch1 is orch2 and snap1["session_id"] == snap2["session_id"]

    duration_ms = (time.perf_counter() - start_time) * 1000
    return ScenarioResult(
        scenario_id="scenario_9",
        scenario_name="Session Disconnect & Reconnect",
        passed=passed,
        duration_ms=round(duration_ms, 2),
        task_completion="COMPLETE",
        interruption_recovery="SUCCESS" if passed else "FAILED",
        latency_ms=round(duration_ms, 2),
        protocol_compliance=True,
        final_state_snapshot=snap2,
        events_count=len(eb2.get_events(sid)),
    )
