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
from backend.memory.session_memory import SessionMemory, session_memory
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


# --------------------------------------------------------------------------
# Test J: Response Manager EventType.RESPONSE_STARTED Regression Test
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_j_response_started_event_emission_regression(components):
    eb, tr, llm, tg, executor, orchestrator = components
    events_received = []

    async def event_collector(evt: NexusEvent):
        events_received.append(evt.type)

    eb.subscribe_all(event_collector)

    # Directly test response generation event lifecycle
    resp = await orchestrator.response_manager.generate_task_response(
        task_results=[{"id": "t1", "name": "Task 1", "status": "COMPLETED", "output": {"res": "ok"}}],
        goal="Plan trip",
        context="Sample context",
    )

    assert EventType.RESPONSE_STARTED in events_received
    assert EventType.RESPONSE_COMPLETED in events_received
    assert len(resp) > 0


# --------------------------------------------------------------------------
# Tests K - O: Non-travel goals, Topic Pivot, Session Reset, Subscriptable Safety
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_k_non_travel_query_no_chennai_dag():
    """TEST A: Fresh session with general non-travel query generates no Chennai travel tasks."""
    session_id = "test_non_travel_fresh"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    res = await orchestrator.handle_user_input("What is the capital of Australia?")
    await asyncio.sleep(0.2)

    tasks = orchestrator.task_graph.get_all_tasks()
    task_names = [t.name.lower() for t in tasks]

    assert "what is the capital of australia?" in orchestrator.goal_manager.get_goal_summary().lower()
    assert not any("chennai" in name for name in task_names)
    assert not any("hotel" in name for name in task_names)


@pytest.mark.asyncio
async def test_l_topic_pivot_clears_chennai_dag():
    """TEST B: Active Chennai trip followed by general non-travel query pivots without executing Chennai tasks."""
    session_id = "test_topic_pivot"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.1)

    res = await orchestrator.handle_user_input("Find the latest information about the UEFA Champions League and tell me which teams are playing this week.")
    await asyncio.sleep(0.2)

    tasks = orchestrator.task_graph.get_all_tasks()
    task_names = [t.name.lower() for t in tasks]

    assert not any("chennai" in name for name in task_names)
    assert any("search" in name or "synthesize" in name for name in task_names)


@pytest.mark.asyncio
async def test_m_session_reset_isolation():
    """TEST C: Reset session creates isolated state without leaking old task graph."""
    old_id = "test_reset_old"
    orchestrator_old, event_bus_old, _ = await session_memory.get_or_create(old_id)
    await orchestrator_old.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.1)

    await session_memory.delete(old_id)

    new_id = "test_reset_new"
    orchestrator_new, event_bus_new, _ = await session_memory.get_or_create(new_id)
    await orchestrator_new.handle_user_input("What is the capital of Australia?")
    await asyncio.sleep(0.2)

    tasks = orchestrator_new.task_graph.get_all_tasks()
    task_names = [t.name.lower() for t in tasks]
    assert not any("chennai" in name for name in task_names)


@pytest.mark.asyncio
async def test_n_subscriptable_safe_response_generation(components):
    """TEST D: Verify non-dict outputs (ints, strings, empty lists) do not cause subscriptable TypeError."""
    eb, tr, llm, tg, executor, orchestrator = components

    results_with_int = [
        {"name": "Numeric Output Task", "status": "COMPLETED", "output": 42},
        {"name": "String Output Task", "status": "COMPLETED", "output": "Simple text"},
        {"name": "List of Strings Task", "status": "COMPLETED", "output": {"destinations": ["Place A", "Place B"], "count": 2}},
    ]

    response = await orchestrator.response_manager.generate_task_response(
        task_results=results_with_int,
        goal="Test goal with non-dict outputs",
        context="",
    )
    assert len(response) > 0
    assert "Place A" in response or "Simple text" in response or "Numeric" in response


@pytest.mark.asyncio
async def test_o_event_payload_schema_compliance(components):
    """TEST E: Verify RESPONSE_STARTED and RESPONSE_COMPLETED events have conformant payloads."""
    eb, tr, llm, tg, executor, orchestrator = components
    emitted_events = []

    async def event_logger(evt: NexusEvent):
        emitted_events.append(evt)

    eb.subscribe_all(event_logger)

    await orchestrator.response_manager.generate_task_response(
        task_results=[{"id": "t1", "name": "Task 1", "status": "COMPLETED", "output": {"results": "Ok"}}],
        goal="Schema test goal",
        context="Schema test context",
    )

    started_evts = [e for e in emitted_events if e.type == EventType.RESPONSE_STARTED]
    completed_evts = [e for e in emitted_events if e.type == EventType.RESPONSE_COMPLETED]

    assert len(started_evts) >= 1
    assert len(completed_evts) >= 1
    assert "goal" in started_evts[0].data
    assert "text" in completed_evts[0].data


@pytest.mark.asyncio
async def test_p_factual_query_returns_actual_answer():
    """Verify general factual queries return actual answer content (e.g. Canberra, Tokyo) not meta-text."""
    session_id1 = "test_factual_aus"
    orchestrator1, event_bus1, _ = await session_memory.get_or_create(session_id1)

    # Test Australia capital
    await orchestrator1.handle_user_input("What is the capital of Australia?")
    await asyncio.sleep(2.2)  # allow task graph execution (search + synthesize)
    tasks1 = orchestrator1.task_graph.get_all_tasks()
    completed_tasks1 = [t.to_dict() for t in tasks1 if t.status == TaskStatus.COMPLETED]
    response1 = await orchestrator1.response_manager.generate_task_response(
        task_results=completed_tasks1,
        goal="What is the capital of Australia?",
    )
    assert "Canberra" in response1
    assert "Retrieved current relevant information" not in response1

    # Test Japan capital in fresh session
    session_id2 = "test_factual_jpn"
    orchestrator2, event_bus2, _ = await session_memory.get_or_create(session_id2)
    await orchestrator2.handle_user_input("What is the capital of Japan?")
    await asyncio.sleep(2.2)
    tasks2 = orchestrator2.task_graph.get_all_tasks()
    completed_tasks2 = [t.to_dict() for t in tasks2 if t.status == TaskStatus.COMPLETED]
    response2 = await orchestrator2.response_manager.generate_task_response(
        task_results=completed_tasks2,
        goal="What is the capital of Japan?",
    )
    assert "Tokyo" in response2
    assert "Retrieved current relevant information" not in response2


@pytest.mark.asyncio
async def test_q_unknown_query_honest_no_fabrication(components):
    """Verify query with no retrieved data does not fabricate an answer."""
    eb, tr, llm, tg, executor, orchestrator = components

    no_data_results = [
        {"name": "Search info", "status": "COMPLETED", "output": {"query": "xyz123", "results": None, "found": False}},
        {"name": "Synthesize", "status": "COMPLETED", "output": {"query": "xyz123", "answer": None, "found": False}},
    ]

    response = await orchestrator.response_manager.generate_task_response(
        task_results=no_data_results,
        goal="Who won the 1842 lunar speedrace?",
        context="",
    )
    assert "google_api_key" in response.lower() or "processed your request" in response.lower()
    assert "Synthesized response for" not in response
