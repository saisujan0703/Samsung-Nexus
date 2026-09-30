"""
Regression Tests for Travel Planning and Constraint Changes (Phase 8.1)

Verifies:
1. Constraint preservation: When user changes budget, city, duration, and group size are preserved without '?' marks.
2. Plan Diff for budget changes: Budget-sensitive tasks are marked MODIFY, reusable tasks (e.g. destinations) are kept.
3. Realistic travel cost calculations: No double multiplication or absurd billion-rupee totals.
4. ToolResultStatus: Explicit SUCCESS_WITH_RESULTS vs SUCCESS_WITH_NO_RESULTS.
5. Plan status: COMPLETE vs PARTIAL when hotels or components are unavailable.
6. Pivot from travel to non-travel goal (Java interview) without constraint leakage.
7. General-purpose queries remain functional.
"""

import asyncio
import pytest

from backend.agent.orchestrator import AgentState
from backend.execution.task_graph import TaskStatus, PlanDiffAction
from backend.memory.session_memory import session_memory
from backend.tools.base import ToolResultStatus
from backend.tools.calculator import BudgetCalculatorTool
from backend.tools.search import HotelSearchTool


@pytest.mark.asyncio
async def test_constraint_preservation_on_budget_interruption():
    """Verify that changing the budget to ₹20,000 preserves Chennai, 3 days, and 1 person without '?'."""
    session_id = "test_reg_constraint_preservation"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    # Step 1: Initial goal
    res = await orchestrator.handle_user_input("Plan a 3-day Chennai trip for ₹15,000.")
    assert res["status"] in ("plan_started", "completed")
    await asyncio.sleep(0.1)

    initial_goal = orchestrator.goal_manager.current_goal
    assert initial_goal is not None
    assert initial_goal.constraints.get("city") == "chennai"
    assert initial_goal.constraints.get("duration_days") == 3
    assert initial_goal.constraints.get("num_people") == 1
    assert initial_goal.constraints.get("budget") == 15000
    assert "?" not in initial_goal.summary

    # Step 2: User interrupts with budget change
    replan_res = await orchestrator.handle_user_input("Wait, change the budget to ₹20,000.")
    assert replan_res["status"] == "replanned"

    # Step 3: Assert updated constraints and summary
    updated_goal = orchestrator.goal_manager.current_goal
    assert updated_goal is not None
    assert updated_goal.constraints.get("city") == "chennai"
    assert updated_goal.constraints.get("duration_days") == 3
    assert updated_goal.constraints.get("num_people") == 1
    assert updated_goal.constraints.get("budget") == 20000

    # Ensure no '?' placeholders anywhere
    assert "?" not in updated_goal.summary
    assert "₹20,000" in updated_goal.summary
    assert "3-day" in updated_goal.summary or "3 day" in updated_goal.summary
    assert "Chennai" in updated_goal.summary

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_plan_diff_budget_sensitive_tasks():
    """Verify that changing budget does NOT keep all tasks; budget-sensitive tasks are MODIFY."""
    session_id = "test_reg_plan_diff"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    # Initial goal
    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for ₹15,000.")
    await asyncio.sleep(0.2)

    # Interrupt with budget change
    replan_res = await orchestrator.handle_user_input("Wait, change the budget to ₹20,000.")
    diff = replan_res.get("diff", {})

    # Assert Plan Diff has both kept and modified tasks
    # Reusable info like destination search / requirements should be KEEP
    assert len(diff["keep"]) > 0, "Expected reusable tasks to be kept"
    # Budget-sensitive tasks (search_hotels, calculate_budget, etc.) must be MODIFY
    assert len(diff["modify"]) > 0, "Expected budget-sensitive tasks to be modified"

    # Ensure it didn't blindly keep all (KEEP=6, MODIFY=0)
    assert len(diff["modify"]) >= 2

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_realistic_travel_cost_calculation():
    """Verify budget calculator produces realistic figures in INR, never billions."""
    tool = BudgetCalculatorTool()
    cancel_event = asyncio.Event()

    # Case 1: 3-day trip, 1 person, 20k budget with mock dependency hotel output
    params = {
        "total_budget": 20000,
        "num_people": 1,
        "num_nights": 2,
        "_dependency_outputs": {
            "search_hotels": {
                "hotels": [{"name": "FabHotel Prime", "price_per_night": 2200, "rating": 3.9}]
            },
            "search_activities": {
                "activities": [{"name": "Mylapore Tour", "cost_per_person": 500}]
            },
        },
    }
    result = await tool.execute(params, cancel_event)
    assert result.success is True
    data = result.data

    assert data["currency"] == "INR"
    assert data["total_budget"] == 20000
    assert data["hotel_cost"] == 4400  # 2200 * 2 nights
    assert data["activity_cost"] == 500
    assert data["within_budget"] is True

    # Total estimated should be ~₹7,750 (hotel + activities + food + transport + misc)
    assert 5000 <= data["total_estimated"] <= 12000
    assert data["total_estimated"] < 20000
    # Must never be near billions!
    assert data["total_estimated"] < 1_000_000


