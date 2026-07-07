from datetime import datetime, timezone
from dateutil import parser

def now_utc() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)

def to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string."""
    return dt.isoformat()

def from_iso(s: str) -> datetime:
    """Parse ISO 8601 string back to datetime."""
    return parser.isoparse(s)

def elapsed_seconds(start: datetime, end: datetime) -> float:
    """Calculate elapsed time in seconds between two datetimes."""
    return (end - start).total_seconds()
