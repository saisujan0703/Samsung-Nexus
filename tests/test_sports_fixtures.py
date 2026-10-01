"""
SURU AI — Generic Sports Fixtures Architecture Regression & Verification Tests.

Tests generic sports intent detection, dynamic parameter extraction,
timezone conversion (including midnight boundary handling), structured normalization,
live/upcoming/finished status resolution, web fallback handling, and end-to-end orchestrator emission.
"""

import asyncio
from datetime import datetime, timezone
import pytest
from zoneinfo import ZoneInfo

from backend.agent.orchestrator import Orchestrator
from backend.providers.base import MockProvider
from backend.realtime.events import EventBus, EventType
from backend.tools.sports import SportsTool, resolve_timezone, normalize_status


@pytest.mark.asyncio
async def test_sports_intent_detection_across_varied_queries():
    """Verify generic intent detection and parameter extraction across multiple sports and phrasings."""
    provider = MockProvider()

    test_cases = [
        (
            "Which teams play UEFA Nations League today?",
            "SPORTS_FIXTURE_QUERY",
            {"sport": "soccer", "competition": "uefa nations league", "status": "ALL"},
        ),
        (
            "What football matches are today?",
            "SPORTS_FIXTURE_QUERY",
            {"sport": "soccer", "status": "ALL"},
        ),
        (
            "What Champions League games are tonight?",
            "SPORTS_FIXTURE_QUERY",
            {"competition": "champions league", "status": "ALL"},
        ),
        (
            "When does Barcelona play next?",
            "SPORTS_FIXTURE_QUERY",
            {"team": "barcelona", "status": "UPCOMING"},
        ),
        (
            "What are India's next cricket matches?",
            "SPORTS_FIXTURE_QUERY",
            {"sport": "cricket", "team": "india", "status": "UPCOMING"},
        ),
        (
            "What matches are live right now?",
            "SPORTS_FIXTURE_QUERY",
            {"status": "LIVE"},
        ),
        (
            "Show me tomorrow's football fixtures.",
            "SPORTS_FIXTURE_QUERY",
            {"sport": "soccer", "status": "UPCOMING"},
        ),
    ]

    for query, expected_cat, expected_param_subset in test_cases:
        intent = await provider.determine_intent(query)
        assert intent["category"] == expected_cat, f"Failed for query: {query}"
        params = intent.get("sports_params", {})
        for key, val in expected_param_subset.items():
            if val is not None:
                assert params.get(key) == val, f"Param {key} mismatch for {query}: expected {val}, got {params.get(key)}"


@pytest.mark.asyncio
async def test_non_sports_queries_not_misclassified():
    """Verify non-sports queries with temporal words are NOT misclassified as sports fixtures."""
    provider = MockProvider()

    non_sports = [
        "What is the capital of Australia?",
        "Who is the current prime minister of the UK?",
        "Explain ArrayList vs LinkedList in Java",
        "Calculate 15% of 8500",
        "Plan a 3-day Chennai trip under 20000",
    ]

    for q in non_sports:
        intent = await provider.determine_intent(q)
        assert intent["category"] != "SPORTS_FIXTURE_QUERY", f"Misclassified non-sports query: {q}"


def test_timezone_conversion_and_midnight_boundary():
    """
    Verify timezone conversion handles day transitions accurately:
    Kickoff at 20:45 CET (18:45 UTC) on September 29 must convert to:
    - September 30 at 12:15 AM IST (Asia/Kolkata)
    - September 29 at 11:45 AM PDT (America/Los_Angeles)
    """
    raw_utc_str = "2026-09-29T18:45:00Z"
    dt_utc = datetime.fromisoformat(raw_utc_str.replace("Z", "+00:00"))

    # Convert to Asia/Kolkata (+05:30)
    ist_tz = resolve_timezone("Asia/Kolkata")
    dt_ist = dt_utc.astimezone(ist_tz)
    assert dt_ist.strftime("%Y-%m-%d") == "2026-09-30"
    assert dt_ist.strftime("%I:%M %p").lstrip("0") == "12:15 AM"

    # Convert to America/Los_Angeles (-07:00 in daylight savings)
    pdt_tz = resolve_timezone("America/Los_Angeles")
    dt_pdt = dt_utc.astimezone(pdt_tz)
    assert dt_pdt.strftime("%Y-%m-%d") == "2026-09-29"
    assert dt_pdt.strftime("%I:%M %p").lstrip("0") == "11:45 AM"


def test_status_normalization():
    """Verify vendor status strings normalize to canonical SURU enum values."""
    assert normalize_status("post", "Full Time") == "FINISHED"
    assert normalize_status("post", "Final") == "FINISHED"
    assert normalize_status("in", "First Half") == "LIVE"
    assert normalize_status("in", "Halftime") == "HALFTIME"
    assert normalize_status("pre", "Scheduled") == "SCHEDULED"
    assert normalize_status("pre", "Postponed") == "POSTPONED"
    assert normalize_status("pre", "Cancelled") == "CANCELLED"


