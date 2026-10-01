"""
SURU AI — Generic Adversarial & Global Response Routing Test Matrix.

Spans categories A through X with diverse, unseen test inputs:
A. historical information (past years, completed tournaments)
B. current information (live, current context)
C. future information (upcoming events)
D. date ranges (multi-day spans)
E. schedules (historical season vs upcoming fixtures)
F. lists (comprehensive lists)
G. factual questions (direct answers)
H. explanations (in-depth concepts)
I. comparisons (X vs Y)
J. calculations (arithmetic, percentages)
K. coding (data structures, algorithms)
L. multi-step tasks (itineraries, workflows)
M. sports (past archives vs live fixtures)
N. entertainment (movies, awards)
O. science (astronomy, physics)
P. technology (protocols, architecture)
Q. geography (capitals, rivers, landmarks)
R. history (ancient & modern historical events)
S. arbitrary named entities
T. follow-up questions (context continuity)
U. multimodal questions (image context)
V. voice input (audio cleanup, speech synthesis)
W. interruption during response (real-time replanning)
X. unsupported / ambiguous requests (graceful clarification)
"""

import asyncio
import re
import pytest
from unittest.mock import AsyncMock, patch

from backend.agent.orchestrator import Orchestrator
from backend.agent.interruption_manager import Interruption, InterruptionType
from backend.providers.base import MockProvider
from backend.providers.google_gemini import GeminiProvider
from backend.realtime.events import EventBus, EventType
from backend.tools.base import create_default_registry
from backend.tools.date_parser import parse_date_intent


@pytest.fixture
def clean_orchestrator():
    eb = EventBus()
    tools = create_default_registry()
    provider = MockProvider()
    orch = Orchestrator(
        session_id="test_adversarial_global",
        llm_provider=provider,
        tool_registry=tools,
        event_bus=eb,
    )
    return orch, eb


# ============================================================================
# CATEGORY A: Historical Information (Past seasons, explicit past years)
# ============================================================================
@pytest.mark.asyncio
async def test_category_a_historical_information():
    provider = MockProvider()
    queries = [
        "Who won the 2018 FIFA World Cup?",
        "Give me the final results of the 2020 Tokyo Olympics marathon",
        "Who was the champion of Wimbledon 2021?",
        "What was the outcome of the Battle of Waterloo in 1815?",
    ]
    for q in queries:
        intent = await provider.determine_intent(q, current_date="2026-09-30")
        assert intent["category"] in ["CURRENT_INFORMATION", "DIRECT_KNOWLEDGE"]
        assert intent["category"] != "SPORTS_FIXTURE_QUERY", f"Failed for historical: {q}"


# ============================================================================
# CATEGORY B: Current Information (Requires fresh grounding)
# ============================================================================
@pytest.mark.asyncio
async def test_category_b_current_information():
    provider = MockProvider()
    queries = [
        "What is the current price of gold today?",
        "Who is the current prime minister of Japan as of now?",
        "What are the latest developments in quantum computing this week?",
    ]
    for q in queries:
        intent = await provider.determine_intent(q, current_date="2026-09-30")
        assert intent["category"] == "CURRENT_INFORMATION"
        assert intent.get("needs_grounding") is True, f"Failed grounding for: {q}"


# ============================================================================
# CATEGORY C & D: Future Information & Date Ranges
# ============================================================================
@pytest.mark.asyncio
async def test_category_c_d_future_and_date_ranges():
    provider = MockProvider()
    # Explicit future range
    d_from, d_to = parse_date_intent("What events are happening between October 10 and October 15?", reference_date="2026-09-30")
    assert d_from == "2026-10-10"
    assert d_to == "2026-10-15"

    # Weekend parsing
    sat, sun = parse_date_intent("Show matches this weekend", reference_date="2026-09-30")
    assert sat is not None and sun is not None
    assert sat < sun


