"""The enhanced policy, one audit finding per group of tests.

Rule numbers (R1...) match docs/auditoria.md.
"""

from datetime import timedelta

import pytest

from esteira.domain.scoring import (
    ClassicGUT,
    Effort,
    EnhancedGUT,
    effort_for_minutes,
    urgency_from_deadline,
)

from .factories import NOW, FakeTask

TODAY = NOW.date()


def names(ranked):
    return [item.task.name for item in ranked]


def due_in(days):
    return TODAY + timedelta(days=days)


# ── R1: urgency comes from the deadline, not from a guess ──────────


@pytest.mark.parametrize(
    ("days_left", "urgency"),
    [(-3, 5), (0, 5), (1, 4), (2, 4), (3, 3), (7, 3), (8, 2), (14, 2), (15, 1), (90, 1)],
)
def test_urgency_follows_the_days_left(days_left, urgency):
    assert urgency_from_deadline(due_in(days_left), TODAY) == urgency


def test_a_deadline_overrides_the_manual_urgency():
    task = FakeTask(gravity=4, urgency=1, trend=3, due_date=due_in(1))

    priority = EnhancedGUT().priority(task, NOW)

    assert priority.urgency == 4
    assert priority.urgency_from_deadline is True
    assert priority.gut == 4 * 4 * 3


def test_without_a_deadline_the_manual_urgency_stands():
    task = FakeTask(gravity=4, urgency=2, trend=3)

    priority = EnhancedGUT().priority(task, NOW)

    assert priority.urgency == 2
    assert priority.urgency_from_deadline is False


def test_urgency_rises_by_itself_as_the_deadline_approaches():
    task = FakeTask(gravity=3, urgency=1, trend=3, due_date=due_in(10), effort="m")
    policy = EnhancedGUT()

    far = policy.priority(task, NOW).score
    near = policy.priority(task, NOW + timedelta(days=9)).score

    assert near > far


# ── R2: grave and urgent jumps the queue, whatever the product says ─


def test_classic_puts_a_stable_crisis_behind_a_merely_bad_task():
    """The flaw being fixed: 4x4x4 = 64 outranks 5x5x2 = 50."""
    crisis = FakeTask(gravity=5, urgency=5, trend=2, name="crisis")
    bad = FakeTask(gravity=4, urgency=4, trend=4, name="bad")

    assert names(ClassicGUT().rank([crisis, bad], NOW)) == ["bad", "crisis"]


def test_enhanced_puts_the_crisis_first():
    crisis = FakeTask(gravity=5, urgency=5, trend=2, effort="m", name="crisis")
    bad = FakeTask(gravity=4, urgency=4, trend=4, effort="m", name="bad")

    ranked = EnhancedGUT().rank([bad, crisis], NOW)

    assert names(ranked) == ["crisis", "bad"]
    assert ranked[0].priority.crisis is True


def test_a_crisis_beats_even_a_quick_high_score():
    crisis = FakeTask(gravity=5, urgency=5, trend=1, effort="xl", name="crisis")
    quick = FakeTask(gravity=5, urgency=4, trend=5, effort="xs", name="quick")

    assert names(EnhancedGUT().rank([quick, crisis], NOW)) == ["crisis", "quick"]


def test_a_deadline_today_can_turn_a_grave_task_into_a_crisis():
    task = FakeTask(gravity=5, urgency=2, trend=1, due_date=TODAY)

    assert EnhancedGUT().priority(task, NOW).crisis is True


def test_grave_alone_or_urgent_alone_is_not_a_crisis():
    policy = EnhancedGUT()

    assert policy.priority(FakeTask(gravity=5, urgency=4, trend=5), NOW).crisis is False
    assert policy.priority(FakeTask(gravity=4, urgency=5, trend=5), NOW).crisis is False


# ── R3: effort divides the score ────────────────────────────────────


def test_classic_lets_a_huge_task_block_a_quick_one():
    """The flaw being fixed: 125 (days of work) outranks 100 (ten minutes)."""
    huge = FakeTask(gravity=5, urgency=5, trend=5, effort="xl", name="huge")
    quick = FakeTask(gravity=5, urgency=4, trend=5, effort="xs", name="quick")

    assert names(ClassicGUT().rank([quick, huge], NOW)) == ["huge", "quick"]


def test_enhanced_ranks_by_score_per_unit_of_effort():
    long = FakeTask(gravity=4, urgency=4, trend=5, effort="xl", name="long")
    quick = FakeTask(gravity=4, urgency=4, trend=4, effort="xs", name="quick")

    ranked = EnhancedGUT().rank([long, quick], NOW)

    assert names(ranked) == ["quick", "long"]
    assert ranked[0].priority.score == 64 / Effort.XS.weight
    assert ranked[1].priority.score == 80 / Effort.XL.weight


