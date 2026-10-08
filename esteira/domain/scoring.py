"""How the esteira decides what comes next.

Pure Python on purpose: nothing here imports Django, so every rule can be
tested in isolation and read without knowing the web layer.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
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


# What each rating means. Concrete on purpose: a scale without anchors drifts to 3 or to 5.
# The urgency anchors mirror DEADLINE_URGENCY below, so a guess and a date agree.
ANCHORS = {
    "gravity": {
        1: "ninguém nota se não for feito",
        2: "incômodo pequeno, fácil de reverter",
        3: "prejuízo real, mas recuperável",
        4: "prejuízo grande ou difícil de reverter",
        5: "dano irreversível ou que atinge outras pessoas",
    },
    "urgency": {
        1: "pode esperar mais de duas semanas",
        2: "cabe nas próximas duas semanas",
        3: "precisa sair nesta semana",
        4: "precisa sair em um ou dois dias",
        5: "precisa sair hoje",
    },
    "trend": {
        1: "não piora com o tempo",
        2: "piora devagar, ao longo de meses",
        3: "piora em semanas",
        4: "piora em dias",
        5: "piora a cada hora",
    },
}


class Effort(StrEnum):
    """T-shirt sizes for how long a task takes.

    Coarse on purpose: people estimate sizes far better than minutes, and
    the weight (a Fibonacci-like scale, as in WSJF) keeps a ten-minute task
    from outweighing a day-long one 48 to 1.
    """

    XS = "xs"
    S = "s"
    M = "m"
    L = "l"
    XL = "xl"

    @property
    def weight(self) -> int:
        return _EFFORT[self][0]

    @property
    def max_minutes(self) -> int | None:
        return _EFFORT[self][1]

    @property
    def label(self) -> str:
        return _EFFORT[self][2]


_EFFORT = {
    Effort.XS: (1, 15, "até 15 min"),
    Effort.S: (2, 60, "até 1 hora"),
    Effort.M: (3, 240, "até meio período"),
    Effort.L: (5, 480, "até um dia"),
    Effort.XL: (8, None, "mais de um dia"),
}


def effort_for_minutes(minutes: float) -> Effort:
    for effort in Effort:
        if effort.max_minutes is None or minutes <= effort.max_minutes:
            return effort
    raise AssertionError("unreachable: the last size has no upper bound")


# Days left until the deadline -> urgency. Due today or overdue is a 5.
DEADLINE_URGENCY = ((0, 5), (2, 4), (7, 3), (14, 2))


def urgency_from_deadline(due_date: date, today: date) -> int:
    days_left = (due_date - today).days
    for limit, urgency in DEADLINE_URGENCY:
        if days_left <= limit:
            return urgency
    return MIN_RATING


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
    urgency_from_deadline: bool = False
    crisis: bool = False
    effort: Effort | None = None
    weeks_waiting: int = 0
    aging_bonus: float = 0


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


@dataclass(frozen=True)
class EnhancedGUT:
    """The audited esteira. Each step answers one finding in docs/auditoria.md.

    The two numbers below are design choices, not constants from the literature;
    they are parameters so they can be tuned once real usage data exists.
    """

    aging_points_per_week: float = 2
    effort_when_unknown: Effort = Effort.M

    def priority(self, task: Rankable, now: datetime) -> Priority:
        # R1: with a deadline, urgency is computed instead of guessed.
        from_deadline = task.due_date is not None
        urgency = (
            urgency_from_deadline(task.due_date, now.date()) if from_deadline else task.urgency
        )
        gut = gut_score(task.gravity, urgency, task.trend)

        # R2: maximum gravity and urgency jump the queue regardless of the product.
        crisis = task.gravity == MAX_RATING and urgency == MAX_RATING

        # R3: value per unit of effort, so a quick win is not stuck behind a marathon.
        effort = Effort(task.effort) if task.effort else self.effort_when_unknown

        # R5: every full week waiting adds a fixed bonus, so nothing starves.
        weeks_waiting = max(0, (now - task.created_at).days // 7)
        aging_bonus = weeks_waiting * self.aging_points_per_week

        score = gut / effort.weight + aging_bonus
        return Priority(
            score=score,
            gut=gut,
            urgency=urgency,
            urgency_from_deadline=from_deadline,
            crisis=crisis,
            effort=effort,
            weeks_waiting=weeks_waiting,
            aging_bonus=aging_bonus,
            # R4: ties go to the earlier deadline, then to the older task.
            sort_key=(not crisis, -score, task.due_date or date.max, task.created_at),
        )

    def rank(self, tasks: Iterable[Rankable], now: datetime) -> list[Ranked]:
        return _rank(self, tasks, now)


def _rank(policy, tasks: Iterable[Rankable], now: datetime) -> list[Ranked]:
    ranked = [Ranked(task, policy.priority(task, now)) for task in tasks]
    ranked.sort(key=lambda item: item.priority.sort_key)
    return ranked
