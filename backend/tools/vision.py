"""
NEXUS Vision Tool — Image analysis via multimodal LLM or mock.
"""

from __future__ import annotations

import asyncio
import base64
from typing import Any

from backend.tools.base import BaseTool, ToolResult


class VisionAnalysisTool(BaseTool):
    name = "vision_analysis"
    description = "Analyse an uploaded image to extract information relevant to the current task"
    category = "VISION"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        image_data = params.get("image_data", "")
        prompt = params.get("prompt", "Describe this image and extract relevant information.")
        context = params.get("context", "")

        await self._simulate_latency(2.0, cancel_event)

        # For the hackathon mock, return a realistic analysis
        # In production, this would call a multimodal LLM
        analysis = self._mock_analysis(prompt, context)

        return ToolResult(
            success=True,
            data={
                "analysis": analysis["description"],
                "extracted_info": analysis["extracted"],
                "relevance": analysis["relevance"],
                "suggestions": analysis["suggestions"],
            },
            summary=analysis["summary"],
        )

    def _mock_analysis(self, prompt: str, context: str) -> dict[str, Any]:
        """Generate a realistic mock analysis based on context."""
        context_lower = context.lower()

        if "hotel" in context_lower or "room" in context_lower or "stay" in context_lower:
            return {
                "description": "The image shows a hotel room or property. It appears to be a well-maintained property with modern amenities. The room features clean bedding, air conditioning, and adequate lighting.",
                "extracted": {
                    "type": "hotel",
                    "estimated_stars": 3,
                    "visible_amenities": ["air_conditioning", "clean_bedding", "desk", "wifi"],
                    "condition": "good",
                    "estimated_price_range": "₹2,000 - ₹3,500 per night",
                    "accessibility": "moderate",
                },
                "relevance": "This hotel appears suitable for the planned trip. It's within a moderate price range and seems well-maintained.",
                "suggestions": [
                    "Check online reviews for recent guest experiences",
                    "Verify accessibility features if needed",
                    "Compare price with other options in the search results",
                ],
                "summary": "Analysed hotel image: 3-star property, good condition, estimated ₹2,000-3,500/night",
            }
        elif "food" in context_lower or "restaurant" in context_lower:
            return {
                "description": "The image shows a restaurant or food establishment. The setting appears clean with a pleasant ambiance.",
                "extracted": {
                    "type": "restaurant",
                    "cuisine": "South Indian",
                    "price_range": "budget to mid-range",
                    "ambiance": "casual dining",
                },
                "relevance": "This restaurant could be a dining option for the trip.",
                "suggestions": ["Check for vegetarian options", "Verify location proximity to planned stays"],
                "summary": "Analysed restaurant image: casual South Indian dining, budget-friendly",
            }
        else:
            return {
                "description": "The image shows a location or scene. It appears to be well-maintained and potentially relevant to travel planning.",
                "extracted": {
                    "type": "general",
                    "condition": "good",
                    "notable_features": ["clean", "accessible", "well-lit"],
                },
                "relevance": "This could be relevant to the current planning context.",
                "suggestions": ["Consider adding this location to the itinerary", "Check reviews and ratings"],
                "summary": "Analysed image: general location, good condition",
            }