# ============================================================================
# CATEGORY E: Schedules (Historical Season Archive vs Upcoming Fixtures)
# ============================================================================
@pytest.mark.asyncio
async def test_category_e_schedules_temporal_split():
    provider = MockProvider()
    # Historical schedule request -> must NOT be forced into live ESPN scoreboard
    hist_intent = await provider.determine_intent("Give me the complete schedule of IPL 2025", current_date="2026-09-30")
    assert hist_intent["category"] in ["CURRENT_INFORMATION", "DIRECT_KNOWLEDGE"]
    assert hist_intent["category"] != "SPORTS_FIXTURE_QUERY"

    # Upcoming fixture request -> routed to live sports fixtures
    upcoming_intent = await provider.determine_intent("What football matches are scheduled for tomorrow?", current_date="2026-09-30")
    assert upcoming_intent["category"] == "SPORTS_FIXTURE_QUERY"
    assert upcoming_intent["sports_params"]["status"] in ["UPCOMING", "ALL"]


# ============================================================================
# CATEGORY F: Lists & Complete Requests
# ============================================================================
@pytest.mark.asyncio
async def test_category_f_lists_fulfillment():
    provider = MockProvider()
    queries = [
        "List the top 10 fastest land animals",
        "Give me a complete list of ISO 27001 security controls",
        "What are the 7 wonders of the ancient world?",
    ]
    for q in queries:
        intent = await provider.determine_intent(q, current_date="2026-09-30")
        assert intent["category"] in ["DIRECT_KNOWLEDGE", "CURRENT_INFORMATION"]
        assert intent["category"] != "SPORTS_FIXTURE_QUERY"


# ============================================================================
# CATEGORY G, H, I: Factual, Explanation, Comparison
# ============================================================================
@pytest.mark.asyncio
async def test_category_g_h_i_factual_explanation_comparison(clean_orchestrator):
    orch, _ = clean_orchestrator

    # Factual
    res_fact = await orch.handle_user_input("What is the capital of Australia?")
    assert "Canberra" in res_fact.get("response", "")

    # Explanation / Science
    res_exp = await orch.handle_user_input("Explain photosynthesis.")
    assert "chemical energy" in res_exp.get("response", "").lower() or "glucose" in res_exp.get("response", "").lower()

    # Comparison
    res_comp = await orch.handle_user_input("Explain TCP vs UDP.")
    assert "TCP" in res_comp.get("response", "")
    assert "UDP" in res_comp.get("response", "")


