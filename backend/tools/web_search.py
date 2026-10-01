"""
SURU AI Web Search Service & Tool.

Provides real-time web retrieval for current information, recent events,
and live statistics without question-specific hardcoding or entity whitelists.
Includes multi-source news & web retrieval, publication date parsing,
and multi-factor recency ranking.
"""

from __future__ import annotations

import asyncio
import datetime
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any
import httpx

from backend.tools.base import BaseTool, ToolResult, ToolResultStatus


def parse_pubdate(date_str: str) -> tuple[float, str]:
    """
    Parse date strings (RFC-822, relative, or month-day-year) into
    a numeric timestamp (epoch seconds) and human-readable string.
    """
    if not date_str:
        return 0.0, ""

    # 1. Try standard RFC-822 (used in RSS)
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.timestamp(), dt.strftime("%B %d, %Y")
    except Exception:
        pass

    # 2. Check relative time: "X hours ago", "X days ago"
    rel_match = re.search(r'(\d+)\s*(hour|hr|day|d|min|m)s?\s*ago', date_str, re.IGNORECASE)
    if rel_match:
        val = int(rel_match.group(1))
        unit = rel_match.group(2).lower()
        now = datetime.datetime.now(datetime.timezone.utc)
        if "h" in unit or "m" in unit:
            dt = now - datetime.timedelta(hours=val)
        else:
            dt = now - datetime.timedelta(days=val)
        return dt.timestamp(), dt.strftime("%B %d, %Y")

    # 3. Check regex: "27 September 2026", "September 27, 2026", "Sep 27, 2026"
    months = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12,
    }
    month_pattern = "|".join(months.keys())
    m_re = re.search(
        rf'\b(?:(\d{{1,2}})\s+({month_pattern})|({month_pattern})\s+(\d{{1,2}})),?\s+(\d{{4}})\b',
        date_str,
        re.IGNORECASE
    )
    if m_re:
        try:
            day = int(m_re.group(1) or m_re.group(4) or 1)
            m_str = (m_re.group(2) or m_re.group(3)).lower()
            month = months.get(m_str, 1)
            yr = int(m_re.group(5))
            dt = datetime.datetime(yr, month, day, tzinfo=datetime.timezone.utc)
            return dt.timestamp(), dt.strftime("%B %d, %Y")
        except Exception:
            pass

    # 4. Check "Month Year" (e.g. "September 2026")
    my_re = re.search(rf'\b({month_pattern})\s+(\d{{4}})\b', date_str, re.IGNORECASE)
    if my_re:
        try:
            m_str = my_re.group(1).lower()
            month = months.get(m_str, 1)
            yr = int(my_re.group(2))
            dt = datetime.datetime(yr, month, 1, tzinfo=datetime.timezone.utc)
            return dt.timestamp(), f"{m_str.capitalize()} {yr}"
        except Exception:
            pass

    return 0.0, date_str