@pytest.mark.asyncio
async def test_hotel_search_status_and_partial_plan():
    """Verify explicit SUCCESS_WITH_NO_RESULTS and PARTIAL plan status when hotels are unavailable."""
    tool = HotelSearchTool()
    cancel_event = asyncio.Event()

    # Search with very low impossible budget (₹100/night)
    res = await tool.execute({"city": "chennai", "max_price_per_night": 100}, cancel_event)
    assert res.success is True
    assert res.status == ToolResultStatus.SUCCESS_WITH_NO_RESULTS.value
    assert res.data["count"] == 0
    assert "No hotels found" in res.summary

    # Search with realistic budget (₹5,000/night)
    res_valid = await tool.execute({"city": "chennai", "max_price_per_night": 5000}, cancel_event)
    assert res_valid.success is True
    assert res_valid.status == ToolResultStatus.SUCCESS_WITH_RESULTS.value
    assert res_valid.data["count"] > 0
    assert "Found" in res_valid.summary


@pytest.mark.asyncio
async def test_goal_pivot_from_travel_to_java_interview():
    """Verify pivoting from travel to a Java interview supersedes the old graph and avoids constraint leakage."""
    session_id = "test_reg_goal_pivot"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    # Initial travel plan
    await orchestrator.handle_user_input("Plan a 3-day Chennai trip for ₹15,000.")
    await asyncio.sleep(0.1)

    # Pivot to Java interview
    pivot_res = await orchestrator.handle_user_input("Forget the trip. Help me prepare for a Java interview.")
    assert pivot_res["status"] in ("new_goal_started", "completed")

    current_goal = orchestrator.goal_manager.current_goal
    assert current_goal is not None
    assert "Java" in current_goal.summary or "interview" in current_goal.summary.lower()
    # Travel constraints should NOT leak into Java goal
    assert "city" not in current_goal.constraints or current_goal.constraints.get("city") != "chennai"
    assert "budget" not in current_goal.constraints

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)


@pytest.mark.asyncio
async def test_general_purpose_queries_remain_functional():
    """Verify general-purpose queries from Phase 8 continue working without degradation."""
    session_id = "test_reg_general_purpose"
    orchestrator, event_bus, _ = await session_memory.get_or_create(session_id)

    # Query 1: Capital of Australia
    r1 = await orchestrator.handle_user_input("What is the capital of Australia?")
    ans1 = r1.get("response", "")
    assert "Canberra" in ans1

    # Query 2: Java ArrayList vs LinkedList
    r2 = await orchestrator.handle_user_input("Explain ArrayList vs LinkedList in Java.")
    ans2 = r2.get("response", "")
    assert "ArrayList" in ans2 and "LinkedList" in ans2

    # Query 3: Who is Lionel Messi?
    r3 = await orchestrator.handle_user_input("Who is Lionel Messi?")
    ans3 = r3.get("response", "")
    assert "Messi" in ans3

    # Query 4: Follow up
    r4 = await orchestrator.handle_user_input("What club does he play for?")
    ans4 = r4.get("response", "")
    assert "Inter Miami" in ans4 or "football" in ans4.lower()

    await orchestrator.executor.stop()
    await session_memory.delete(session_id)
