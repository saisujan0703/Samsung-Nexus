"""
NEXUS Calculator Tool — Budget calculation, cost estimation, and trip cost breakdown.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.tools.base import BaseTool, ToolResult


class BudgetCalculatorTool(BaseTool):
    name = "budget_calculator"
    description = "Calculate trip budgets, cost breakdowns, and per-person costs"
    category = "CALCULATOR"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        await self._simulate_latency(0.5, cancel_event)

        total_budget = params.get("total_budget", 0)
        num_people = params.get("num_people", 1)
        num_nights = params.get("num_nights", 1)

        # Gather cost items
        hotel_cost = params.get("hotel_cost_per_night", 0) * num_nights
        activity_costs = params.get("activity_costs", [])
        transport_cost = params.get("transport_cost", 0)
        food_cost_per_day = params.get("food_cost_per_day", 500) * (num_nights + 1)
        misc_cost = params.get("misc_cost", 0)

        total_activity_cost = sum(
            a.get("cost_per_person", 0) * num_people for a in activity_costs
        ) if isinstance(activity_costs, list) else 0

        total_food = food_cost_per_day * num_people
        total_transport = transport_cost * num_people

        total_estimated = hotel_cost + total_activity_cost + total_food + total_transport + misc_cost
        remaining = total_budget - total_estimated
        per_person = total_estimated / max(num_people, 1)

        within_budget = total_estimated <= total_budget if total_budget > 0 else True

        breakdown = {
            "hotel": hotel_cost,
            "activities": total_activity_cost,
            "food": total_food,
            "transport": total_transport,
            "miscellaneous": misc_cost,
            "total_estimated": total_estimated,
            "total_budget": total_budget,
            "remaining": remaining,
            "per_person": round(per_person, 2),
            "within_budget": within_budget,
            "num_people": num_people,
            "num_nights": num_nights,
        }

        status = "within budget" if within_budget else "over budget"
        summary = (
            f"Total estimated: ₹{total_estimated:,.0f} | "
            f"Budget: ₹{total_budget:,.0f} | "
            f"Per person: ₹{per_person:,.0f} | "
            f"Status: {status}"
        )

        return ToolResult(success=True, data=breakdown, summary=summary)