async def fetch_google_news_rss(query: str, max_results: int = 6, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Fetch live news reporting via Google News RSS endpoint."""
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-US&gl=US&ceid=US:en"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                return []
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            results = []
            for item in items[:max_results]:
                title = item.find("title").text if item.find("title") is not None else ""
                pub = item.find("pubDate").text if item.find("pubDate") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                clean_desc = html.unescape(re.sub(r'<[^>]+>', ' ', desc)).strip()

                source = ""
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title, source = parts[0], parts[1]

                ts, formatted_date = parse_pubdate(pub)
                if title:
                    results.append({
                        "title": title,
                        "source": source or "News",
                        "date": formatted_date,
                        "timestamp": ts,
                        "snippet": clean_desc,
                        "url": link,
                    })
            return results
    except Exception:
        return []


async def fetch_authoritative_archive(query: str, max_sections: int = 5, timeout: float = 8.0) -> list[dict[str, Any]]:
    """
    Search authoritative encyclopedia and tournament archives for complete schedules,
    fixtures, election results, or multi-match tournament datasets.
    """
    clean_q = re.sub(r'^(?:give me|show me|what is|tell me|find)\s+(?:the\s+)?', '', query, flags=re.IGNORECASE)
    clean_q = re.sub(r'\b(?:complete|full|entire|all)\b', '', clean_q, flags=re.IGNORECASE).strip()

    headers = {
        "User-Agent": "SURU-AI-Agent/1.0 (https://github.com/tsaksham1304/SURU-AI-Interruptible-Real-Time-Agent; contact@suru.ai)",
    }

    results: list[dict[str, Any]] = []
    try:
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_q)}&format=json"
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(search_url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            hits = data.get("query", {}).get("search", [])
            if not hits:
                return []

            top_title = hits[0]["title"]

            sec_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(top_title)}&prop=sections&format=json"
            sec_resp = await client.get(sec_url)
            if sec_resp.status_code != 200:
                return []
            sec_data = sec_resp.json()
            sections = sec_data.get("parse", {}).get("sections", [])

            target_sections = []
            keywords = ["schedule", "fixture", "playoff", "reschedul", "bracket", "match", "result", "knockout", "stage", "final"]
            for s in sections:
                line_lower = s.get("line", "").lower()
                if any(k in line_lower for k in keywords):
                    target_sections.append((s["index"], s["line"]))

            if not target_sections and sections:
                target_sections = [(sections[0]["index"], sections[0]["line"])]

            target_sections = target_sections[:max_sections]

            for s_idx, s_title in target_sections:
                p_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={urllib.parse.quote(top_title)}&prop=text&section={s_idx}&format=json"
                p_resp = await client.get(p_url)
                if p_resp.status_code != 200:
                    continue
                p_data = p_resp.json()
                html_text = p_data.get("parse", {}).get("text", {}).get("*", "")

                clean_html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html_text, flags=re.DOTALL)
                plain = re.sub(r'<[^>]+>', ' ', clean_html)
                plain = html.unescape(plain)
                plain = re.sub(r'[ \t]+', ' ', plain)
                plain = re.sub(r'\n\s*\n', '\n', plain).strip()

                if plain:
                    max_chars = 50000 if any(k in s_title.lower() for k in ["fixture", "schedule", "match", "stage", "playoff"]) else 15000
                    results.append({
                        "title": f"Authoritative Archive: {top_title} — {s_title}",
                        "source": "Authoritative Archive",
                        "date": "",
                        "timestamp": 0.0,
                        "snippet": plain[:max_chars],
                        "url": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(top_title)}",
                        "score": 50000.0,
                    })
    except Exception:
        pass

    return results


async def fetch_web_ddg(query: str, max_results: int = 6, timeout: float = 6.0) -> list[dict[str, Any]]:
    """Fetch live web results via DuckDuckGo HTML endpoint."""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://duckduckgo.com/",
    }
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=timeout) as client:
            resp = await client.post(url, data={"q": query})
            if resp.status_code != 200:
                return []
            snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            titles = re.findall(r'class="result__title"[^>]*>.*?<a[^>]*>(.*?)</a>', resp.text, re.DOTALL)
            urls = re.findall(r'class="result__url"[^>]*>(.*?)</a>', resp.text, re.DOTALL)

            results = []
            for i in range(min(len(snippets), max_results)):
                t = html.unescape(re.sub(r'<[^>]+>', '', titles[i])).strip() if i < len(titles) else ""
                s = html.unescape(re.sub(r'<[^>]+>', '', snippets[i])).strip()
                u = html.unescape(re.sub(r'<[^>]+>', '', urls[i])).strip() if i < len(urls) else ""

                date_match = re.search(
                    r'(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}|\d+\s+(?:hours?|days?|mins?|weeks?)\s+ago)',
                    s,
                    re.IGNORECASE
                )
                raw_d = date_match.group(0) if date_match else ""
                ts, formatted_date = parse_pubdate(raw_d)

                if t and s:
                    results.append({
                        "title": t,
                        "source": "Web",
                        "date": formatted_date,
                        "timestamp": ts,
                        "snippet": s,
                        "url": u,
                    })
            return results
    except Exception:
        return []


async def search_web(
    query: str,
    max_results: int = 6,
    timeout: float = 6.0,
    current_date_str: str = "",
) -> list[dict[str, Any]]:
    """
    Perform a live multi-source web search with recency scoring and ranking.
    Queries both live news and web indexes, applying temporal query construction
    when freshness markers are detected.
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    # Detect generic temporal markers
    temporal_markers = [
        "till date", "currently", "current", "latest", "today", "now",
        "recent", "as of", "yesterday", "last night", "this week", "this month"
    ]
    is_temporal = any(m in clean_query.lower() for m in temporal_markers)

    month_year = ""
    if current_date_str:
        my_match = re.search(r'([A-Za-z]+)\s+\d{1,2},?\s+(\d{4})', current_date_str)
        if my_match:
            month_year = f"{my_match.group(1)} {my_match.group(2)}"

    core_query = re.sub(
        r'^(?:how many|what is|what are|who is|who are|tell me|can you tell me|find|which)\s+',
        '',
        clean_query,
        flags=re.IGNORECASE
    ).strip(' ?.')

    year_match = re.search(r"\b(19\d\d|20\d\d)\b", clean_query)
    requested_year = int(year_match.group(1)) if year_match else None
    current_year = datetime.datetime.now(datetime.timezone.utc).year
    is_historical_year = requested_year is not None and requested_year < current_year

    queries_to_run = [clean_query]
    if is_temporal and month_year and month_year.lower() not in clean_query.lower() and not requested_year:
        queries_to_run.append(f"{core_query} {month_year}")
    elif is_historical_year and core_query != clean_query:
        queries_to_run.append(core_query)

    tasks = []
    has_schedule_or_archive_intent = any(
        w in clean_query.lower() for w in [
            "schedule", "fixture", "fixtures", "matches", "tournament",
            "complete", "full", "entire", "all matches", "calendar", "archive"
        ]
    ) or is_historical_year

    if has_schedule_or_archive_intent:
        tasks.append(fetch_authoritative_archive(clean_query, timeout=timeout + 3.0))

    for q in queries_to_run:
        # For historical queries, RSS news from today is irrelevant; query web search
        if not is_historical_year:
            tasks.append(fetch_google_news_rss(q, max_results=max_results, timeout=timeout))
        tasks.append(fetch_web_ddg(q, max_results=max_results, timeout=timeout))

    fetched = await asyncio.gather(*tasks, return_exceptions=True)
    all_results = []
    for res_list in fetched:
        if isinstance(res_list, list):
            all_results.extend(res_list)

    # Multi-factor ranking: Query Relevance + Year Precision + Domain Authority + Recency
    query_terms = set(re.findall(r'\b[a-zA-Z0-9]{3,}\b', clean_query.lower()))

    seen_titles = set()
    ranked_results = []
    for r in all_results:
        norm_title = re.sub(r'[^a-zA-Z0-9]', '', r["title"].lower())
        if not norm_title or norm_title in seen_titles:
            continue
        seen_titles.add(norm_title)

        title_lower = r["title"].lower()
        snippet_lower = r.get("snippet", "").lower()
        text_content = f"{title_lower} {snippet_lower}"

        matched_terms = sum(1 for term in query_terms if term in text_content)
        relevance_score = matched_terms * 100.0

        # Exact phrase or title term bonus
        title_terms = sum(1 for term in query_terms if term in title_lower)
        relevance_score += title_terms * 80.0

        # Year matching precision: heavily boost matches for requested year, penalize mismatched years
        year_score = 0.0
        if requested_year:
            req_yr_str = str(requested_year)
            if req_yr_str in title_lower:
                year_score += 600.0
            elif req_yr_str in snippet_lower:
                year_score += 250.0

            # If title explicitly features a conflicting year (e.g. 2026 when 2025 was asked)
            other_years = re.findall(r"\b(19\d\d|20\d\d)\b", title_lower)
            if other_years and req_yr_str not in other_years:
                year_score -= 500.0

        # Recency bonus (capped so it never overrides relevance or year matching)
        recency_score = 0.0
        if not is_historical_year:
            ts = r.get("timestamp", 0.0)
            if ts > 0:
                # Up to 150 points for very recent news
                recency_score = min(150.0, max(0.0, (ts - 1.7e9) / 600000.0))

        # Authority score for recognized news/sports/reference domains
        src = r.get("source", "").lower()
        authority_score = 50.0 if any(
            a in src for a in ["icc", "bcci", "hindu", "times", "al jazeera", "bbc", "reuters", "espn", "cricinfo", "bloomberg", "wikipedia"]
        ) else 0.0

        # Authoritative archive boost
        archive_score = 20000.0 if r.get("source") == "Authoritative Archive" else 0.0

        total_score = relevance_score + year_score + recency_score + authority_score + archive_score
        r["score"] = total_score
        ranked_results.append(r)

    ranked_results.sort(key=lambda x: x["score"], reverse=True)
    return ranked_results[:max_results + 3]


def format_search_evidence(results: list[dict[str, Any]], query: str, as_of_date: str) -> str:
    """Format search results into structured, dated evidence text for LLM grounding."""
    if not results:
        return f"[Live Web Search for '{query}': No fresh external results could be retrieved as of {as_of_date}]"

    lines = []

    # 1. Authoritative Archival & Full Fixture Data (if retrieved)
    archive_items = [r for r in results if r.get("source") == "Authoritative Archive"]
    if archive_items:
        lines.append(f"[Authoritative Historical & Tournament Archive Records as of {as_of_date}]:")
        for idx, r in enumerate(archive_items, 1):
            lines.append(f"### {r.get('title')}")
            lines.append(f"Source URL: {r.get('url')}")
            lines.append(f"Official Archive Data:\n{r.get('snippet')}\n")

    # 2. General Web & News Results
    standard_items = [r for r in results if r.get("source") != "Authoritative Archive"]
    if standard_items:
        lines.append(f"[Live Web & News Evidence as of {as_of_date}]:")
        for idx, r in enumerate(standard_items, 1):
            title = r.get("title", f"Source {idx}")
            snippet = r.get("snippet", "")
            date_str = r.get("date", "")
            source_str = r.get("source", "")
            url_str = r.get("url", "")

            header_parts = [f"{idx}."]
            if date_str:
                header_parts.append(f"[Published: {date_str}]")
            if source_str:
                header_parts.append(f"({source_str})")
            header_parts.append(title)

            lines.append(" ".join(header_parts))
            if snippet:
                lines.append(f"   Snippet: {snippet}")
            if url_str:
                lines.append(f"   URL: {url_str}")

    return "\n".join(lines)


class WebSearchTool(BaseTool):
    """Tool allowing the agent or task executor to run live web search queries."""
    name = "web_search"
    description = "Search the web for current events, latest statistics, recent news, or factual verification."
    category = "SEARCH"

    async def execute(self, params: dict[str, Any], cancel_event: asyncio.Event) -> ToolResult:
        query = params.get("query") or params.get("q") or ""
        if not query:
            return ToolResult(
                success=False,
                status=ToolResultStatus.FAILED.value,
                data={},
                error="No search query provided",
                summary="Web search failed: empty query",
            )

        results = await search_web(query)
        if cancel_event.is_set():
            return ToolResult(
                success=False,
                status=ToolResultStatus.CANCELLED.value,
                data={},
                error="Search cancelled",
                summary="Web search cancelled",
            )

        if results:
            return ToolResult(
                success=True,
                status=ToolResultStatus.SUCCESS_WITH_RESULTS.value,
                data={"results": results, "query": query, "count": len(results)},
                summary=f"Found {len(results)} search results for '{query}'",
            )
        else:
            return ToolResult(
                success=True,
                status=ToolResultStatus.SUCCESS_WITH_NO_RESULTS.value,
                data={"results": [], "query": query, "count": 0},
                summary=f"No web search results found for '{query}'",
            )
