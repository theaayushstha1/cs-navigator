"""Date and deadline tools for the Scholarship agent."""

import os
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


def _local_tz():
    tz_name = os.getenv("TUTOR_TZ", "America/New_York")
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return timezone.utc


def get_current_date() -> dict:
    """Get today's date with semester context.

    Returns current date in multiple formats plus the current academic semester.
    """
    now = datetime.now(_local_tz())
    month = now.month

    if month <= 5:
        semester = "Spring"
    elif month <= 7:
        semester = "Summer"
    else:
        semester = "Fall"

    return {
        "date": now.strftime("%Y-%m-%d"),
        "formatted": now.strftime("%B %d, %Y"),
        "semester": f"{semester} {now.year}",
        "year": now.year,
    }


def check_deadline(deadline_date: str) -> dict:
    """Check if a deadline has passed and categorize its urgency.

    Args:
        deadline_date: The deadline in YYYY-MM-DD format.

    Returns:
        Dict with status (EXPIRED, TODAY, URGENT, UPCOMING, OPEN) and days_remaining.
    """
    if not isinstance(deadline_date, str):
        return {"status": "INVALID", "message": "deadline_date must be a string"}
    try:
        deadline = datetime.strptime(deadline_date, "%Y-%m-%d").date()
    except ValueError:
        return {"status": "INVALID", "message": f"Could not parse date: {deadline_date}"}

    today = datetime.now(_local_tz()).date()
    delta = (deadline - today).days

    if delta < 0:
        return {"status": "EXPIRED", "days_remaining": delta}
    elif delta == 0:
        return {"status": "TODAY", "days_remaining": 0}
    elif delta <= 7:
        return {"status": "URGENT", "days_remaining": delta}
    elif delta <= 30:
        return {"status": "UPCOMING", "days_remaining": delta}
    else:
        return {"status": "OPEN", "days_remaining": delta}