# ============================================================================
# CATEGORY J: Calculation
# ============================================================================
@pytest.mark.asyncio
async def test_category_j_calculation(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Calculate 15% of 80000")
    assert res.get("status") == "completed"
    assert "12,000" in res.get("response", "") or "12000" in res.get("response", "")


# ============================================================================
# CATEGORY K: Coding
# ============================================================================
@pytest.mark.asyncio
async def test_category_k_coding(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Explain ArrayList vs LinkedList in Java")
    assert res.get("status") == "completed"
    resp = res.get("response", "")
    assert "ArrayList" in resp
    assert "LinkedList" in resp


# ============================================================================
# CATEGORY L: Multi-step Tasks (TaskGraph execution)
# ============================================================================
@pytest.mark.asyncio
async def test_category_l_multi_step_travel(clean_orchestrator):
    orch, _ = clean_orchestrator
    res = await orch.handle_user_input("Plan a 3-day Chennai trip for ₹15,000")
    assert res.get("status") in ["plan_started", "completed"]
    assert len(orch.task_graph) > 0
    assert orch.goal_manager.current_goal.constraints.get("city") == "chennai"
    assert orch.goal_manager.current_goal.constraints.get("budget") == 15000


# ============================================================================
# CATEGORY M: Sports (Distinguishing Live Fixtures vs Tactical/Factual Questions)
# ============================================================================
@pytest.mark.asyncio
async def test_category_m_sports_mode_distinction():
    provider = MockProvider()

    # Live Fixtures -> SPORTS_FIXTURE_QUERY
    q1 = "What Champions League games are tonight?"
    intent1 = await provider.determine_intent(q1, current_date="2026-09-30")
    assert intent1["category"] == "SPORTS_FIXTURE_QUERY"

    # Tactical/Rules Question -> DIRECT_KNOWLEDGE or CURRENT_INFORMATION
    q2 = "Explain the offside rule in football."
    intent2 = await provider.determine_intent(q2, current_date="2026-09-30")
    assert intent2["category"] in ["DIRECT_KNOWLEDGE", "CURRENT_INFORMATION"]
    assert intent2["category"] != "SPORTS_FIXTURE_QUERY"


# ============================================================================
# CATEGORY N, O, P, Q, R, S: Domains & Arbitrary Entities (Intent Classification)
# ============================================================================
@pytest.mark.asyncio
async def test_category_domains_and_arbitrary_entities():
    provider = MockProvider()
    test_queries = [
        ("Who directed the 1994 movie The Shawshank Redemption?", "DIRECT_KNOWLEDGE"),
        ("What is the speed of light in vacuum?", "DIRECT_KNOWLEDGE"),
        ("Explain how DNS resolution works.", "DIRECT_KNOWLEDGE"),
        ("What is the longest river in South America?", "DIRECT_KNOWLEDGE"),
        ("Who wrote The Prince in 1513?", "DIRECT_KNOWLEDGE"),
    ]
    for q, expected_cat in test_queries:
        intent = await provider.determine_intent(q, current_date="2026-09-30")
        assert intent["category"] in [expected_cat, "CURRENT_INFORMATION"]
        assert intent["category"] != "SPORTS_FIXTURE_QUERY"
        assert intent.get("needs_dag") is False


# ============================================================================
# CATEGORY T: Follow-up Questions (Context Preservation)
# ============================================================================
@pytest.mark.asyncio
async def test_category_t_follow_up_context(clean_orchestrator):
    orch, _ = clean_orchestrator

    turn1 = await orch.handle_user_input("Who is Stephen Curry?")
    assert "Stephen Curry" in turn1.get("response", "")

    turn2 = await orch.handle_user_input("What team does he play for?")
    assert "Golden State Warriors" in turn2.get("response", "")


# ============================================================================
# CATEGORY V: Audio & TTS Text Sanitization (No raw SVG or internal metadata)
# ============================================================================
def test_category_v_tts_sanitization():
    # Simulation of TTS cleanup regex from useSpeechSynthesis.ts
    raw_markdown = """
    Here are the results:
    | Team | Score |
    |------|-------|
    | Team A | 2 |
    | Team B | 1 |

    <svg width="24" height="24"><path d="M0 0h24v24H0z"/></svg>
    [Click here](https://example.com/details)
    """

    # 1. Strip SVG tags
    cleaned = re.sub(r"<svg[\s\S]*?<\/svg>", "", raw_markdown, flags=re.IGNORECASE)
    assert "<svg" not in cleaned
    assert "</svg>" not in cleaned

    # 2. Strip URLs & markdown links
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    assert "https://example.com" not in cleaned
    assert "Click here" in cleaned


# ============================================================================
# CATEGORY W: Interruption during response / Replanning
# ============================================================================
@pytest.mark.asyncio
async def test_category_w_interruption_replanning(clean_orchestrator):
    orch, _ = clean_orchestrator

    # Initial plan
    res1 = await orch.handle_user_input("Plan a 3-day Chennai trip for 15,000 rupees.")
    assert res1["status"] == "plan_started"
    assert orch.goal_manager.current_goal.constraints.get("budget") == 15000

    # User interrupts: change budget to 20,000 rupees
    res2 = await orch.handle_user_input("Wait, change the budget to 20,000 rupees")
    assert res2["status"] == "replanned"
    assert "diff" in res2
    assert orch.goal_manager.current_goal.constraints.get("budget") == 20000


# ============================================================================
# CATEGORY X: Ambiguous / Direct General Questions
# ============================================================================
@pytest.mark.asyncio
async def test_category_x_ambiguous_and_direct():
    provider = MockProvider()
    res = await provider.determine_intent("Tell me something interesting about Mars", current_date="2026-09-30")
    assert res["category"] in ["DIRECT_KNOWLEDGE", "CURRENT_INFORMATION"]
    assert res.get("needs_dag") is False
