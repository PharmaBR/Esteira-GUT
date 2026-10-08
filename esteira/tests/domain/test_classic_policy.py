"""The original esteira: order by G x U x T, nothing else."""

from datetime import timedelta

import pytest

from esteira.domain.scoring import ClassicGUT, InvalidRating, gut_score

from .factories import NOW, FakeTask


def test_score_is_the_product_of_the_three_ratings():
    assert gut_score(4, 5, 3) == 60


def test_score_ranges_from_1_to_125():
    assert gut_score(1, 1, 1) == 1
    assert gut_score(5, 5, 5) == 125


@pytest.mark.parametrize("ratings", [(0, 3, 3), (3, 6, 3), (3, 3, -1)])
def test_ratings_outside_1_to_5_are_rejected(ratings):
    with pytest.raises(InvalidRating):
        gut_score(*ratings)


def test_queue_is_ordered_by_score_highest_first():
    low = FakeTask(gravity=1, urgency=2, trend=2, name="low")
    high = FakeTask(gravity=5, urgency=5, trend=4, name="high")
    mid = FakeTask(gravity=3, urgency=3, trend=3, name="mid")

    ranked = ClassicGUT().rank([low, high, mid], NOW)

    assert [item.task.name for item in ranked] == ["high", "mid", "low"]
    assert [item.priority.score for item in ranked] == [100, 27, 4]


def test_ties_keep_arrival_order():
    first = FakeTask(created_at=NOW - timedelta(hours=2), name="first")
    second = FakeTask(created_at=NOW - timedelta(hours=1), name="second")

    ranked = ClassicGUT().rank([second, first], NOW)

    assert [item.task.name for item in ranked] == ["first", "second"]


def test_classic_ignores_deadline_and_effort():
    plain = FakeTask(name="plain", created_at=NOW - timedelta(days=1))
    dressed = FakeTask(name="dressed", due_date=NOW.date(), effort="xs")

    ranked = ClassicGUT().rank([dressed, plain], NOW)

    assert [item.task.name for item in ranked] == ["plain", "dressed"]
    assert ranked[0].priority.score == ranked[1].priority.score == 27