def test_structured_normalization_espn_schema():
    """Verify raw ESPN event dictionary normalizes cleanly into SURU internal schema."""
    raw_event = {
        "id": "715890",
        "date": "2026-09-29T18:45:00Z",
        "name": "Estonia at Bulgaria",
        "competitions": [
            {
                "league": {"name": "UEFA Nations League"},
                "stage": {"name": "League C"},
                "venue": {"fullName": "Hristo Botev Stadium"},
                "competitors": [
                    {
                        "homeAway": "home",
                        "score": "1",
                        "team": {"displayName": "Bulgaria", "abbreviation": "BUL", "logo": "https://example.com/bul.png"},
                    },
                    {
                        "homeAway": "away",
                        "score": "0",
                        "team": {"displayName": "Estonia", "abbreviation": "EST", "logo": "https://example.com/est.png"},
                    },
                ],
            }
        ],
        "status": {
            "type": {"state": "in", "description": "Second Half", "shortDetail": "62'"},
            "displayClock": "62",
        },
    }

    normalized = SportsTool._normalize_espn_event(raw_event, "Soccer", ZoneInfo("Asia/Kolkata"))
    assert normalized is not None
    assert normalized["id"] == "715890"
    assert normalized["competition"] == "UEFA Nations League"
    assert normalized["stage"] == "League C"
    assert normalized["status"] == "LIVE"
    assert normalized["elapsed_time"] == "62'"
    assert normalized["home_team"]["name"] == "Bulgaria"
    assert normalized["away_team"]["name"] == "Estonia"
    assert normalized["home_score"] == 1
    assert normalized["away_score"] == 0
    assert normalized["local_date"] == "Sep 30, 2026"
    assert normalized["local_start_time"] == "12:15 AM"
    assert normalized["venue"] == "Hristo Botev Stadium"
    assert normalized["source"] == "ESPN Scoreboard API"


@pytest.mark.asyncio
async def test_web_search_fallback_when_provider_empty(monkeypatch):
    """Verify web search fallback extracts structured match data when structured API returns empty."""
    async def mock_search_web(query, max_results=3):
        return [
            {
                "title": "India vs Bangladesh 1st T20I: Live schedule, timings, and squads",
                "snippet": "India vs Bangladesh match is scheduled to take place on October 6, 2026 at New Madhavrao Scindia Stadium.",
                "source": "ESPN Cricinfo",
                "date": "Sep 28, 2026",
            }
        ]

    import backend.tools.web_search
    monkeypatch.setattr(backend.tools.web_search, "search_web", mock_search_web)

    fallback_matches = await SportsTool.fetch_fixtures_via_web_fallback(
        query="India cricket next match",
        sport="Cricket",
        competition="Bilateral Series",
        timezone_str="Asia/Kolkata",
    )

    assert len(fallback_matches) == 1
    m = fallback_matches[0]
    assert m["home_team"]["name"] == "India"
    assert m["away_team"]["name"] == "Bangladesh"
    assert m["status"] == "SCHEDULED"
    assert m["source"] == "ESPN Cricinfo"


@pytest.mark.asyncio
async def test_missing_data_handling_honesty():
    """Verify that when no verified fixtures exist, system produces an honest summary rather than inventing matches."""
    result = await SportsTool.fetch_fixtures({
        "sport": "curling",
        "competition": "non_existent_championship_9999",
        "date_from": "2099-01-01",
    })

    assert len(result["matches"]) == 0
    assert "no matches scheduled" in result["summary"].lower()


@pytest.mark.asyncio
async def test_orchestrator_end_to_end_sports_event_emission():
    """Verify end-to-end execution of a sports fixture query through the Orchestrator emits SPORTS_FIXTURES event."""
    from backend.tools.base import create_default_registry
    event_bus = EventBus()
    tools = create_default_registry()
    provider = MockProvider()
    orchestrator = Orchestrator(
        session_id="test_sports_session",
        llm_provider=provider,
        tool_registry=tools,
        event_bus=event_bus,
    )

    emitted_events = []

    async def event_collector(event):
        emitted_events.append(event)

    event_bus.subscribe_all(event_collector)

    result = await orchestrator.handle_user_input("Which teams play UEFA Nations League today?")

    assert result["status"] == "completed"
    assert "matches" in result
    assert "spoken_summary" in result

    # Verify SPORTS_FIXTURES event was fired
    sports_events = [e for e in emitted_events if e.type == EventType.SPORTS_FIXTURES]
    assert len(sports_events) == 1, "SPORTS_FIXTURES event was not emitted"
    payload = sports_events[0].data
    assert "matches" in payload
    assert "summary" in payload
    assert payload["timezone"] == "Asia/Kolkata"

    # Verify RESPONSE_COMPLETED event includes spoken_summary
    resp_events = [e for e in emitted_events if e.type == EventType.RESPONSE_COMPLETED]
    assert len(resp_events) >= 1
    assert "spoken_summary" in resp_events[-1].data
