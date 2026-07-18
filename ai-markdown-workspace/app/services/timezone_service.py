"""
Timezone service for AI Markdown Workspace.
All timestamps stored as UTC, displayed in WIB (Asia/Jakarta, UTC+7).
"""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


# Fixed WIB (UTC+7) — no DST
WIB = ZoneInfo('Asia/Jakarta')
WIB_OFFSET = timedelta(hours=7)


def utc_now() -> datetime:
    """
    Get current time in UTC for database storage.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def to_wib(dt: datetime) -> datetime:
    """
    Convert UTC datetime to WIB (Western Indonesian Time).
    
    Args:
        dt: Datetime in UTC (with or without timezone info)
        
    Returns:
        datetime: Datetime converted to WIB timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(WIB)


def wib_now() -> datetime:
    """
    Get current time in WIB.
    
    Returns:
        datetime: Current WIB time
    """
    return to_wib(utc_now())


def format_wib(dt: datetime, with_seconds: bool = False) -> str:
    """
    Format datetime as WIB string for display.
    
    Args:
        dt: Datetime to format (assumed UTC if naive)
        with_seconds: Include seconds in output
        
    Returns:
        str: Formatted datetime string with 'WIB' suffix
             Example: '2026-07-18 14:30:45 WIB' or '2026-07-18 14:30 WIB'
    """
    wib_dt = to_wib(dt)
    fmt = "%Y-%m-%d %H:%M:%S" if with_seconds else "%Y-%m-%d %H:%M"
    return f"{wib_dt.strftime(fmt)} WIB"


def format_wib_relative(dt: datetime) -> str:
    """
    Format datetime as relative time in WIB.
    
    Args:
        dt: Datetime to format (assumed UTC if naive)
        
    Returns:
        str: Relative time string like '2 minutes ago', 'yesterday at 14:30'
    """
    wib_dt = to_wib(dt)
    now_wib = wib_now()
    diff = now_wib - wib_dt
    
    total_seconds = int(diff.total_seconds())
    
    if total_seconds < 0:
        return "just now"
    elif total_seconds < 60:
        return f"{total_seconds} seconds ago"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif total_seconds < 172800:  # 2 days
        return f"yesterday at {wib_dt.strftime('%H:%M')}"
    else:
        return wib_dt.strftime("%Y-%m-%d %H:%M")


def from_iso_utc(iso_str: str) -> datetime:
    """
    Parse ISO 8601 UTC string from database.
    
    Args:
        iso_str: ISO 8601 formatted string (e.g., '2026-07-18T07:30:45Z' or '2026-07-18T07:30:45+00:00')
        
    Returns:
        datetime: Parsed datetime with UTC timezone info
    """
    if not iso_str:
        return utc_now()
    
    # Handle 'Z' suffix
    if iso_str.endswith('Z'):
        iso_str = iso_str[:-1] + '+00:00'
    
    # Handle missing timezone (assume UTC)
    if '+' not in iso_str and '-' not in iso_str[10:]:
        iso_str += '+00:00'
    
    return datetime.fromisoformat(iso_str).replace(tzinfo=timezone.utc)


def to_iso_utc(dt: datetime) -> str:
    """
    Convert datetime to ISO 8601 UTC string for database storage.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        str: ISO 8601 formatted UTC string
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.isoformat().replace('+00:00', 'Z')


# Jinja2 filter functions for template usage
def jinja_wib_filter(dt: datetime) -> str:
    """Jinja2 filter: Convert UTC datetime to formatted WIB string."""
    if isinstance(dt, str):
        dt = from_iso_utc(dt)
    return format_wib(dt)


def jinja_from_iso_filter(iso_str: str) -> datetime:
    """Jinja2 filter: Parse ISO UTC string to datetime."""
    return from_iso_utc(iso_str)


def jinja_wib_relative_filter(dt: datetime) -> str:
    """Jinja2 filter: Convert UTC datetime to relative WIB string."""
    if isinstance(dt, str):
        dt = from_iso_utc(dt)
    return format_wib_relative(dt)
