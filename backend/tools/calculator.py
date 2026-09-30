"""
NEXUS Calculator Tool — Budget calculation, cost estimation, and trip cost breakdown.
"""

from __future__ import annotations

import asyncio
import re
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
        num_nights = params.get("num_nights", 2)
        if num_nights < 1:
            num_nights = 1

        # Check for dependency outputs to resolve realistic costs from completed tasks
        dep_outputs = params.get("_dependency_outputs", {})
        hotel_cost_per_night = params.get("hotel_cost_per_night", 0)
        hotel_name = "Hotel"
        hotels_available = True

        if not hotel_cost_per_night and dep_outputs:
            for dep_out in dep_outputs.values():
                if isinstance(dep_out, dict) and "hotels" in dep_out:
                    hotels = dep_out.get("hotels", [])
                    if hotels:
                        top_hotel = hotels[0]
                        hotel_cost_per_night = top_hotel.get("price_per_night", 0)
                        hotel_name = top_hotel.get("name", "Hotel")
                        hotels_available = True
                    else:
                        hotels_available = False
                        hotel_name = "None within budget"
                        hotel_cost_per_night = 0
                    break

        num_rooms = max(1, (num_people + 1) // 2)
        hotel_cost = hotel_cost_per_night * num_nights * num_rooms

        activity_costs = params.get("activity_costs", [])
        total_activity_cost = 0
        if activity_costs and isinstance(activity_costs, list):
            total_activity_cost = sum(
                a.get("cost_per_person", 0) * num_people for a in activity_costs if isinstance(a, dict)
            )
        elif dep_outputs:
            for dep_out in dep_outputs.values():
                if isinstance(dep_out, dict) and isinstance(dep_out.get("activities"), list):
                    acts = dep_out["activities"][:3]
                    total_activity_cost = sum(
                        a.get("cost_per_person", 0) for a in acts if isinstance(a, dict)
                    ) * num_people
                    break

        transport_cost = params.get("transport_cost", 0)
        if not transport_cost:
            transport_cost = 350 * num_people  # realistic local transport

        food_cost_per_day = params.get("food_cost_per_day", 500)
        total_food = food_cost_per_day * (num_nights + 1) * num_people
        total_transport = transport_cost
        misc_cost = params.get("misc_cost", 300)

        total_estimated = hotel_cost + total_activity_cost + total_food + total_transport + misc_cost
        remaining = total_budget - total_estimated
        per_person = total_estimated / max(num_people, 1)

        within_budget = total_estimated <= total_budget if total_budget > 0 else True

        breakdown = {
            "hotel": hotel_cost,
            "hotel_cost": hotel_cost,
            "hotel_name": hotel_name,
            "hotel_price_per_night": hotel_cost_per_night,
            "num_rooms": num_rooms,
            "num_nights": num_nights,
            "activities": total_activity_cost,
            "activity_cost": total_activity_cost,
            "food": total_food,
            "food_cost": total_food,
            "transport": total_transport,
            "transport_cost": total_transport,
            "miscellaneous": misc_cost,
            "total_estimated": total_estimated,
            "total_budget": total_budget,
            "remaining": remaining,
            "per_person": round(per_person, 2),
            "within_budget": within_budget,
            "hotels_available": hotels_available,
            "num_people": num_people,
            "currency": "INR",
        }

        status = "within budget" if within_budget else "over budget"
        summary = (
            f"Total estimated: ₹{total_estimated:,.0f} | "
            f"Budget: ₹{total_budget:,.0f} | "
            f"Per person: ₹{per_person:,.0f} | "
            f"Status: {status}"
        )

        return ToolResult(success=True, data=breakdown, summary=summary)


class CalculatorTool(BaseTool):
    """
    General-purpose calculator tool for arithmetic and percentage calculations.
    Safely evaluates expressions like '17.5% of 84000', '25 * 400 + 150', etc.
    """
    name = "calculator"
    description = "Perform mathematical and percentage calculations (e.g. '17.5% of 84000', '250 * 12')"
    category = "CALCULATOR"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        await self._simulate_latency(0.3, cancel_event)
        raw_expr = str(params.get("expression") or params.get("query") or "").strip()
        if not raw_expr:
            return ToolResult(
                success=False,
                error="No mathematical expression provided",
                summary="Calculation failed: empty expression",
            )

        try:
            result = self.evaluate_expression(raw_expr)
            formatted = f"{result:,.2f}".rstrip("0").rstrip(".") if isinstance(result, float) else f"{result:,}"
            summary = f"Calculated: {raw_expr} = {formatted}"
            return ToolResult(
                success=True,
                data={
                    "expression": raw_expr,
                    "result": result,
                    "formatted": formatted,
                },
                summary=summary,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Calculation error: {e}",
                summary=f"Failed to calculate '{raw_expr}': {e}",
            )

    @staticmethod
    def evaluate_expression(expr: str) -> float | int:
        """Safely compute percentage and arithmetic expressions without eval()."""
        clean = expr.lower().strip()
        # Handle 'X% of Y' pattern (e.g. '17.5% of 84000', '17.5 percent of 84,000')
        percent_match = re.search(r"([\d\.]+)\s*(?:%|percent)\s*of\s*([\d,\.]+)", clean)
        if percent_match:
            pct = float(percent_match.group(1))
            base = float(percent_match.group(2).replace(",", ""))
            val = (pct / 100.0) * base
            return int(val) if val.is_integer() else round(val, 4)

        # Handle 'calculate/what is' prefixes and strip currency symbols
        clean = re.sub(r"^(?:calculate|what is|compute)\s*", "", clean)
        clean = re.sub(r"[₹$,rs\.?]", "", clean).strip()

        # Handle simple inline percentages like '84000 * 17.5%'
        clean = re.sub(r"([\d\.]+)\s*%", r"(\1/100)", clean)

        # Sanitize for safe AST evaluation: only allow digits, parens, and standard operators
        allowed_chars = set("0123456789+-*/.() \t\n")
        if not all(c in allowed_chars for c in clean):
            raise ValueError("Expression contains invalid characters")

        import ast
        import operator

        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def _eval_node(node: ast.AST) -> float | int:
            if isinstance(node, ast.Expression):
                return _eval_node(node.body)
            elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            elif isinstance(node, ast.BinOp) and type(node.op) in ops:
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                return ops[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp) and type(node.op) in ops:
                operand = _eval_node(node.operand)
                return ops[type(node.op)](operand)
            raise ValueError("Unsupported mathematical operation")

        tree = ast.parse(clean, mode="eval")
        res = _eval_node(tree)
        return int(res) if isinstance(res, float) and res.is_integer() else round(res, 4)

