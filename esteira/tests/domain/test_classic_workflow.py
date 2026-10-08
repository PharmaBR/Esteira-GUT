"""One slot in execution; tasks move queue -> running -> done."""

import pytest

from esteira.domain.rules import Mode, RuleViolation, Status, ensure_slot_free, ensure_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (Status.QUEUED, Status.RUNNING),
        (Status.RUNNING, Status.DONE),
        (Status.RUNNING, Status.QUEUED),
    ],
)
def test_classic_allows_the_basic_flow(current, target):
    ensure_transition(Mode.CLASSIC, current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (Status.QUEUED, Status.DONE),
        (Status.DONE, Status.RUNNING),
        (Status.QUEUED, Status.BLOCKED),
        (Status.RUNNING, Status.PAUSED),
    ],
)
def test_classic_rejects_everything_else(current, target):
    with pytest.raises(RuleViolation):
        ensure_transition(Mode.CLASSIC, current, target)


def test_slot_is_free_when_nothing_is_running():
    ensure_slot_free(running=0)


def test_only_one_task_runs_at_a_time():
    with pytest.raises(RuleViolation):
        ensure_slot_free(running=1)
