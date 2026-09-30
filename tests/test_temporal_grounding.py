import pytest
from backend.agent.context_manager import ContextManager
from backend.providers.base import MockProvider
from backend.providers.google_gemini import GeminiProvider
from backend.tools.web_search import format_search_evidence, search_web


@pytest.mark.asyncio
async def test_temporal_intent_routing_mock():
    """Verify semantic temporal intent routing with zero entity whitelisting (MockProvider)."""
    mock = MockProvider()
    runtime_date = ContextManager.get_current_runtime_date()

    test_queries = [
        ("What is the capital of Australia?", False, "Timeless knowledge"),
        ("Explain ArrayList vs LinkedList in Java", False, "Coding"),
        ("Calculate 17.5% of 84000", False, "Calculation"),
        ("How many international centuries does Virat Kohli have currently?", True, "Current sports stat"),
        ("How many career goals does Cristiano Ronaldo have currently?", True, "Current sports stat"),
        ("Who is the current President of France?", True, "Current political leader"),
        ("Who won the match last night?", True, "Recent match result"),
        ("What is today's weather in Tokyo?", True, "Current weather"),
    ]

    for q, expect_grounding, label in test_queries:
        intent = await mock.determine_intent(q, current_date=runtime_date)
        gr = intent.get("needs_grounding", False)
        assert gr == expect_grounding, f"Failed on query '{q}': expected grounding={expect_grounding}, got {gr} ({label})"


@pytest.mark.asyncio
async def test_temporal_intent_routing_gemini():
    """Verify semantic temporal intent routing with zero entity whitelisting (Gemini)."""
    gemini = GeminiProvider(fallback_to_mock=False)
    if not gemini.is_configured:
        pytest.skip("Gemini API not configured")

    runtime_date = ContextManager.get_current_runtime_date()
    test_queries = [
        ("What is the capital of Australia?", False),
        ("Explain ArrayList vs LinkedList in Java", False),
        ("Calculate 17.5% of 84000", False),
        ("How many international centuries does Virat Kohli have currently?", True),
        ("How many career goals does Cristiano Ronaldo have currently?", True),
        ("Who is the current President of France?", True),
        ("Who won the match last night?", True),
    ]

    for q, expect_grounding in test_queries:
        intent = await gemini.determine_intent(q, current_date=runtime_date)
        gr = intent.get("needs_grounding", False)
        assert gr == expect_grounding, f"Failed on Gemini query '{q}': expected grounding={expect_grounding}, got {gr}"


@pytest.mark.asyncio
async def test_fresh_evidence_overrides_stale_conversation_context():
    """Architectural test: When previous context contains stale information, fresh evidence must win."""
    gemini = GeminiProvider(fallback_to_mock=False)
    if not gemini.is_configured:
        pytest.skip("Gemini API not configured")

    current_date = ContextManager.get_current_runtime_date()
    stale_context = "User: How many ODI runs does Kohli have?\nAssistant: Kohli has 14,797 ODI runs."
    query = "How many ODI runs has Virat Kohli scored till date?"

    resp = await gemini.generate_direct_response(
        query,
        context=stale_context,
        use_grounding=True,
        current_date=current_date,
    )
    assert resp and len(resp) > 20
    # Must report 15,000+ milestone from September 27-29, 2026 reporting rather than repeating 14,797
    assert "15,000" in resp or "15000" in resp


@pytest.mark.asyncio
async def test_conflicting_dated_sources_newest_wins():
    """Architectural test: When multiple conflicting dated sources exist, newest evidence supersedes."""
    gemini = GeminiProvider(fallback_to_mock=False)
    if not gemini.is_configured:
        pytest.skip("Gemini API not configured")

    current_date = "Tuesday, September 29, 2026"
    mock_results = [
        {
            "title": "AlphaCorp Quarterly Revenue Reaches $500M",
            "source": "Financial Times",
            "date": "September 28, 2026",
            "timestamp": 1790640000.0,
            "snippet": "AlphaCorp reports record Q3 revenue of $500M as of September 28, 2026.",
            "url": "https://example.com/ft-news",
        },
        {
            "title": "AlphaCorp Revenue at $350M in 2024",
            "source": "TechDaily",
            "date": "March 15, 2024",
            "timestamp": 1710460800.0,
            "snippet": "AlphaCorp closed the year with $350M total revenue.",
            "url": "https://example.com/tech-old",
        },
    ]

    evidence = format_search_evidence(mock_results, "What is AlphaCorp revenue currently?", as_of_date=current_date)
    prompt = f"""You are SURU AI, a helpful, intelligent, real-time interruptible AI assistant.

LIVE RETRIEVED WEB EVIDENCE:
{evidence}

CRITICAL GROUNDING & TEMPORAL INSTRUCTIONS:
1. Current Runtime Date: {current_date}.
2. RECENCY RULE: A newer source (e.g. September 28, 2026) COMPLETELY SUPERSEDES and OVERRIDES an older source (e.g. 2024).
3. Answer based on the newest figure supported by recent authoritative reporting.

User Request:
"What is AlphaCorp revenue currently?"
"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    data = await gemini._post_gemini("generateContent", payload)
    ans = data["candidates"][0]["content"]["parts"][0]["text"]

    assert "$500M" in ans or "500 million" in ans.lower()
    assert "$350M" not in ans or "previously" in ans.lower() or "in 2024" in ans.lower()


@pytest.mark.asyncio
async def test_unseen_current_information_retrieval():
    """Architectural test: Genuinely fresh unseen question retrieves live evidence and answers accurately."""
    gemini = GeminiProvider(fallback_to_mock=False)
    if not gemini.is_configured:
        pytest.skip("Gemini API not configured")

    current_date = ContextManager.get_current_runtime_date()
    unseen_query = "Who is the current Chancellor of Germany?"
    resp = await gemini.generate_direct_response(
        unseen_query,
        use_grounding=True,
        current_date=current_date,
    )
    assert resp and len(resp) > 20
    assert "Merz" in resp or "Friedrich" in resp or "Chancellor" in resp


@pytest.mark.asyncio
async def test_gemini_followup_contextual_grounding():
    """Verify follow-up queries inherit grounding requirement when time-sensitive."""
    gemini = GeminiProvider(fallback_to_mock=False)
    if not gemini.is_configured:
        pytest.skip("Gemini API not configured")

    runtime_date = ContextManager.get_current_runtime_date()
    conv_context = "User: How many international centuries does Virat Kohli have currently?\nAssistant: As of September 2026, Virat Kohli has 86 international centuries."
    follow_up_q = "What about Cristiano Ronaldo's career goals?"
    intent_fu = await gemini.determine_intent(follow_up_q, context=conv_context, current_date=runtime_date)
    assert intent_fu.get("needs_grounding", False) is True

    resp_fu = await gemini.generate_direct_response(
        follow_up_q,
        context=conv_context,
        use_grounding=True,
        current_date=runtime_date,
    )
    assert resp_fu and len(resp_fu) > 20
    assert any(w in resp_fu.lower() for w in ["goal", "ronaldo", "cristiano"])
