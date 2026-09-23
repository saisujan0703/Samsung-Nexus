"""
NEXUS Database/Query Tool — Structured queries against mock travel databases.
"""

from __future__ import annotations

import asyncio
from typing import Any

from backend.tools.base import BaseTool, ToolResult


# Transport data
TRANSPORT_DB = {
    "chennai": {
        "local": [
            {"type": "auto_rickshaw", "avg_cost_per_km": 15, "accessibility": "moderate"},
            {"type": "taxi/uber", "avg_cost_per_km": 12, "accessibility": "good"},
            {"type": "metro", "avg_cost_per_trip": 40, "accessibility": "excellent"},
            {"type": "bus", "avg_cost_per_trip": 15, "accessibility": "basic"},
            {"type": "suburban_train", "avg_cost_per_trip": 10, "accessibility": "moderate"},
        ],
        "inter_city": [
            {"from": "Chennai", "to": "Mahabalipuram", "distance_km": 58, "bus_cost": 100, "taxi_cost": 1200},
            {"from": "Chennai", "to": "Pondicherry", "distance_km": 150, "bus_cost": 300, "taxi_cost": 3000},
            {"from": "Chennai", "to": "Kanchipuram", "distance_km": 72, "bus_cost": 120, "taxi_cost": 1500},
        ],
    }
}

RESTAURANT_DB = {
    "chennai": [
        {"name": "Saravana Bhavan", "cuisine": "South Indian", "price_range": "budget", "avg_meal_cost": 200, "rating": 4.3, "accessibility": "good"},
        {"name": "Murugan Idli Shop", "cuisine": "South Indian", "price_range": "budget", "avg_meal_cost": 150, "rating": 4.4, "accessibility": "moderate"},
        {"name": "Dakshin - ITC", "cuisine": "South Indian Fine Dining", "price_range": "premium", "avg_meal_cost": 1500, "rating": 4.7, "accessibility": "excellent"},
        {"name": "Copper Chimney", "cuisine": "North Indian", "price_range": "mid", "avg_meal_cost": 600, "rating": 4.1, "accessibility": "good"},
        {"name": "Bay 146", "cuisine": "Multi-cuisine", "price_range": "mid", "avg_meal_cost": 500, "rating": 4.0, "accessibility": "good"},
        {"name": "Junior Kuppanna", "cuisine": "Chettinad", "price_range": "mid", "avg_meal_cost": 400, "rating": 4.2, "accessibility": "moderate"},
    ],
}


class DatabaseQueryTool(BaseTool):
    name = "database_query"
    description = "Query structured databases for transport, restaurants, and general travel info"
    category = "DATABASE"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        query_type = params.get("query_type", "")
        city = params.get("city", "").lower()

        await self._simulate_latency(1.0, cancel_event)

        if query_type == "transport":
            data = TRANSPORT_DB.get(city, {})
            return ToolResult(
                success=True,
                data={"transport": data, "city": city},
                summary=f"Found transport options for {city.title()}",
            )

        elif query_type == "restaurants":
            restaurants = RESTAURANT_DB.get(city, [])
            max_cost = params.get("max_meal_cost", None)
            if max_cost:
                restaurants = [r for r in restaurants if r["avg_meal_cost"] <= max_cost]
            min_accessibility = params.get("min_accessibility", None)
            if min_accessibility:
                acc_order = {"basic": 0, "moderate": 1, "good": 2, "excellent": 3}
                min_level = acc_order.get(min_accessibility, 0)
                restaurants = [r for r in restaurants if acc_order.get(r["accessibility"], 0) >= min_level]
            return ToolResult(
                success=True,
                data={"restaurants": restaurants, "city": city, "count": len(restaurants)},
                summary=f"Found {len(restaurants)} restaurants in {city.title()}",
            )

        elif query_type == "itinerary_check":
            # Validate an itinerary against constraints
            items = params.get("items", [])
            constraints = params.get("constraints", {})
            issues: list[str] = []
            total_cost = 0

            for item in items:
                cost = item.get("cost", 0)
                total_cost += cost
                if constraints.get("max_walking") and item.get("walking") == "high":
                    if constraints["max_walking"] in ("low", "moderate"):
                        issues.append(f"{item.get('name', 'Unknown')} requires high walking")

            budget = constraints.get("budget", 0)
            if budget and total_cost > budget:
                issues.append(f"Total cost ₹{total_cost} exceeds budget ₹{budget}")

            return ToolResult(
                success=True,
                data={"valid": len(issues) == 0, "issues": issues, "total_cost": total_cost},
                summary=f"Itinerary check: {'valid' if not issues else f'{len(issues)} issues found'}",
            )

        return ToolResult(
            success=False,
            error=f"Unknown query type: {query_type}",
            summary="Query failed: unknown type",
        )
