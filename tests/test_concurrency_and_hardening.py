"""
Comprehensive automated tests for Phase 5 — Real-Time + Concurrency Hardening
"""

import asyncio
from typing import Any
import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.agent.orchestrator import Orchestrator, AgentState
from backend.agent.interruption_manager import Interruption, InterruptionType
from backend.agent.replanner import Replanner, PlanDiff
from backend.execution.task_executor import TaskExecutor
from backend.execution.task_graph import Task, TaskGraph, TaskStatus
from backend.memory.session_memory import SessionMemory
from backend.providers.base import MockProvider, PlanSpec
from backend.realtime.events import EventBus, EventType, NexusEvent
from backend.tools.base import ToolRegistry, BaseTool, ToolResult


class SlowMockTool(BaseTool):
    """Tool that sleeps to simulate work and test cancellation/concurrency."""
    name: str = "slow_tool"
    description: str = "A slow mock tool for testing."
    delay: float = 0.2

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        step = 0.02
        elapsed = 0.0
        while elapsed < self.delay:
            if cancel_event and cancel_event.is_set():
                return ToolResult(success=False, data={}, summary="Cancelled during delay")
            await asyncio.sleep(step)
            elapsed += step
        return ToolResult(success=True, data={"result": f"processed_{params}"}, summary="Success")


@pytest.fixture
def components():
    eb = EventBus()
    tr = ToolRegistry()
    tr.register(SlowMockTool())
    llm = MockProvider()
    tg = TaskGraph()
    executor = TaskExecutor(tg, tr, eb, "test_session")
    orchestrator = Orchestrator("test_session", llm, tr, eb)
    return eb, tr, llm, tg, executor, orchestrator


# --------------------------------------------------------------------------
# Test A: Two independent tasks execute concurrently without duplicate execution
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_concurrent_task_execution(components):
    eb, tr, llm, tg, executor, orchestrator = components
    t1 = Task(id="t1", name="Task 1", description="", tool="slow_tool", input={"v": 1})
    t2 = Task(id="t2", name="Task 2", description="", tool="slow_tool", input={"v": 2})
    tg.add_task(t1)
    tg.add_task(t2)

    await executor.start()
    completed = await executor.wait_for_completion(timeout=1.5)
    print(f"DEBUG test_a: completed={completed}, t1={t1.status}, t2={t2.status}, running={list(executor._running.keys())}")
    await executor.stop()

    assert completed is True
    assert t1.status == TaskStatus.COMPLETED
    assert t2.status == TaskStatus.COMPLETED
    assert t1.output == {"result": "processed_{'v': 1}"}
    assert t2.output == {"result": "processed_{'v': 2}"}


# --------------------------------------------------------------------------
# Test B: Task is cancelled while running
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_b_task_cancellation_propagation(components):
    eb, tr, llm, tg, executor, orchestrator = components
    slow_tool = SlowMockTool()
    slow_tool.delay = 0.5
    tr.register(slow_tool)

    t1 = Task(id="t1", name="Task 1", description="", tool="slow_tool", input={"v": 1})
    tg.add_task(t1)

    asyncio.create_task(executor.start())
    await asyncio.sleep(0.05)  # Let it start running
    assert t1.status == TaskStatus.RUNNING

    cancelled_ids = await executor.cancel_task("t1", "user_cancelled")
    await executor.stop()

    assert "t1" in cancelled_ids
    assert t1.status == TaskStatus.CANCELLED
    assert t1.output is None  # Must NOT commit success output


# --------------------------------------------------------------------------
# Test C & D: Stale task result and plan version isolation
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_c_and_d_stale_result_and_plan_versioning(components):
    eb, tr, llm, tg, executor, orchestrator = components
    t1 = Task(id="t1", name="Task 1", description="", tool="slow_tool", input={"v": 1})
    tg.add_task(t1)

    executor.plan_version = 1
    cancel_event = asyncio.Event()

    # Launch task directly under plan_version 1
    atask = asyncio.create_task(
        executor._run_task(t1, cancel_event, "t1_p1_abc", 1)
    )

    # Change plan version before task completes
    executor.plan_version = 2
    await atask

    # Output must NOT be committed because plan version changed
    assert t1.output is None
    assert t1.status != TaskStatus.COMPLETED


# --------------------------------------------------------------------------
# Test E: Idempotent PlanDiff Application
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_e_idempotent_plan_diff(components):
    eb, tr, llm, tg, executor, orchestrator = components
    replanner = Replanner(llm, eb, "test_session")

    t1 = Task(id="t1", name="Task 1", description="", tool="slow_tool", input={"v": 1})
    tg.add_task(t1)

    diff = PlanDiff(diff_id="diff_123")
    diff.cancel.append("t1")

    # Apply first time
    summary1 = await replanner.apply_diff(tg, diff)
    assert "t1" in summary1["cancelled"]

    # Apply second time with same diff
    summary2 = await replanner.apply_diff(tg, diff)
    assert summary2.get("idempotent_skip") is True
    assert summary2["cancelled"] == []


# --------------------------------------------------------------------------
# Test F: Rapid Consecutive Interruptions
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f_rapid_consecutive_interruptions(components):
    eb, tr, llm, tg, executor, orchestrator = components

    # Simulate rapid calls to handle_user_input / handle_speech_started
    task1 = asyncio.create_task(orchestrator.handle_user_input("Plan a trip to Chennai for 15k"))
    await asyncio.sleep(0.01)
    task2 = asyncio.create_task(orchestrator.handle_speech_started())
    task3 = asyncio.create_task(orchestrator.handle_user_input("Make it 20k instead"))
    task4 = asyncio.create_task(orchestrator.handle_user_input("Actually 25k"))

    res1, _, res3, res4 = await asyncio.gather(task1, task2, task3, task4)

    # System must settle without deadlock or exception
    assert orchestrator.state in (AgentState.EXECUTING, AgentState.IDLE, AgentState.REPLANNING)
    assert orchestrator.plan_version > 1


# --------------------------------------------------------------------------
# Test G & H: Session Memory Persistence across disconnects/reconnects
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_g_and_h_session_persistence_reconnect():
    sm = SessionMemory()
    sid = "persisted_session_123"

    orch1, eb1, is_new1 = await sm.get_or_create(sid)
    assert is_new1 is True

    await orch1.handle_user_input("Initial goal")
    initial_version = orch1.plan_version

    # Reconnect to same session
    orch2, eb2, is_new2 = await sm.get_or_create(sid)
    assert is_new2 is False
    assert orch2 is orch1
    assert eb2 is eb1
    assert orch2.plan_version == initial_version


# --------------------------------------------------------------------------
# Test I: EventBus Subscriber Exception Isolation
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_i_eventbus_subscriber_error_isolation():
    eb = EventBus()
    received = []

    async def faulty_subscriber(event: NexusEvent):
        raise ValueError("Subscriber failed intentionally")

    async def healthy_subscriber(event: NexusEvent):
        received.append(event.type)

    eb.subscribe(EventType.USER_TEXT_INPUT, faulty_subscriber)
    eb.subscribe(EventType.USER_TEXT_INPUT, healthy_subscriber)

    # Emit event — faulty subscriber error must be caught and healthy subscriber must receive event
    event = await eb.emit(EventType.USER_TEXT_INPUT, text="test")
    assert EventType.USER_TEXT_INPUT in received
