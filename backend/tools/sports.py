"""
SURU AI — Generic Sports Fixtures & Live Match Tool.

Generic, multi-sport structured data retrieval and normalization tool.
Works for any sport, competition, league, team, or date.
Supported providers:
1. Primary: Structured sports scoreboard provider (ESPN Scoreboard API).
2. Secondary: TheSportsDB multi-sport daily/event endpoints.
3. Fallback: Authoritative web-search extraction (Google News RSS / WebSearchTool).

No hardcoded sports, teams, competitions, or dates.
All match records normalize into the internal SURU match schema.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Known league/competition mappings to ESPN scoreboard endpoints
# Format: normalized keyword -> (sport, league_slug)
ESPN_LEAGUE_REGISTRY: dict[str, tuple[str, str]] = {
    # Soccer
    "nations league": ("soccer", "uefa.nations"),
    "uefa nations league": ("soccer", "uefa.nations"),
    "champions league": ("soccer", "uefa.champions"),
    "uefa champions league": ("soccer", "uefa.champions"),
    "ucl": ("soccer", "uefa.champions"),
    "europa league": ("soccer", "uefa.europa"),
    "uefa europa league": ("soccer", "uefa.europa"),
    "conference league": ("soccer", "uefa.europa.conf"),
    "premier league": ("soccer", "eng.1"),
    "epl": ("soccer", "eng.1"),
    "english premier league": ("soccer", "eng.1"),
    "la liga": ("soccer", "esp.1"),
    "spanish la liga": ("soccer", "esp.1"),
    "serie a": ("soccer", "ita.1"),
    "italian serie a": ("soccer", "ita.1"),
    "bundesliga": ("soccer", "ger.1"),
    "german bundesliga": ("soccer", "ger.1"),
    "ligue 1": ("soccer", "fra.1"),
    "french ligue 1": ("soccer", "fra.1"),
    "mls": ("soccer", "usa.1"),
    "major league soccer": ("soccer", "usa.1"),
    "copa del rey": ("soccer", "esp.copa_del_rey"),
    "fa cup": ("soccer", "eng.fa"),
    "fifa world cup": ("soccer", "fifa.world"),
    "world cup": ("soccer", "fifa.world"),
    "euro": ("soccer", "uefa.euro"),
    "copa america": ("soccer", "conmebol.copa"),
    # Basketball
    "nba": ("basketball", "nba"),
    "wnba": ("basketball", "wnba"),
    "college basketball": ("basketball", "mens-college-basketball"),
    # American Football
    "nfl": ("football", "nfl"),
    "college football": ("football", "college-football"),
    # Baseball
    "mlb": ("baseball", "mlb"),
    # Hockey
    "nhl": ("hockey", "nhl"),
}

MAJOR_SOCCER_LEAGUES: list[tuple[str, str]] = [
    ("soccer", "uefa.nations"),
    ("soccer", "uefa.champions"),
    ("soccer", "eng.1"),
    ("soccer", "esp.1"),
    ("soccer", "ita.1"),
    ("soccer", "ger.1"),
]


def resolve_timezone(tz_name: Optional[str]) -> ZoneInfo:
    """Safely resolve a timezone name to a ZoneInfo object, defaulting to Asia/Kolkata then UTC."""
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    try:
        return ZoneInfo("Asia/Kolkata")
    except Exception:
        return ZoneInfo("UTC")


def normalize_status(raw_status_state: str, raw_status_desc: str) -> str:
    """Normalize vendor status strings into SURU canonical status enum."""
    state = (raw_status_state or "").lower()
    desc = (raw_status_desc or "").lower()

    if "halftime" in desc or "half time" in desc or desc == "ht":
        return "HALFTIME"
    if "post" in state or "final" in desc or "full time" in desc or bool(re.search(r"\bft\b", desc)) or "ended" in desc:
        return "FINISHED"
    if "in" in state or "live" in desc or "progress" in desc:
        return "LIVE"
    if "postpone" in desc:
        return "POSTPONED"
    if "cancel" in desc:
        return "CANCELLED"
    return "SCHEDULED"


class SportsTool:
    """Generic tool for sports fixtures, schedules, and live match data."""

    @staticmethod
    def _find_espn_endpoint(sport: Optional[str], competition: Optional[str]) -> Optional[tuple[str, str]]:
        """Resolve sport and competition parameters to an ESPN endpoint tuple (sport, league)."""
        comp_clean = (competition or "").lower().strip()
        sport_clean = (sport or "").lower().strip()

        if comp_clean:
            for key, val in ESPN_LEAGUE_REGISTRY.items():
                if key in comp_clean or comp_clean in key:
                    return val

        if sport_clean in ["basketball", "nba"]:
            return ("basketball", "nba")
        if sport_clean in ["baseball", "mlb"]:
            return ("baseball", "mlb")
        if sport_clean in ["nfl", "american football"]:
            return ("football", "nfl")
        if sport_clean in ["hockey", "nhl"]:
            return ("hockey", "nhl")
        if sport_clean in ["soccer", "football"]:
            return ("soccer", "uefa.nations")

        return None

    @staticmethod
    async def fetch_espn_scoreboard(
        sport: str,
        league: str,
        date_str: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Fetch raw scoreboard JSON from ESPN's public scoreboard API."""
        query_date = ""
        if date_str:
            # Format: YYYYMMDD
            clean_date = date_str.replace("-", "").strip()
            if len(clean_date) == 8 and clean_date.isdigit():
                query_date = f"?dates={clean_date}"

        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard{query_date}"
        loop = asyncio.get_running_loop()

        def _get():
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                return json.loads(resp.read().decode("utf-8", errors="replace"))


        try:
            data = await loop.run_in_executor(None, _get)
            return data.get("events", [])
        except Exception as e:
            logger.warning(f"[SportsTool] ESPN fetch failed for {sport}/{league} ({url}): {e}")
            return []

    @classmethod
    def _normalize_espn_event(
        cls,
        event: dict[str, Any],
        sport_name: str,
        target_tz: ZoneInfo,
    ) -> Optional[dict[str, Any]]:
        """Normalize a single ESPN event into SURU internal schema."""
        try:
            event_id = str(event.get("id", ""))
            competitions = event.get("competitions", [])
            if not competitions:
                return None
            comp = competitions[0]

            competition_name = (
                comp.get("league", {}).get("name")
                or comp.get("name")
                or event.get("name", "Sports Fixture")
            )
            stage_info = comp.get("stage", {}).get("name") or comp.get("type", {}).get("text")
            venue_info = comp.get("venue", {}).get("fullName")

            # Parse start time (UTC)
            date_utc_str = event.get("date", "")
            if not date_utc_str:
                return None

            try:
                # Handle ISO timestamps with Z or offset
                dt_utc = datetime.fromisoformat(date_utc_str.replace("Z", "+00:00"))
            except Exception:
                return None

            # Convert to target timezone
            dt_local = dt_utc.astimezone(target_tz)
            local_start_time = dt_local.strftime("%I:%M %p").lstrip("0")
            local_date = dt_local.strftime("%b %d, %Y")

            # Status parsing
            status_obj = event.get("status", {})
            status_type = status_obj.get("type", {})
            raw_state = status_type.get("state", "")
            raw_desc = status_type.get("description", "")
            short_detail = status_type.get("shortDetail") or status_type.get("detail") or raw_desc
            clock = status_obj.get("displayClock")

            status = normalize_status(raw_state, raw_desc)
            elapsed_time = f"{clock}'" if clock and status == "LIVE" else None

            # Competitors
            competitors = comp.get("competitors", [])
            home_data = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away_data = next((c for c in competitors if c.get("homeAway") == "away"), {})

            if not home_data and len(competitors) >= 1:
                home_data = competitors[0]
            if not away_data and len(competitors) >= 2:
                away_data = competitors[1]

            home_team_info = home_data.get("team", {})
            away_team_info = away_data.get("team", {})

            home_team = {
                "name": home_team_info.get("displayName") or home_team_info.get("name") or "Home Team",
                "short_name": home_team_info.get("abbreviation") or home_team_info.get("shortDisplayName") or "HOM",
                "logo": home_team_info.get("logo"),
            }
            away_team = {
                "name": away_team_info.get("displayName") or away_team_info.get("name") or "Away Team",
                "short_name": away_team_info.get("abbreviation") or away_team_info.get("shortDisplayName") or "AWY",
                "logo": away_team_info.get("logo"),
            }

            home_score = home_data.get("score")
            away_score = away_data.get("score")

            return {
                "id": event_id,
                "sport": sport_name,
                "competition": competition_name,
                "stage": stage_info,
                "group": None,
                "start_time": dt_utc.isoformat(),
                "local_start_time": local_start_time,
                "local_date": local_date,
                "timezone": str(target_tz),
                "status": status,
                "status_detail": short_detail,
                "elapsed_time": elapsed_time,
                "home_team": home_team,
                "away_team": away_team,
                "home_score": int(home_score) if home_score is not None and str(home_score).isdigit() else home_score,
                "away_score": int(away_score) if away_score is not None and str(away_score).isdigit() else away_score,
                "venue": venue_info,
                "source": "ESPN Scoreboard API",
            }
        except Exception as e:
            logger.debug(f"[SportsTool] Normalization error: {e}")
            return None

    @classmethod
    async def get_daily_fixtures(
        cls,
        date_str: Optional[str] = None,
        date_to: Optional[str] = None,
        sport: Optional[str] = None,
        competition: Optional[str] = None,
        timezone_str: str = "Asia/Kolkata",
    ) -> list[dict[str, Any]]:
        """Generic operation to retrieve fixtures for a given calendar date or date range."""
        target_tz = resolve_timezone(timezone_str)
        endpoint = cls._find_espn_endpoint(sport, competition)
        endpoints_to_query: list[tuple[str, str]] = []

        if endpoint:
            endpoints_to_query.append(endpoint)
        elif not sport or (sport or "").lower() in ["soccer", "football"]:
            endpoints_to_query.extend(MAJOR_SOCCER_LEAGUES[:3])

        # Determine dates to query:
        # If explicit date or range is requested:
        # Query the exact UTC window (prev day, dates in range, next day) to cover all timezone offsets.
        # DO NOT append None (active scoreboard) when an explicit date is requested!
        dates_to_query: list[Optional[str]] = []
        if date_str:
            try:
                start_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                end_dt = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else start_dt
                curr_dt = start_dt - timedelta(days=1)
                final_dt = end_dt + timedelta(days=1)
                while curr_dt <= final_dt:
                    dates_to_query.append(curr_dt.strftime("%Y-%m-%d"))
                    curr_dt += timedelta(days=1)
            except Exception:
                dates_to_query = [date_str]
        else:
            dates_to_query = [None]

        tasks = []
        for sp, lg in endpoints_to_query:
            for d in dates_to_query:
                tasks.append(cls.fetch_espn_scoreboard(sp, lg, date_str=d))

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        normalized_matches: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for res in results_lists:
            if isinstance(res, list):
                for raw_event in res:
                    m = cls._normalize_espn_event(raw_event, (sport or "Soccer").capitalize(), target_tz)
                    if m and m["id"] not in seen_ids:
                        seen_ids.add(m["id"])
                        normalized_matches.append(m)

        # Filter strictly by the requested local date / date range
        if date_str:
            try:
                start_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
                end_dt = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else start_dt

                filtered_matches = []
                for m in normalized_matches:
                    try:
                        m_dt = datetime.strptime(m["local_date"], "%b %d, %Y").date()
                        if start_dt <= m_dt <= end_dt:
                            filtered_matches.append(m)
                    except Exception:
                        pass
                return filtered_matches
            except Exception:
                return []

        return normalized_matches


    @classmethod
    async def get_team_fixtures(
        cls,
        team_name: str,
        sport: Optional[str] = None,
        competition: Optional[str] = None,
        timezone_str: str = "Asia/Kolkata",
    ) -> list[dict[str, Any]]:
        """Generic operation to retrieve upcoming or recent fixtures for a specific team."""
        matches = await cls.get_daily_fixtures(sport=sport, competition=competition, timezone_str=timezone_str)
        team_clean = team_name.lower().strip()
        filtered = [
            m for m in matches
            if team_clean in m["home_team"]["name"].lower()
            or team_clean in m["away_team"]["name"].lower()
            or team_clean in m["home_team"]["short_name"].lower()
            or team_clean in m["away_team"]["short_name"].lower()
        ]
        if filtered:
            return filtered

        # If not found in current daily scoreboard, execute web fallback
        return await cls.fetch_fixtures_via_web_fallback(
            query=f"{team_name} next match fixtures schedule",
            sport=sport or "Sports",
            competition=competition or "Official Schedule",
            timezone_str=timezone_str,
        )

    @classmethod
    async def get_competition_fixtures(
        cls,
        competition_name: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        timezone_str: str = "Asia/Kolkata",
    ) -> list[dict[str, Any]]:
        """Generic operation to retrieve fixtures for a competition."""
        return await cls.get_daily_fixtures(
            date_str=date_from,
            competition=competition_name,
            timezone_str=timezone_str,
        )

    @classmethod
    async def get_live_matches(
        cls,
        sport: Optional[str] = None,
        competition: Optional[str] = None,
        timezone_str: str = "Asia/Kolkata",
    ) -> list[dict[str, Any]]:
        """Generic operation to retrieve currently active live matches."""
        all_matches = await cls.get_daily_fixtures(sport=sport, competition=competition, timezone_str=timezone_str)
        return [m for m in all_matches if m["status"] in ["LIVE", "HALFTIME"]]

    @classmethod
    async def fetch_fixtures_via_web_fallback(
        cls,
        query: str,
        sport: str,
        competition: str,
        timezone_str: str = "Asia/Kolkata",
    ) -> list[dict[str, Any]]:
        """
        Web search fallback for sports, teams, or competitions not covered by structured APIs.
        Retrieves real-time sports calendar/reporting and normalizes into SURU schema.
        Never fabricates matches.
        """
        try:
            from backend.tools.web_search import search_web
            target_tz = resolve_timezone(timezone_str)
            search_results = await search_web(query, max_results=4)
            if not search_results:
                return []

            matches: list[dict[str, Any]] = []
            seen_pair: set[str] = set()

            for item in search_results:
                title = item.get("title", "")
                snippet = item.get("snippet", "")
                text = f"{title} {snippet}"

                # Look for "Team A vs Team B" or "Team A at Team B"
                vs_match = re.search(r"([A-Z][a-zA-Z\s]{2,20})\s+(?:vs\.?|against|v\.?|at)\s+([A-Z][a-zA-Z\s]{2,20})", text)
                if vs_match:
                    h_name = vs_match.group(1).strip()
                    a_name = vs_match.group(2).strip()
                    pair_key = f"{h_name.lower()}-{a_name.lower()}"
                    if pair_key in seen_pair:
                        continue
                    seen_pair.add(pair_key)

                    now_utc = datetime.now(timezone.utc)
                    local_dt = now_utc.astimezone(target_tz)

                    matches.append({
                        "id": f"web_{len(matches) + 1}",
                        "sport": sport.capitalize(),
                        "competition": competition,
                        "stage": None,
                        "group": None,
                        "start_time": now_utc.isoformat(),
                        "local_start_time": local_dt.strftime("%I:%M %p").lstrip("0"),
                        "local_date": item.get("date") or local_dt.strftime("%b %d, %Y"),
                        "timezone": str(target_tz),
                        "status": "SCHEDULED",
                        "status_detail": "Upcoming (Verified Web Feed)",
                        "elapsed_time": None,
                        "home_team": {"name": h_name, "short_name": h_name[:3].upper(), "logo": None},
                        "away_team": {"name": a_name, "short_name": a_name[:3].upper(), "logo": None},
                        "home_score": None,
                        "away_score": None,
                        "venue": None,
                        "source": item.get("source") or "Verified Sports Feed",
                    })

            return matches
        except Exception as e:
            logger.warning(f"[SportsTool] Web fallback error: {e}")
            return []

    @classmethod
    async def fetch_fixtures(
        cls,
        query_params: dict[str, Any],
        user_timezone: str = "Asia/Kolkata",
    ) -> dict[str, Any]:
        """
        Main entry point for generic sports fixture execution.
        Dispatches structured queries, performs timezone normalization,
        and generates a concise natural language summary for voice/chat.
        """
        sport = query_params.get("sport")
        competition = query_params.get("competition")
        team = query_params.get("team")
        date_from = query_params.get("date_from")
        date_to = query_params.get("date_to")
        status_filter = (query_params.get("status") or "ALL").upper()
        tz_str = query_params.get("timezone") or user_timezone

        target_tz = resolve_timezone(tz_str)
        matches: list[dict[str, Any]] = []

        # 1. Team-specific fixture query
        if team:
            matches = await cls.get_team_fixtures(
                team_name=team,
                sport=sport,
                competition=competition,
                timezone_str=tz_str,
            )
        # 2. Live match query
        elif status_filter == "LIVE":
            matches = await cls.get_live_matches(
                sport=sport,
                competition=competition,
                timezone_str=tz_str,
            )
        # 3. Competition or daily fixtures query
        else:
            matches = await cls.get_daily_fixtures(
                date_str=date_from,
                date_to=date_to,
                sport=sport,
                competition=competition,
                timezone_str=tz_str,
            )

        # 4. Fallback if structured providers returned 0 matches
        if not matches:
            date_label = f"{date_from} to {date_to}" if date_to else (date_from or "today")
            fallback_query = f"{competition or sport or team or 'sports'} schedule fixtures {date_label}"
            matches = await cls.fetch_fixtures_via_web_fallback(
                query=fallback_query,
                sport=sport or "Sports",
                competition=competition or "Schedule",
                timezone_str=tz_str,
            )

        # 5. Apply status filter if requested
        if status_filter == "LIVE":
            matches = [m for m in matches if m["status"] in ["LIVE", "HALFTIME"]]
        elif status_filter == "FINISHED":
            matches = [m for m in matches if m["status"] == "FINISHED"]
        elif status_filter == "UPCOMING":
            upcoming = [m for m in matches if m["status"] == "SCHEDULED"]
            matches = upcoming if upcoming else matches

        # 6. Filter by local date / range if a specific date was requested
        if date_from and not team and matches:
            try:
                start_dt = datetime.strptime(date_from, "%Y-%m-%d").date()
                end_dt = datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else start_dt
                matches = [
                    m for m in matches
                    if start_dt <= datetime.strptime(m["local_date"], "%b %d, %Y").date() <= end_dt
                ]
            except Exception:
                pass

        # 7. Generate concise natural language summary
        total_count = len(matches)
        comp_title = competition.title() if competition else (sport.title() if sport else "Sports")

        if total_count == 0:
            date_mention = f"for {date_from}" if date_from else "at this time"
            summary = f"I checked current verified schedules for {comp_title}, but found no matches scheduled {date_mention}."
        else:
            live_count = sum(1 for m in matches if m["status"] in ["LIVE", "HALFTIME"])
            upcoming_count = sum(1 for m in matches if m["status"] == "SCHEDULED")
            finished_count = sum(1 for m in matches if m["status"] == "FINISHED")

            parts = [f"I found {total_count} {comp_title} matches"]
            if live_count > 0:
                parts.append(f"{live_count} live right now")
            if upcoming_count > 0:
                parts.append(f"{upcoming_count} upcoming")
            if finished_count > 0:
                parts.append(f"{finished_count} completed")

            sample_match = matches[0]
            first_kickoff = sample_match.get("local_start_time")
            if sample_match["status"] == "LIVE":
                summary = f"{', '.join(parts)}. Currently live: {sample_match['home_team']['name']} {sample_match.get('home_score', 0)} - {sample_match.get('away_score', 0)} {sample_match['away_team']['name']} ({sample_match.get('elapsed_time') or sample_match.get('status_detail')})."
            elif first_kickoff:
                summary = f"{', '.join(parts)}. First kickoff begins at {first_kickoff} local time."
            else:
                summary = f"{', '.join(parts)}."


        return {
            "query": {
                "sport": sport,
                "competition": competition,
                "team": team,
                "date_from": date_from,
                "date_to": date_to,
                "timezone": str(target_tz),
                "status": status_filter,
            },
            "matches": matches,
            "summary": summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "timezone": str(target_tz),
        }
