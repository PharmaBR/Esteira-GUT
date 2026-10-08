"""What a task is allowed to do, and when.

Pure Python: the Django models ask these functions for permission before
changing state, and show a RuleViolation's message to the user as-is.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, StrEnum

from .scoring import Effort


class RuleViolation(Exception):
    """An action the esteira does not allow. The message is written for the user."""


class Mode(StrEnum):
    CLASSIC = "classic"
    ENHANCED = "enhanced"


class Status(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    DONE = "done"
    DISCARDED = "discarded"


TRANSITIONS: dict[Mode, dict[Status, frozenset[Status]]] = {
    Mode.CLASSIC: {
        Status.QUEUED: frozenset({Status.RUNNING}),
        Status.RUNNING: frozenset({Status.DONE, Status.QUEUED}),
    },
    # Leaving the slot unfinished must say why (pause or block); there is no silent return.
    Mode.ENHANCED: {
        Status.QUEUED: frozenset({Status.RUNNING, Status.BLOCKED, Status.DISCARDED}),
        Status.RUNNING: frozenset({Status.DONE, Status.PAUSED, Status.BLOCKED}),
        Status.PAUSED: frozenset({Status.RUNNING, Status.BLOCKED, Status.DISCARDED}),
        Status.BLOCKED: frozenset({Status.QUEUED, Status.DISCARDED}),
    },
}

# Still someone's problem: these count against the ceiling.
OPEN_STATUSES = frozenset({Status.QUEUED, Status.RUNNING, Status.PAUSED, Status.BLOCKED})


def ensure_transition(mode: Mode, current: Status, target: Status) -> None:
    if target not in TRANSITIONS[mode].get(current, frozenset()):
        raise RuleViolation("Essa ação não está disponível para a tarefa no estado atual.")


def ensure_slot_free(running: int) -> None:
    """The esteira has a single slot: finish (or release) before pulling again."""
    if running:
        raise RuleViolation("Já existe uma tarefa em execução. Conclua-a antes de puxar a próxima.")


def ensure_reason(reason: str | None) -> str:
    """Blocking and pausing are only useful if we know why they happened."""
    reason = (reason or "").strip()
    if not reason:
        raise RuleViolation("Diga o motivo em poucas palavras.")
    return reason


class Verdict(Enum):
    ADMIT = "admit"
    DELEGATE = "delegate"
    DISCARD = "discard"


def triage(*, important: bool, mine: bool) -> Verdict:
    """The door of the esteira: only what is important and yours gets in."""
    if not important:
        return Verdict.DISCARD
    return Verdict.ADMIT if mine else Verdict.DELEGATE


def ensure_capacity(open_tasks: int, limit: int) -> None:
    if open_tasks >= limit:
        raise RuleViolation(
            f"A esteira está cheia ({open_tasks} de {limit}). "
            "Conclua ou descarte algo antes de aceitar mais uma tarefa."
        )


@dataclass(frozen=True)
class Accuracy:
    total: int = 0
    on_target: int = 0
    underestimated: int = 0  # took longer than estimated
    overestimated: int = 0  # took less than estimated


def estimate_accuracy(pairs: Iterable[tuple[Effort, Effort]]) -> Accuracy:
    """Compare (estimated, actual) effort sizes of finished tasks."""
    total = on_target = under = over = 0
    for estimated, actual in pairs:
        total += 1
        if actual.weight > estimated.weight:
            under += 1
        elif actual.weight < estimated.weight:
            over += 1
        else:
            on_target += 1
    return Accuracy(total, on_target, under, over)
