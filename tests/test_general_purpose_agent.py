"""
Automated regression test suite for Phase 8 — General-Purpose SURU AI Agent.

Verifies:
A. General knowledge ("What is the capital of Australia?")
B. Coding ("Explain ArrayList vs LinkedList in Java.")
C. Follow-up conversation context ("Who is Stephen Curry?" -> "What team does he play for?")
D. Non-travel query isolation ("Who is Lionel Messi?" -> no Chennai DAG, no travel constraints)
E. Arbitrary query ("Explain TCP vs UDP.")
F. Calculation ("Calculate 17.5% of 84000.")
G. Travel ("Plan a 3-day Chennai trip for ₹15,000.")
H. Complex task multi-step TaskGraph
I. Interruption & PlanDiff on complex task
J. Goal pivot (Travel -> Interview prep)
K. Gemini failure fallback handling
L. Gemini success end-to-end response delivery
M. Anti-question-echo verification
N. Tool failure handling
O. Secret safety (No API keys in serialized events or snapshots)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch

from backend.agent.orchestrator import AgentState, Orchestrator
from backend.agent.interruption_manager import Interruption, InterruptionType
from backend.memory.session_memory import SessionMemory
from backend.providers.base import MockProvider, create_provider
from backend.providers.google_gemini import GeminiProvider
from backend.realtime.events import EventBus, EventType
from backend.tools.base import create_default_registry
from backend.tools.calculator import CalculatorTool


@pytest.fixture
def clean_orchestrator():
    """Create a clean in-memory Orchestrator with MockProvider."""
    event_bus = EventBus()
    tools = create_default_registry()
    provider = MockProvider()
    orchestrator = Orchestrator(
        session_id="test_general_purpose",
        llm_provider=provider,
        tool_registry=tools,
        event_bus=event_bus,
    )
    return orchestrator, event_bus


# ---------------------------------------------------------------------------
# Test A: General Knowledge — Australia Capital (No question echo)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_a_general_knowledge_australia(clean_orchestrator):
    orch, eb = clean_orchestrator
    query = "What is the capital of Australia?"
    res = await orch.handle_user_input(query)

    assert res.get("status") == "completed"
    response_text = res.get("response", "")
    assert "Canberra" in response_text
    # Verify no question echo
    assert not response_text.startswith(f"I processed your request regarding '{query}'")
    assert not response_text.startswith("Synthesized response for:")
    # Verify no unnecessary DAG tasks created
    assert len(orch.task_graph) == 0


# ---------------------------------------------------------------------------
# Test B: Coding — ArrayList vs LinkedList
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_b_coding_arraylist_vs_linkedlist(clean_orchestrator):
    orch, _ = clean_orchestrator
    query = "Explain ArrayList vs LinkedList in Java."
    res = await orch.handle_user_input(query)

    assert res.get("status") == "completed"
    response_text = res.get("response", "")
    assert "ArrayList" in response_text
    assert "LinkedList" in response_text
    assert ("O(1)" in response_text or "array" in response_text.lower())
    assert len(orch.task_graph) == 0


# ---------------------------------------------------------------------------
# Test C: Follow-up Conversation — Stephen Curry -> What team does he play for?
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_c_followup_context_preservation(clean_orchestrator):
    orch, _ = clean_orchestrator

    # First turn
    res1 = await orch.handle_user_input("Who is Stephen Curry?")
    assert res1.get("status") == "completed"
    assert "Stephen Curry" in res1.get("response", "")

    # Second turn (contextual pronoun)
    res2 = await orch.handle_user_input("What team does he play for?")
    assert res2.get("status") == "completed"
    resp2 = res2.get("response", "")
    assert "Golden State Warriors" in resp2 or "Warriors" in resp2


# ---------------------------------------------------------------------------
# Test D: Non-Travel Query Isolation — Lionel Messi
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_d_non_travel_query_isolation(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Who is Lionel Messi?")

    assert res.get("status") == "completed"
    response_text = res.get("response", "")
    assert "Messi" in response_text

    # Verify no travel DAG was generated
    assert len(orch.task_graph) == 0

    # Verify no travel constraints were injected into GoalManager
    constraints = orch.goal_manager.get_constraints()
    assert "city" not in constraints or constraints["city"] != "chennai"
    assert "budget" not in constraints
    assert "num_people" not in constraints
    assert "max_walking" not in constraints
    assert "duration_days" not in constraints


# ---------------------------------------------------------------------------
# Test E: Arbitrary Query — TCP vs UDP
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_e_tcp_vs_udp(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Explain TCP vs UDP.")

    assert res.get("status") == "completed"
    response_text = res.get("response", "")
    assert "TCP" in response_text
    assert "UDP" in response_text
    assert "connection" in response_text.lower()


# ---------------------------------------------------------------------------
# Test F: Calculation — 17.5% of 84000
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_f_calculation_percentage(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Calculate 17.5% of 84000.")

    assert res.get("status") == "completed"
    response_text = res.get("response", "")
    # 17.5 / 100 * 84000 = 14700
    assert "14,700" in response_text or "14700" in response_text

    # Also test CalculatorTool directly
    calc_tool = CalculatorTool()
    tool_res = await calc_tool.execute({"expression": "17.5% of 84000"}, cancel_event=asyncio.Event())
    assert tool_res.success is True
    assert tool_res.data["result"] == 14700


# ---------------------------------------------------------------------------
# Test G: Travel — 3-day Chennai trip
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_g_travel_planning_preserved(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")

    assert res.get("status") == "plan_started"
    # Verify travel tasks were scheduled
    assert len(orch.task_graph) > 0
    task_tools = [t.tool for t in orch.task_graph.get_all_tasks()]
    assert "destination_search" in task_tools or "hotel_search" in task_tools

    # Constraints were properly populated
    constraints = orch.goal_manager.get_constraints()
    assert constraints.get("city") == "chennai"
    assert constraints.get("budget") == 15000

    await orch.executor.stop()


# ---------------------------------------------------------------------------
# Test H: Complex Multi-Step Task uses TaskGraph
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_h_complex_task_dag_scheduling(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Plan a 5-day Japan trip under ₹1.5 lakh, compare hotels and build an itinerary.")

    assert res.get("status") == "plan_started"
    assert len(orch.task_graph) >= 3
    await orch.executor.stop()


# ---------------------------------------------------------------------------
# Test I: Interruption & PlanDiff on Complex Task
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_i_interruption_and_plan_diff(clean_orchestrator):
    orch, _ = clean_orchestrator
    await orch.handle_user_input("Plan a 3-day Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.05)

    # Interrupt with budget change
    interruption_res = await orch.handle_user_input("Wait, change the budget to 20000.")

    assert interruption_res.get("status") == "replanned"
    assert orch.plan_version > 1
    assert orch.goal_manager.get_constraints().get("budget") == 20000
    assert "diff" in interruption_res
    await orch.executor.stop()


# ---------------------------------------------------------------------------
# Test J: Goal Pivot — Travel goal to completely unrelated goal
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_j_goal_pivot_unrelated_domain(clean_orchestrator):
    orch, _ = clean_orchestrator
    await orch.handle_user_input("Plan a Chennai trip for 15000 rupees.")
    await asyncio.sleep(0.05)

    # Pivot to interview prep
    pivot_res = await orch.handle_user_input("Forget the trip. Help me prepare for a Java interview.")

    assert pivot_res.get("status") in ("new_goal_started", "plan_started")
    assert orch.plan_version > 1
    # Check that previous travel tasks do not contaminate new goal
    goal_summary = orch.goal_manager.get_goal_summary()
    assert "Java interview" in goal_summary
    await orch.executor.stop()


# ---------------------------------------------------------------------------
# Test K: Gemini Failure — Truthful fallback
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_k_gemini_failure_truthful_fallback():
    provider = GeminiProvider(api_key="test_dummy_key", model="gemini-3.8-flash", fallback_to_mock=False)

    # Simulate 503 transient error from Google API
    with patch.object(provider, "_post_gemini", side_effect=RuntimeError("Gemini API error (status 503): High demand")):
        resp = await provider.generate_direct_response("What is photosynthesis?")
        assert "temporarily experiencing high demand" in resp or "unavailable" in resp
        # Must not fabricate an answer or crash
        assert "503" not in resp  # Raw status code masked from user


# ---------------------------------------------------------------------------
# Test L: Gemini Success — Content reaches RESPONSE_COMPLETED
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_l_gemini_success_end_to_end():
    event_bus = EventBus()
    tools = create_default_registry()
    provider = GeminiProvider(api_key="test_dummy_key", model="gemini-3.8-flash", fallback_to_mock=False)

    gemini_api_response = {
        "candidates": [{
            "content": {
                "parts": [{"text": "Canberra is the federal capital city of the Commonwealth of Australia."}]
            }
        }]
    }

    intent_api_response = {
        "candidates": [{
            "content": {
                "parts": [{"text": json.dumps({"category": "DIRECT_KNOWLEDGE", "needs_dag": False})}]
            }
        }]
    }

    async def mock_post(endpoint, payload):
        if "response_mime_type" in payload.get("generationConfig", {}):
            return intent_api_response
        return gemini_api_response

    with patch.object(provider, "_post_gemini", side_effect=mock_post):
        orch = Orchestrator(
            session_id="test_gemini_l",
            llm_provider=provider,
            tool_registry=tools,
            event_bus=event_bus,
        )

        res = await orch.handle_user_input("What is the capital of Australia?")
        assert res.get("status") == "completed"
        assert "Canberra is the federal capital city" in res.get("response", "")

        # Verify RESPONSE_COMPLETED event emitted with actual text
        completed_events = [
            e for e in event_bus.get_events("test_gemini_l")
            if e.type == EventType.RESPONSE_COMPLETED
        ]

        assert len(completed_events) == 1
        assert "Canberra is the federal capital city" in completed_events[0].data["text"]


# ---------------------------------------------------------------------------
# Test M: No Question Echo
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_m_no_question_echo(clean_orchestrator):
    orch, _ = clean_orchestrator
    questions = [
        "What is the capital of Australia?",
        "Who is Lionel Messi?",
        "Explain TCP vs UDP.",
        "What is photosynthesis?",
    ]
    for q in questions:
        res = await orch.handle_user_input(q)
        ans = res.get("response", "")
        # Assert response is not a mere echo of the question
        assert ans.strip() != q.strip()
        assert not ans.startswith(f"I processed your request regarding '{q}'")
        assert not ans.startswith(f"Synthesized response for: {q}")
        assert not ans.startswith(f"Retrieved current relevant information for: {q}")


# ---------------------------------------------------------------------------
# Test N: Tool Failure Handling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_n_tool_failure_handling():
    calc = CalculatorTool()
    # Invalid expression
    res = await calc.execute({"expression": "invalid @!#$ expression"}, cancel_event=asyncio.Event())
    assert res.success is False
    assert res.error is not None
    assert "failed" in res.summary.lower() or "error" in res.summary.lower()


# ---------------------------------------------------------------------------
# Test O: Secret Safety — No API Keys in Events or Snapshots
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_o_secret_safety_in_snapshots():
    fake_secret = "AIzaSySecretApiKey123456789"
    provider = GeminiProvider(api_key=fake_secret, model="gemini-3.8-flash")
    event_bus = EventBus()
    tools = create_default_registry()

    orch = Orchestrator(
        session_id="test_secret_safety",
        llm_provider=provider,
        tool_registry=tools,
        event_bus=event_bus,
    )

    await orch.handle_user_input("What is the capital of Australia?")

    snapshot = orch.get_snapshot()
    serialized_snapshot = json.dumps(snapshot)
    assert fake_secret not in serialized_snapshot

    events = [e.model_dump() for e in event_bus.get_events("test_secret_safety")]
    serialized_events = json.dumps(events)
    assert fake_secret not in serialized_events


# ---------------------------------------------------------------------------
# Test P: Arbitrary Unseen Query Reaches Gemini Without Canned Mock Output
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_p_arbitrary_unseen_query_gemini_routing(monkeypatch):
    """An arbitrary query should reach GeminiProvider and never return 'curated test domain'."""
    gemini_reply = "The Magna Carta was signed in 1215 and established that everyone, even the king, is subject to the law."
    
    class MockResponse:
        def __init__(self, text):
            self.status_code = 200
            self._data = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        def json(self):
            return self._data
        @property
        def text(self):
            return json.dumps(self._data)

    async def mock_post(self, url, headers=None, json=None, **kwargs):
        if "generateContent" in url:
            # Check if this is intent routing
            prompt_text = str(json)
            if "intent classifier" in prompt_text:
                return MockResponse('{"category": "DIRECT_KNOWLEDGE", "needs_dag": false, "reasoning": "general history question"}')
            return MockResponse(gemini_reply)
        return MockResponse("{}")

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.8-flash")
    event_bus = EventBus()
    tools = create_default_registry()
    orch = Orchestrator(session_id="test_arbitrary", llm_provider=provider, tool_registry=tools, event_bus=event_bus)

    res = await orch.handle_user_input("What is the historical significance of the Magna Carta?")
    ans = res.get("response", "")

    assert gemini_reply in ans
    assert "curated test domain" not in ans.lower()
    assert "offline mode" not in ans.lower()
    assert "unsupported" not in ans.lower()


# ---------------------------------------------------------------------------
# Test Q: Quota Exhaustion Seamlessly Switches to Candidate Model
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_q_gemini_quota_fallback_to_candidate_model(monkeypatch):
    """When primary model encounters 429 quota exhaustion, it switches to next candidate model."""
    call_log = []

    class MockResponse:
        def __init__(self, status_code, body):
            self.status_code = status_code
            self._data = body
            self.text = json.dumps(body)
        def json(self):
            return self._data

    async def mock_post(self, url, headers=None, json=None, **kwargs):
        call_log.append(url)
        if "gemini-3.6-flash" in url:
            # Primary model exhausted
            return MockResponse(429, {"error": {"status": "RESOURCE_EXHAUSTED", "message": "Quota exceeded limit 20"}})
        # Fallback candidate model succeeds
        return MockResponse(200, {"candidates": [{"content": {"parts": [{"text": "Dynamic answer from backup model."}]}}]})

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.6-flash")
    ans = await provider.generate_direct_response("Explain binary search tree.")

    assert ans == "Dynamic answer from backup model."
    assert any("gemini-3.6-flash" in u for u in call_log)
    assert any("gemini-3.8-flash" in u for u in call_log)
    assert provider.active_model == "gemini-3.8-flash"


# ---------------------------------------------------------------------------
# Test R: Truthful Error Message When All Gemini Candidates Fail
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_r_truthful_failure_message_when_all_gemini_down(monkeypatch):
    """When all Gemini models fail, system returns truthful service message without mock fallback."""
    class MockResponse:
        def __init__(self):
            self.status_code = 429
            self.text = json.dumps({"error": {"status": "RESOURCE_EXHAUSTED", "message": "All quotas exceeded"}})
        def json(self):
            return {"error": {"status": "RESOURCE_EXHAUSTED"}}

    async def mock_post(self, url, headers=None, json=None, **kwargs):
        return MockResponse()

    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)

    provider = GeminiProvider(api_key="test-key", model="gemini-3.6-flash")
    ans = await provider.generate_direct_response("Tell me a story.")

    # Truthful message; never curated mock text
    assert "curated test domain" not in ans.lower()
    assert "configure google_api_key in .env" not in ans.lower()
    assert "quota" in ans.lower() or "temporarily" in ans.lower()


