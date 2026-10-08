"""States and gates the enhanced esteira adds. Rule numbers match docs/auditoria.md."""

import pytest

from esteira.domain.rules import (
    Mode,
    RuleViolation,
    Status,
    Verdict,
    ensure_capacity,
    ensure_reason,
    ensure_transition,
    estimate_accuracy,
    triage,
)
from esteira.domain.scoring import Effort

S = Status


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.QUEUED, S.RUNNING),
        (S.RUNNING, S.DONE),
        # R6: a task waiting on someone else leaves the slot (or the queue).
        (S.RUNNING, S.BLOCKED),
        (S.QUEUED, S.BLOCKED),
        (S.BLOCKED, S.QUEUED),
        # R9: an interruption is an explicit pause, later resumed.
        (S.RUNNING, S.PAUSED),
        (S.PAUSED, S.RUNNING),
        (S.PAUSED, S.BLOCKED),
        # R8: what will never be done is discarded, not left to rot.
        (S.QUEUED, S.DISCARDED),
        (S.BLOCKED, S.DISCARDED),
        (S.PAUSED, S.DISCARDED),
        # ...and a discard can be taken back, so it needs no "are you sure?".
        (S.DISCARDED, S.QUEUED),
    ],
)
def test_enhanced_transitions(current, target):
    ensure_transition(Mode.ENHANCED, current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        # Leaving the slot without finishing must say why: pause or block, never a silent return.
        (S.RUNNING, S.QUEUED),
        (S.RUNNING, S.DISCARDED),
        (S.BLOCKED, S.RUNNING),
        (S.BLOCKED, S.DONE),
        (S.PAUSED, S.DONE),
        (S.DONE, S.QUEUED),
        (S.DISCARDED, S.RUNNING),
    ],
)
def test_enhanced_forbidden_transitions(current, target):
    with pytest.raises(RuleViolation):
        ensure_transition(Mode.ENHANCED, current, target)


# ── R6 / R9: blocking and pausing must give a reason ────────────────


def test_a_reason_is_returned_trimmed():
    assert ensure_reason("  aguardando a coordenação ") == "aguardando a coordenação"


@pytest.mark.parametrize("reason", ["", "   ", None])
def test_a_missing_reason_is_refused(reason):
    with pytest.raises(RuleViolation):
        ensure_reason(reason)


# ── R7: triage at the door (important? mine?) ───────────────────────


@pytest.mark.parametrize(
    ("important", "mine", "verdict"),
    [
        (True, True, Verdict.ADMIT),
        (True, False, Verdict.DELEGATE),
        (False, True, Verdict.DISCARD),
        (False, False, Verdict.DISCARD),
    ],
)
def test_triage(important, mine, verdict):
    assert triage(important=important, mine=mine) is verdict


# ── R8: the queue has a ceiling ─────────────────────────────────────


def test_there_is_room_below_the_limit():
    ensure_capacity(open_tasks=19, limit=20)


@pytest.mark.parametrize("open_tasks", [20, 25])
def test_a_full_esteira_refuses_new_tasks(open_tasks):
    with pytest.raises(RuleViolation, match="20"):
        ensure_capacity(open_tasks=open_tasks, limit=20)


# ── R10: compare what was estimated with what happened ──────────────


def test_estimate_accuracy_counts_hits_and_misses():
    pairs = [
        (Effort.S, Effort.S),
        (Effort.S, Effort.L),  # took longer than estimated
        (Effort.XS, Effort.M),  # took longer than estimated
        (Effort.L, Effort.M),  # took less
    ]

    accuracy = estimate_accuracy(pairs)

    assert (
        accuracy.total,
        accuracy.on_target,
        accuracy.underestimated,
        accuracy.overestimated,
    ) == (
        4,
        1,
        2,
        1,
    )


def test_estimate_accuracy_with_no_history():
    assert estimate_accuracy([]).total == 0
