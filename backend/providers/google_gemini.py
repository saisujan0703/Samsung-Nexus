"""
NEXUS Google Gemini LLM Provider.

Integrates Google Gemini via HTTP API (using httpx) for planning, interruption
classification, structured responses, and multimodal analysis.
Supports fallback to MockProvider if API key is not configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator
from datetime import datetime, timezone
import httpx

from backend.config import Settings, settings
from backend.providers.base import (
    Classification,
    LLMProvider,
    Message,
    MockProvider,
    PlanSpec,
)
from backend.tools.web_search import format_search_evidence, search_web

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(LLMProvider):
    """
    Google Gemini Provider for NEXUS.
    Communicates asynchronously with Gemini API endpoints using httpx.
    """

    name = "gemini"

    FALLBACK_MODELS = [
        "gemini-3.8-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-flash-latest",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        fallback_to_mock: bool = True,
    ) -> None:
        selected_model = (model or settings.GEMINI_MODEL or "gemini-3.8-flash").strip()
        selected_api_key = (settings.GOOGLE_API_KEY if api_key is None else api_key).strip()

        if not selected_model:
            raise ValueError("Missing required configuration: GEMINI_MODEL must be set to a non-empty model name.")

        self.api_key = selected_api_key
        self.model = selected_model
        self.active_model = selected_model
        self.fallback_to_mock = fallback_to_mock
        self._fallback_provider = MockProvider()

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def _post_gemini(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make an async authenticated request to Google Gemini API with exponential backoff retries and model resilience."""
        if not self.is_configured:
            raise ValueError(
                "GOOGLE_API_KEY is not set. Please set GOOGLE_API_KEY in .env or environment variables."
            )

        # Build list of models to try: active/configured model first, followed by fallbacks
        models_to_try: list[str] = [self.active_model]
        for fb in self.FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        headers = {"Content-Type": "application/json"}
        last_error = ""

        async with httpx.AsyncClient(timeout=120.0) as client:
            for model_candidate in models_to_try:
                url = f"{GEMINI_API_URL}/{model_candidate}:{endpoint}?key={self.api_key}"
                max_attempts = 3

                for attempt in range(1, max_attempts + 1):
                    try:
                        response = await client.post(url, headers=headers, json=payload)
                        if response.status_code == 200:
                            if self.active_model != model_candidate:
                                logger.info(
                                    f"Switched active Gemini model from {self.active_model} to {model_candidate}"
                                )
                                self.active_model = model_candidate
                            return response.json()

                        resp_text = response.text
                        last_error = f"Gemini API error ({model_candidate}, status {response.status_code}): {resp_text}"

                        # Quota exhaustion for this specific model: switch immediately to next candidate
                        if response.status_code == 429 and ("RESOURCE_EXHAUSTED" in resp_text or "Quota" in resp_text):
                            logger.warning(
                                f"Gemini model {model_candidate} quota exhausted; switching to next available candidate..."
                            )
                            break

                        # Model deprecated or unavailable: move to next candidate model
                        if response.status_code == 404:
                            logger.warning(
                                f"Gemini model {model_candidate} not found / deprecated; switching to next available candidate..."
                            )
                            break

                        # Transient retryable status code (408, 429 burst rate limit, 500, 502, 503, 504)
                        if response.status_code in {408, 429, 500, 502, 503, 504} and attempt < max_attempts:
                            base_delay = 1.0 if attempt == 1 else 2.0
                            jitter = (attempt * 0.1)
                            delay = base_delay + jitter
                            logger.warning(
                                f"Gemini model {model_candidate} transient error ({response.status_code}, attempt {attempt}/{max_attempts}). Retrying in {delay:.2f}s..."
                            )
                            await asyncio.sleep(delay)
                            continue

                        # If transient error persists across all attempts on this model, raise error
                        if response.status_code in {408, 429, 500, 502, 503, 504}:
                            raise RuntimeError(last_error)

                        # Permanent non-retryable error
                        raise RuntimeError(last_error)

                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        last_error = f"Gemini network error ({model_candidate}, attempt {attempt}/{max_attempts}): {exc}"
                        if attempt < max_attempts:
                            delay = 1.0 if attempt == 1 else 2.0
                            logger.warning(f"{last_error}. Retrying in {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            continue
                        logger.warning(f"{last_error}. Moving to next model candidate...")
                        break

            raise RuntimeError(last_error or "All Gemini model candidates failed after retries.")

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

        prompt = f"""You are the interruption classifier for SURU AI, an interruptible real-time agent.
Classify the user's interruption into exactly ONE category from: {categories}.

Current Goal / Context:
{context}

User Utterance:
"{text}"

Category definitions:
- BACKCHANNEL: acknowledgment like "ok", "yeah", "mhm", "cool"
- QUESTION: inquiring about status, budget, decisions like "why hotel X?", "what is the budget?"
- CORRECTION: correcting details like "actually 4 people", "I meant next week"
- CONSTRAINT_CHANGE: modifying budget, people, walking, preferences like "avoid walking", "parents joining", "change budget to ₹20,000"
- GOAL_CHANGE: modifying what to achieve like "find hostels instead of luxury hotels"
- TASK_CANCELLATION: cancelling a task like "stop searching hotels", "cancel the activity"
- NEW_GOAL: completely changing topic like "forget the trip, help with an interview"

Respond strictly with a JSON object:
{{
  "category": "CATEGORY_NAME",
  "confidence": 0.95,
  "reasoning": "brief explanation",
  "details": {{"budget": 20000}}
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        try:
            data = await self._post_gemini("generateContent", payload)
            raw_json = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:]
            if raw_json.startswith("```"):
                raw_json = raw_json[3:]
            if raw_json.endswith("```"):
                raw_json = raw_json[:-3]
            parsed = json.loads(raw_json.strip())
            extracted_details = self._extract_constraint_changes(text)
            parsed_details = parsed.get("details") if isinstance(parsed.get("details"), dict) else {}
            merged_details = {**extracted_details, **parsed_details}
            return Classification(
                category=parsed.get("category", "CONSTRAINT_CHANGE"),
                confidence=float(parsed.get("confidence", 0.9)),
                reasoning=parsed.get("reasoning", "Gemini classification"),
                details=merged_details,
            )
        except Exception as e:
            logger.warning(f"Gemini classify failed: {e}, falling back to mock")
            return await self._fallback_provider.classify(text, categories, context)

    async def determine_intent(self, text: str, context: str = "", current_date: str = "") -> dict[str, Any]:
        """Classify the user's intent to decide between direct response, web search grounding, or multi-step DAG execution."""
        if not self.is_configured:
            return await self._fallback_provider.determine_intent(text, context, current_date=current_date)

        date_prompt = f"Today's Real-World Date: {current_date}\n" if current_date else ""
        prompt = f"""You are the intent classifier and routing engine for SURU AI.
{date_prompt}Analyze the user request and determine the query category, whether it requires fresh real-time web search/grounding, whether it requires structured sports fixtures, and whether it requires a multi-step task graph (DAG).

Categories:
- SPORTS_FIXTURE_QUERY: Queries asking for CURRENT, LIVE, or UPCOMING sports fixtures/matches/schedules (e.g. today, tonight, tomorrow, this weekend, next week, or specific near-term dates like 'matches on September 28').
  NOTE: Historical tournament questions, past season winners, history of a competition, or complete historical season archives (e.g. "Who won IPL 2025?", "Complete schedule of IPL 2025", "History of the World Cup") belong in CURRENT_INFORMATION (with needs_grounding: true) or DIRECT_KNOWLEDGE, NOT SPORTS_FIXTURE_QUERY!
  For SPORTS_FIXTURE_QUERY, extract:
  "sports_params": {{
    "sport": "soccer/basketball/cricket/etc or null",
    "competition": "competition or tournament name or null",
    "team": "team or club or country name or null",
    "date_from": "YYYY-MM-DD or null (e.g. for explicit dates like 'September 28' return '2026-09-28', for relative dates resolve relative to Today's Real-World Date)",
    "date_to": "YYYY-MM-DD or null (e.g. for ranges like 'between Sep 28 and Sep 30' return '2026-09-30', for weekends return Sunday)",
    "status": "ALL (default for 'today', 'tonight', 'matches today', 'which teams play', 'scheduled') | LIVE | FINISHED | UPCOMING"
  }}
- CURRENT_INFORMATION: ANY query whose answer depends on current, recent, historical, or evolving real-world information that requires factual lookup or web evidence.
  Examples:
  * Complete schedules, fixtures, or outcomes of past seasons/tournaments (e.g. "IPL 2025 complete schedule", "2024 Copa America results").
  * Words like "currently", "today", "yesterday", "latest", "recent", "now", "this week", "this month", "current", "as of [date]", "last night".
  * Questions about sports statistics, match scores/results, tournament winners, current world leaders/officials, ongoing news, weather, or records that change over time.
- DIRECT_KNOWLEDGE: Timeless factual, historical, scientific, or conceptual knowledge (e.g. "What is photosynthesis?", "Who was the first president of the USA?", "Explain recursion", "Difference between TCP and UDP").
- CODING: Programming explanations, code writing, algorithms, software architecture, debugging (e.g. "Explain ArrayList vs LinkedList", "Write Java code to reverse a list").
- CALCULATION: Mathematical operations, arithmetic, percentages, unit conversions (e.g. "Calculate 17.5% of 84000").
- MULTI_STEP_AGENT_TASK: Complex multi-step planning, comparing multiple options, multi-criteria travel itineraries (e.g. "Plan a 5-day Japan trip under ₹1.5 lakh").
- FOLLOW_UP: Contextual follow-up question continuing recent dialogue.

TEMPORAL INTENT PRINCIPLE:
If the user specifies an explicit historical year, season, or past date (e.g. 2025, 2024, last year), you MUST preserve that temporal intent. Never replace or redirect their requested historical inquiry with the current date/season!

Context:
{context}

User Request:
"{text}"

Respond strictly with JSON:
{{
  "category": "CURRENT_INFORMATION",
  "needs_grounding": true,
  "needs_dag": false,
  "sports_params": null,
  "reasoning": "brief explanation"
}}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        try:
            data = await self._post_gemini("generateContent", payload)
            raw_json = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:]
            if raw_json.startswith("```"):
                raw_json = raw_json[3:]
            if raw_json.endswith("```"):
                raw_json = raw_json[:-3]
            parsed = json.loads(raw_json.strip())
            category = parsed.get("category", "DIRECT_KNOWLEDGE")
            needs_dag = parsed.get("needs_dag", category == "MULTI_STEP_AGENT_TASK")
            needs_grounding = parsed.get("needs_grounding", category == "CURRENT_INFORMATION")
            sports_params = parsed.get("sports_params")

            if category == "SPORTS_FIXTURE_QUERY":
                from backend.tools.date_parser import parse_date_intent
                d_from, d_to = parse_date_intent(text, current_date)
                if not sports_params:
                    sports_params = {}
                if d_from and not sports_params.get("date_from"):
                    sports_params["date_from"] = d_from
                if d_to and not sports_params.get("date_to"):
                    sports_params["date_to"] = d_to
                if not sports_params.get("timezone"):
                    sports_params["timezone"] = "Asia/Kolkata"
                if not sports_params.get("status"):
                    sports_params["status"] = "ALL"

            return {
                "category": category,
                "needs_grounding": bool(needs_grounding),
                "needs_dag": bool(needs_dag),
                "sports_params": sports_params,
                "reasoning": parsed.get("reasoning", "Gemini intent classification"),
            }
        except Exception as e:
            logger.warning(f"Gemini intent classification failed: {e}; applying heuristic routing")
            text_lower = text.lower().strip()
            is_multi_step = any(w in text_lower for w in ["plan a", "plan my", "trip to", "itinerary", "vacation to", "tour to", "travel to"]) and any(w in text_lower for w in ["day", "days", "budget", "hotel", "flight", "trip"])
            if is_multi_step:
                return {
                    "category": "MULTI_STEP_AGENT_TASK",
                    "needs_grounding": False,
                    "needs_dag": True,
                    "reasoning": "Heuristic routing fallback",
                }
            from backend.tools.date_parser import parse_date_intent
            d_from, d_to = parse_date_intent(text, current_date)
            sports_signals = [
                "match", "matches", "fixture", "fixtures", "schedule", "scheduled", "play next",
                "plays next", "play today", "playing today", "play tonight", "live right now",
                "live match", "live matches", "who plays", "teams play", "which teams"
            ]
            if any(s in text_lower for s in sports_signals) or (
                any(w in text_lower for w in ["play", "game", "games"]) and
                (d_from is not None or any(w in text_lower for w in ["today", "tonight", "tomorrow", "this weekend", "next", "live"]))
            ):
                return await self._fallback_provider.determine_intent(text, context, current_date=current_date)

            temporal_signals = [
                "currently", "today", "yesterday", "latest", "recent", "now",
                "this week", "this month", "current", "as of", "who won", "score",
                "goals", "centuries", "champion", "president", "prime minister",
                "weather", "news", "last night", "results"
            ]
            needs_grounding = any(w in text_lower for w in temporal_signals)
            category = "CURRENT_INFORMATION" if needs_grounding else "DIRECT_KNOWLEDGE"
            return {
                "category": category,
                "needs_grounding": needs_grounding,
                "needs_dag": False,
                "reasoning": "Heuristic routing fallback",
            }

    async def generate_direct_response(
        self,
        text: str,
        context: str = "",
        use_grounding: bool = False,
        current_date: str = "",
    ) -> str:
        """Generate a direct conversational response with fresh web search grounding when requested."""
        if not self.is_configured:
            if self.fallback_to_mock:
                return await self._fallback_provider.generate_direct_response(
                    text, context, use_grounding=use_grounding, current_date=current_date
                )
            return "Google API key is not configured. Please set GOOGLE_API_KEY in .env."

        # Obtain fresh runtime date if not supplied
        if not current_date:
            current_date = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")

        search_evidence = ""
        if use_grounding:
            try:
                search_results = await search_web(text, max_results=6, current_date_str=current_date)
                search_evidence = format_search_evidence(search_results, text, as_of_date=current_date)
            except Exception as e:
                logger.warning(f"Web search retrieval error: {e}")
                search_evidence = f"[Web search retrieval temporarily unavailable as of {current_date}]"

        grounding_instruction = ""
        if search_evidence:
            grounding_instruction = f"""
LIVE RETRIEVED WEB EVIDENCE:
{search_evidence}

CRITICAL GROUNDING & TEMPORAL INSTRUCTIONS:
1. Current Runtime Date: {current_date}. Note that your pretrained knowledge cutoff is in the past compared to today's date!
2. You MUST prioritize the live retrieved web evidence above over any outdated pre-training knowledge.
3. TEMPORAL INTENT PRESERVATION: If the user explicitly asks about a historical year, season, or past period (e.g. 2025, 2024, last year, 2018 World Cup), answer that specific requested period! NEVER replace or redirect their requested historical inquiry to the current season/year, and never say "the current season is 2026, if you want historical details let me know". If they asked for 2025, ANSWER 2025.
4. RECENCY RULE: For queries about current/evolving facts (e.g. latest statistics, records, current leaders, recent match outcomes), newer evidence takes precedence over older sources. State the newest verified milestone or figure as of recent date or {current_date}.
5. TASK COMPLETION & COMPLETENESS REQUIREMENT:
   - When the user explicitly requests a "complete", "full", "entire", or "all" schedule, tournament fixtures, list, or dataset:
     * When authoritative archive records or search evidence are provided, EXTRACT AND PROVIDE THE COMPLETE, COMPREHENSIVE SCHEDULE/FIXTURES in a well-structured Markdown table or organized list (e.g. grouped by stage or ordered by match number with Date, Matchup, Venue, and Result/Status). If a tournament underwent rescheduling, reflect the final authoritative/revised schedule from the archive.
     * Only if the authoritative sources truly lack the schedule after search should you state that it could not be retrieved.
     * CRITICAL RULE: NEVER silently replace a requested complete schedule or dataset with a high-level summary, tournament dates, overview of rules/format, number of matches, a few selected fixtures, an offer to provide specific team/playoff schedules, or external links to other pages. Deliver the complete data from the authoritative records.
   - For factual, conceptual, coding, comparison, calculation, or explanation questions, answer directly and thoroughly.
   - Never answer with evasive commentary about what the user could have asked.
6. If the retrieved evidence does not contain sufficient details, state honestly what could be verified rather than fabricating.
"""
        else:
            grounding_instruction = f"""Current Real-World Date: {current_date}.
TEMPORAL INTENT & TASK COMPLETION:
- If the user asks for a historical period, specific year/season (e.g. 2025, 2024), or event, fulfill that exact requested period. Never redirect them to the current date/season.
- COMPLETENESS: When the user explicitly requests a "complete", "full", "entire", or "all" schedule, list, or dataset, provide the complete structured data, or honestly state if the full dataset is unavailable. NEVER substitute a complete request with a mere summary, tournament overview, links, or offer to give team subsets.
- Answer directly, accurately, and concisely without evasive commentary."""

        prompt = f"""You are SURU AI, a helpful, intelligent, real-time interruptible AI assistant.
{grounding_instruction}

Context and Previous Conversation:
{context}

User Request:
"{text}"
"""
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
        }

        try:
            data = await self._post_gemini("generateContent", payload)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except RuntimeError as e:
            err_str = str(e).lower()
            logger.error(f"Gemini direct response failed after all retries and fallback models: {e}")
            if "quota" in err_str or "429" in err_str or "resource_exhausted" in err_str:
                return "Gemini service quota is currently exhausted. Please try again later or verify your API quota."
            if "503" in err_str or "unavailable" in err_str or "demand" in err_str:
                return "Gemini is temporarily experiencing high demand or unavailability. Please try again in a few moments."
            return "I couldn't process your request due to an AI provider service error. Please try again in a moment."
        except Exception as e:
            logger.error(f"Gemini direct response unexpected error: {e}")
            return "I received an invalid response from the AI provider. Please try again."

    async def create_plan(self, goal: str, constraints: dict[str, Any], context: str = "") -> PlanSpec:
        """Generate structured task graph plan."""
        if not self.is_configured:
            if self.fallback_to_mock:
                return await self._fallback_provider.create_plan(goal, constraints, context)
            raise ValueError("GOOGLE_API_KEY not configured")

        prompt = f"""You are the task planner for SURU AI. Generate a structured execution plan.
Goal: {goal}
Constraints: {json.dumps(constraints)}
Context: {context}

Available Tools:
- destination_search: {{"city": str, "max_walking": str, "budget_per_person": int}}
- hotel_search: {{"city": str, "max_price_per_night": int, "num_nights": int, "num_rooms": int}}
- activity_search: {{"city": str, "max_walking": str, "max_cost_per_person": int}}
- budget_calculator: {{"total_budget": int, "num_people": int, "num_nights": int}}
- calculator: {{"expression": str}}
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

        parts: list[dict[str, Any]] = [{"text": prompt or "Analyze this image and describe what is shown."}]
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

        prompt = f"""You are SURU AI, an interruptible real-time agent.
Summarize the results of the completed tasks in a natural, concise, conversational tone.
Goal: {goal}
Task Results: {json.dumps(task_results)}
Context: {context}

CRITICAL ACCURACY GUIDELINES:
1. Use ONLY the exact monetary values present in the task results (specifically total_estimated in budget_calculator). Never invent astronomical, billion-rupee, or fictitious numbers.
2. If hotel search returned 0 hotels, state clearly that no hotels were found within the current budget and suggest adjusting the hotel budget, dates, or accommodation category. Never fabricate hotel names.
3. Keep the response concise, realistic, and directly addressing the user's goal.
"""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        try:
            data = await self._post_gemini("generateContent", payload)
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Gemini response generation failed: {e}, falling back to mock")
            return await self._fallback_provider.generate_response(task_results, goal, context)

