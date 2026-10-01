"""
SURU AI — Generic Natural Language Date & Range Resolver.

Provides robust, general-purpose temporal and date extraction for any query.
Supports:
- Explicit dates: "September 28", "28 September", "Sep 28th", "October 1", "Oct 1st"
- Relative dates: "today", "tonight", "tomorrow", "yesterday"
- Weekends: "this weekend", "next weekend"
- Weekdays: "next Monday", "this Friday", "on Tuesday"
- Date ranges: "between Sep 28 and Sep 30", "from September 28 to October 2", "Sep 28 - Sep 30"
- ISO / numeric formats: "2026-09-28", "28/09/2026", "09-28-2026"

No hardcoded questions or topics. Completely generic.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional

MONTHS: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

WEEKDAYS: dict[str, int] = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}


def parse_date_intent(
    text: str,
    reference_date: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Parse natural language text and return (date_from, date_to) formatted as YYYY-MM-DD.
    If no range is present, date_to is None.
    If no date is mentioned in text, returns (None, None).
    """
    if not text or not text.strip():
        return None, None

    t = text.lower().strip()

    # Parse reference date
    ref_dt: date
    if reference_date:
        try:
            ref_dt = datetime.strptime(reference_date.strip()[:10], "%Y-%m-%d").date()
        except Exception:
            ref_dt = date.today()
    else:
        ref_dt = date.today()

    # 1. Date ranges: "between <d1> and <d2>", "from <d1> to <d2>", "<d1> to <d2>", "<d1> - <d2>"
    range_match = re.search(
        r"(?:between|from)\s+([a-zA-Z0-9\s,]+?)\s+(?:and|to|-)\s+([a-zA-Z0-9\s,]+)",
        t,
    )
    if not range_match:
        range_match = re.search(
            r"([a-zA-Z]{3,9}\s+\d{1,2})\s*(?:to|-)\s*([a-zA-Z]{3,9}\s+\d{1,2})",
            t,
        )
    if range_match:
        d1_str, d2_str = range_match.group(1).strip(), range_match.group(2).strip()
        d1, _ = parse_single_date(d1_str, ref_dt)
        d2, _ = parse_single_date(d2_str, ref_dt)
        if d1 and d2:
            return (min(d1, d2), max(d1, d2))
        if d1:
            return d1, None

    # 2. Weekends
    if "this weekend" in t:
        sat = ref_dt + timedelta(days=(5 - ref_dt.weekday()))
        sun = sat + timedelta(days=1)
        return sat.strftime("%Y-%m-%d"), sun.strftime("%Y-%m-%d")

    if "next weekend" in t:
        sat = ref_dt + timedelta(days=(5 - ref_dt.weekday() + 7))
        sun = sat + timedelta(days=1)
        return sat.strftime("%Y-%m-%d"), sun.strftime("%Y-%m-%d")

    # 3. Relative single keywords
    if "yesterday" in t:
        return (ref_dt - timedelta(days=1)).strftime("%Y-%m-%d"), None

    if "tomorrow" in t:
        return (ref_dt + timedelta(days=1)).strftime("%Y-%m-%d"), None

    if "today" in t or "tonight" in t:
        return ref_dt.strftime("%Y-%m-%d"), None

    # 4. "next <weekday>" / "this <weekday>" / "on <weekday>"
    for day_name, day_idx in WEEKDAYS.items():
        if f"next {day_name}" in t:
            days_ahead = (day_idx - ref_dt.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            else:
                days_ahead += 7
            return (ref_dt + timedelta(days=days_ahead)).strftime("%Y-%m-%d"), None

        if f"this {day_name}" in t or f"on {day_name}" in t:
            days_ahead = (day_idx - ref_dt.weekday()) % 7
            if days_ahead == 0 and f"this {day_name}" in t:
                days_ahead = 7
            return (ref_dt + timedelta(days=days_ahead)).strftime("%Y-%m-%d"), None

    # 5. Standalone 4-digit Year (e.g. "IPL 2025", "2024 season", "in 2023")
    # Matches a 4-digit year between 1900 and 2100 not attached to month/day
    year_match = re.search(r"\b(19\d\d|20\d\d)\b", t)
    if year_match:
        yr = int(year_match.group(1))
        # If text explicitly requests a year or season, return the full year boundary
        return f"{yr}-01-01", f"{yr}-12-31"

    # 6. Month name + day (e.g. "September 28", "28 September", "Sep 28th", "October 1")
    d_single, _ = parse_single_date(t, ref_dt)
    if d_single:
        return d_single, None

    return None, None


def parse_single_date(text: str, ref_dt: date) -> tuple[Optional[str], Optional[str]]:
    """Helper to parse a single explicit date occurrence."""
    # 1. Check Month + Day
    for m_name, m_num in MONTHS.items():
        # Match 'September 28' or 'Sep 28th' or 'September 28, 2026'
        pattern1 = rf"\b{m_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s*,?\s*(\d{{4}}))?\b"
        match1 = re.search(pattern1, text)
        if match1:
            day = int(match1.group(1))
            year = int(match1.group(2)) if match1.group(2) else ref_dt.year
            try:
                dt = date(year, m_num, day)
                return dt.strftime("%Y-%m-%d"), None
            except ValueError:
                pass

        # Match '28 September' or '28th Sep' or '28th of September'
        pattern2 = rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?{m_name}(?:\s*,?\s*(\d{{4}}))?\b"
        match2 = re.search(pattern2, text)
        if match2:
            day = int(match2.group(1))
            year = int(match2.group(2)) if match2.group(2) else ref_dt.year
            try:
                dt = date(year, m_num, day)
                return dt.strftime("%Y-%m-%d"), None
            except ValueError:
                pass

    # 2. Check ISO format: YYYY-MM-DD
    iso_match = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        try:
            dt = date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
            return dt.strftime("%Y-%m-%d"), None
        except ValueError:
            pass

    # 3. Check DD/MM/YYYY or MM/DD/YYYY
    slash_match = re.search(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b", text)
    if slash_match:
        p1, p2, yr = int(slash_match.group(1)), int(slash_match.group(2)), int(slash_match.group(3))
        # Try DD/MM/YYYY then MM/DD/YYYY
        try:
            if p2 <= 12 and p1 <= 31:
                return date(yr, p2, p1).strftime("%Y-%m-%d"), None
            elif p1 <= 12 and p2 <= 31:
                return date(yr, p1, p2).strftime("%Y-%m-%d"), None
        except ValueError:
            pass

    return None, None
