"""How the esteira decides what comes next.

Pure Python on purpose: nothing here imports Django, so every rule can be
tested in isolation and read without knowing the web layer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

MIN_RATING = 1
MAX_RATING = 5


class InvalidRating(ValueError):
    """A G, U or T rating outside the 1-5 scale."""


def gut_score(gravity: int, urgency: int, trend: int) -> int:
    for rating in (gravity, urgency, trend):
        if not MIN_RATING <= rating <= MAX_RATING:
            raise InvalidRating(f"Notas GUT vão de {MIN_RATING} a {MAX_RATING}; recebi {rating}.")
    return gravity * urgency * trend


class Rankable(Protocol):
    """What a policy needs to know about a task. The Django model satisfies it."""

    gravity: int
    urgency: int
    trend: int
    created_at: datetime
    due_date: date | None
    effort: str


@dataclass(frozen=True)
class Priority:
    """A task's place in the queue, with the parts that produced it."""

    score: float
    gut: int
    urgency: int
    sort_key: tuple[Any, ...]


@dataclass(frozen=True)
class Ranked:
    task: Any
    priority: Priority


class ClassicGUT:
    """The original esteira: highest G x U x T first, ties in arrival order."""

    def priority(self, task: Rankable, now: datetime) -> Priority:
        score = gut_score(task.gravity, task.urgency, task.trend)
        return Priority(
            score=score,
            gut=score,
            urgency=task.urgency,
            sort_key=(-score, task.created_at),
        )

    def rank(self, tasks: Iterable[Rankable], now: datetime) -> list[Ranked]:
        return _rank(self, tasks, now)


def _rank(policy, tasks: Iterable[Rankable], now: datetime) -> list[Ranked]:
    ranked = [Ranked(task, policy.priority(task, now)) for task in tasks]
    ranked.sort(key=lambda item: item.priority.sort_key)
    return ranked
