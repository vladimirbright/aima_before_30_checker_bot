"""Utility functions for the application."""

from datetime import datetime
import pytz


def format_timestamp(iso_timestamp: str, timezone_name: str = 'Europe/Lisbon') -> str:
    """
    Format ISO timestamp to human-readable format.

    Args:
        iso_timestamp: ISO format timestamp string
        timezone_name: Timezone name (default: Europe/Lisbon)

    Returns:
        str: Human-readable timestamp
    """
    try:
        # Parse ISO timestamp
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))

        # Convert to specified timezone
        tz = pytz.timezone(timezone_name)
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        dt = dt.astimezone(tz)

        # Calculate time difference
        now = datetime.now(tz)
        diff = now - dt

        # Format based on how recent it is
        total_seconds = diff.total_seconds()

        if total_seconds < 60:
            return "Just now"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = int(total_seconds / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        elif total_seconds < 86400:  # Less than 24 hours
            hours = int(total_seconds / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        else:
            # Format as full date/time
            return dt.strftime("%d %B %Y at %H:%M")

    except Exception:
        # Fallback to original timestamp if parsing fails
        return iso_timestamp
