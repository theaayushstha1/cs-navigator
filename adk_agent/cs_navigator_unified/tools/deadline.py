"""Date and deadline tools for the Scholarship agent."""

from datetime import datetime, timezone


def get_current_date() -> dict:
    """Get today's date with semester context.

    Returns current date in multiple formats plus the current academic semester.
    """
    now = datetime.now(timezone.utc)
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
    try:
        deadline = datetime.strptime(deadline_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return {"status": "INVALID", "message": f"Could not parse date: {deadline_date}"}

    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    delta = (deadline - now).days

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
