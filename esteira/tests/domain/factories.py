"""Plain-Python stand-ins for tasks, so domain tests never touch Django."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

NOW = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)


@dataclass
class FakeTask:
    gravity: int = 3
    urgency: int = 3
    trend: int = 3
    created_at: datetime = NOW
    due_date: date | None = None
    effort: str = ""
    name: str = ""