def test_bigger_effort_never_raises_priority():
    scores = [EnhancedGUT().priority(FakeTask(effort=effort.value), NOW).score for effort in Effort]

    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores)


def test_a_task_without_an_estimate_is_treated_as_medium():
    unknown = EnhancedGUT().priority(FakeTask(effort=""), NOW)
    medium = EnhancedGUT().priority(FakeTask(effort="m"), NOW)

    assert unknown.score == medium.score


@pytest.mark.parametrize(
    ("minutes", "effort"),
    [(1, Effort.XS), (15, Effort.XS), (16, Effort.S), (60, Effort.S), (61, Effort.M)]
    + [(240, Effort.M), (241, Effort.L), (480, Effort.L), (481, Effort.XL), (5000, Effort.XL)],
)
def test_minutes_map_to_an_effort_size(minutes, effort):
    assert effort_for_minutes(minutes) is effort


# ── R4: ties break by deadline, then by age ─────────────────────────


def test_classic_scale_only_produces_30_distinct_scores():
    """Why ties are the norm: 125 combinations collapse into 30 values."""
    scores = {g * u * t for g in range(1, 6) for u in range(1, 6) for t in range(1, 6)}

    assert len(scores) == 30


def test_equal_scores_go_to_the_earlier_deadline():
    # Both due inside the same urgency band, so their scores are identical.
    later = FakeTask(due_date=due_in(7), effort="m", name="later")
    sooner = FakeTask(due_date=due_in(4), effort="m", name="sooner")

    assert names(EnhancedGUT().rank([later, sooner], NOW)) == ["sooner", "later"]


def test_a_deadline_beats_no_deadline_on_a_tie():
    undated = FakeTask(urgency=3, effort="m", name="undated", created_at=NOW - timedelta(days=2))
    dated = FakeTask(due_date=due_in(5), effort="m", name="dated")

    assert names(EnhancedGUT().rank([undated, dated], NOW)) == ["dated", "undated"]


def test_then_the_older_task_goes_first():
    newer = FakeTask(effort="m", name="newer", created_at=NOW - timedelta(hours=1))
    older = FakeTask(effort="m", name="older", created_at=NOW - timedelta(hours=5))

    assert names(EnhancedGUT().rank([newer, older], NOW)) == ["older", "newer"]


# ── R5: waiting raises priority, so nothing starves ─────────────────


def test_no_bonus_in_the_first_week():
    task = FakeTask(created_at=NOW - timedelta(days=6))

    assert EnhancedGUT().priority(task, NOW).aging_bonus == 0


def test_each_full_week_waiting_adds_the_same_bonus():
    policy = EnhancedGUT(aging_points_per_week=2)

    one = policy.priority(FakeTask(created_at=NOW - timedelta(days=7)), NOW)
    three = policy.priority(FakeTask(created_at=NOW - timedelta(days=22)), NOW)

    assert (one.aging_bonus, three.aging_bonus) == (2, 6)


def test_a_low_task_eventually_overtakes_a_fresh_higher_one():
    stale = FakeTask(gravity=1, urgency=2, trend=2, effort="m", name="stale")
    fresh = FakeTask(gravity=3, urgency=3, trend=3, effort="m", name="fresh")
    policy = EnhancedGUT()

    stale.created_at = NOW - timedelta(weeks=1)
    assert names(policy.rank([stale, fresh], NOW)) == ["fresh", "stale"]

    stale.created_at = NOW - timedelta(weeks=5)
    assert names(policy.rank([stale, fresh], NOW)) == ["stale", "fresh"]


def test_nothing_starves_the_oldest_task_beats_any_new_arrival():
    """Base priority is capped at 125; the bonus is not. So waiting always wins in the end."""
    policy = EnhancedGUT()
    worst = FakeTask(gravity=1, urgency=1, trend=1, effort="xl", name="worst")
    newcomer = FakeTask(gravity=5, urgency=4, trend=5, effort="xs", name="newcomer")

    for weeks in range(1, 200):
        now = NOW + timedelta(weeks=weeks)
        newcomer.created_at = now  # the best possible non-crisis task, arriving this instant
        if names(policy.rank([newcomer, worst], now))[0] == "worst":
            break
    else:
        pytest.fail("the oldest task never reached the top")

    assert weeks <= 52
