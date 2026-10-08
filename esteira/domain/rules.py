"""What a task is allowed to do, and when.

Pure Python: the Django models ask these functions for permission before
changing state, and show a RuleViolation's message to the user as-is.
"""

from __future__ import annotations

from enum import StrEnum


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
}


def ensure_transition(mode: Mode, current: Status, target: Status) -> None:
    if target not in TRANSITIONS[mode].get(current, frozenset()):
        raise RuleViolation("Essa ação não está disponível para a tarefa no estado atual.")


def ensure_slot_free(running: int) -> None:
    """The esteira has a single slot: finish (or release) before pulling again."""
    if running:
        raise RuleViolation("Já existe uma tarefa em execução. Conclua-a antes de puxar a próxima.")
