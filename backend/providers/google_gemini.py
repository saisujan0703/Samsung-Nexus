"""
NEXUS Google Gemini LLM Provider.

Integrates Google Gemini via HTTP API (using httpx) for planning, interruption
classification, structured responses, and multimodal analysis.
Supports fallback to MockProvider if API key is not configured.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator
import httpx

from backend.config import settings
from backend.providers.base import (
    Classification,
    LLMProvider,
    Message,
    MockProvider,
    PlanSpec,
)

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    """
    Google Gemini Provider for NEXUS.
    Communicates asynchronously with Gemini API endpoints using httpx.
    """

    name = "gemini"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-flash",
        fallback_to_mock: bool = True,
    ) -> None:
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model = model
        self.fallback_to_mock = fallback_to_mock
        self._fallback_provider = MockProvider()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def _post_gemini(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make an async authenticated request to Google Gemini API."""
        if not self.is_configured:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Please set GOOGLE_API_KEY in .env or environment variables."
            )

        url = f"{GEMINI_API_URL}/{self.model}:{endpoint}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Gemini API error (status {response.status_code}): {response.text}"
                )
            return response.json()

    async def generate(self, messages: list[Message], **kwargs: Any) -> str:
        if not self.is_configured:
            if self.fallback_to_mock:
                return await self._fallback_provider.generate(messages, **kwargs)
            raise ValueError("GOOGLE_API_KEY not configured")

        contents = []
        for msg in messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.content}]})

        payload = {"contents": contents}
        data = await self._post_gemini("generateContent", payload)
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            return ""

    async def generate_stream(self, messages: list[Message], **kwargs: Any) -> AsyncIterator[str]:
        if not self.is_configured:
            if self.fallback_to_mock:
                async for chunk in self._fallback_provider.generate_stream(messages, **kwargs):
                    yield chunk
                return
            raise ValueError("GOOGLE_API_KEY not configured")

        full_text = await self.generate(messages, **kwargs)
        for word in full_text.split():
            yield word + " "

    async def classify(self, text: str, categories: list[str], context: str = "") -> Classification:
        """Classify user utterance into one of the designated interruption categories."""
        if not self.is_configured:
            if self.fallback_to_mock:
                return await self._fallback_provider.classify(text, categories, context)
            raise ValueError("GOOGLE_API_KEY not configured")

        prompt = f"""You are the interruption classifier for NEXUS, an interruptible real-time agent.
Classify the user's interruption into exactly ONE category from: {categories}.

Current Goal / Context:
{context}

User Utterance:
"{text}"

Category definitions:
- BACKCHANNEL: acknowledgment like "ok", "yeah", "mhm", "cool"
- QUESTION: inquiring about status, budget, decisions like "why hotel X?", "what is the budget?"
- CORRECTION: correcting details like "actually 4 people", "I meant next week"
- CONSTRAINT_CHANGE: modifying budget, people, walking, preferences like "avoid walking", "parents joining"
- GOAL_CHANGE: modifying what to achieve like "find hostels instead of luxury hotels"
- TASK_CANCELLATION: cancelling a task like "stop searching hotels", "cancel the activity"
- NEW_GOAL: completely changing topic like "forget the trip, help with an interview"

Respond strictly with a JSON object:
{{
  "category": "CATEGORY_NAME",
  "confidence": 0.95,
  "reasoning": "brief explanation",
  "details": {{}}
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        try:
            data = await self._post_gemini("generateContent", payload)
            raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_json)
            return Classification(
                category=parsed.get("category", "CONSTRAINT_CHANGE"),
                confidence=float(parsed.get("confidence", 0.9)),
                reasoning=parsed.get("reasoning", "Gemini classification"),
                details=parsed.get("details", {}),
            )
        except Exception as e:
            logger.warning(f"Gemini classify failed: {e}, falling back to mock")
            return await self._fallback_provider.classify(text, categories, context)

    async def create_plan(self, goal: str, constraints: dict[str, Any], context: str = "") -> PlanSpec:
        """Generate structured task graph plan."""
        if not self.is_configured:
            if self.fallback_to_mock:
                return await self._fallback_provider.create_plan(goal, constraints, context)
            raise ValueError("GOOGLE_API_KEY not configured")

        prompt = f"""You are the task planner for NEXUS. Generate a structured execution plan.
Goal: {goal}
Constraints: {json.dumps(constraints)}
Context: {context}

Available Tools:
- destination_search: {{"city": str, "max_walking": str, "budget_per_person": int}}
- hotel_search: {{"city": str, "max_price_per_night": int, "num_nights": int, "num_rooms": int}}
- activity_search: {{"city": str, "max_walking": str, "max_cost_per_person": int}}
- budget_calculator: {{"total_budget": int, "num_people": int, "num_nights": int}}
- database_query: {{"query_type": str, "city": str}}

Respond strictly with JSON matching:
{{
  "goal_summary": "...",
  "constraints": {{...}},
  "tasks": [
    {{
      "id": "unique_short_id",
      "name": "Human-readable name",
      "description": "...",
      "tool": "tool_name",
      "input": {{...}},
      "dependencies": ["dependency_task_id"],
      "priority": 10
    }}
  ]
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        try:
            data = await self._post_gemini("generateContent", payload)
            raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_json)
            return PlanSpec(
                goal_summary=parsed.get("goal_summary", goal),
                constraints=parsed.get("constraints", constraints),
                tasks=parsed.get("tasks", []),
            )
        except Exception as e:
            logger.warning(f"Gemini planning failed: {e}, falling back to mock")
            return await self._fallback_provider.create_plan(goal, constraints, context)

    async def analyze_image(self, image_data: str, prompt: str) -> str:
        """Multimodal image analysis using Gemini vision capabilities."""
        if not self.is_configured:
            if self.fallback_to_mock:
                return await self._fallback_provider.analyze_image(image_data, prompt)
            raise ValueError("GOOGLE_API_KEY not configured")

        parts: list[dict[str, Any]] = [{"text": prompt}]
        # If image_data is base64 encoded
        if "," in image_data:
            mime_part, b64_data = image_data.split(",", 1)
            mime_type = "image/jpeg"
            if "png" in mime_part:
                mime_type = "image/png"
            elif "webp" in mime_part:
                mime_type = "image/webp"
            parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})
        elif len(image_data) > 100:
            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": image_data}})

        payload = {"contents": [{"parts": parts}]}
        try:
            data = await self._post_gemini("generateContent", payload)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini image analysis failed: {e}, falling back to mock")
            return await self._fallback_provider.analyze_image(image_data, prompt)

    async def generate_response(self, task_results: list[dict], goal: str, context: str = "") -> str:
        if not self.is_configured:
            if self.fallback_to_mock:
                return await self._fallback_provider.generate_response(task_results, goal, context)
            raise ValueError("GOOGLE_API_KEY not configured")

        prompt = f"""You are NEXUS, an interruptible real-time agent.
Summarize the results of the completed tasks in a natural, concise, conversational tone.
Goal: {goal}
Task Results: {json.dumps(task_results)}
Context: {context}
"""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            data = await self._post_gemini("generateContent", payload)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return await self._fallback_provider.generate_response(task_results, goal, context)
