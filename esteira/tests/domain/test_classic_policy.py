"""The original esteira: order by G x U x T, nothing else."""

from datetime import timedelta

import pytest

from esteira.domain.scoring import BANDS, ClassicGUT, InvalidRating, band_for, gut_score

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


# The original's help text: "Em empate, vem antes a de prazo mais próximo."


def test_ties_go_to_the_nearest_deadline():
    later = FakeTask(due_date=NOW.date() + timedelta(days=9), name="later")
    sooner = FakeTask(due_date=NOW.date() + timedelta(days=2), name="sooner")

    ranked = ClassicGUT().rank([later, sooner], NOW)

    assert [item.task.name for item in ranked] == ["sooner", "later"]


def test_on_a_tie_a_deadline_comes_before_no_deadline():
    undated = FakeTask(created_at=NOW - timedelta(days=3), name="undated")
    dated = FakeTask(due_date=NOW.date() + timedelta(days=30), name="dated")

    ranked = ClassicGUT().rank([undated, dated], NOW)

    assert [item.task.name for item in ranked] == ["dated", "undated"]


def test_remaining_ties_keep_arrival_order():
    first = FakeTask(created_at=NOW - timedelta(hours=2), name="first")
    second = FakeTask(created_at=NOW - timedelta(hours=1), name="second")

    ranked = ClassicGUT().rank([second, first], NOW)

    assert [item.task.name for item in ranked] == ["first", "second"]


def test_a_deadline_never_outranks_a_higher_score():
    urgent_date = FakeTask(gravity=2, urgency=2, trend=2, due_date=NOW.date(), name="due today")
    higher = FakeTask(gravity=3, urgency=3, trend=3, name="higher")

    ranked = ClassicGUT().rank([urgent_date, higher], NOW)

    assert [item.task.name for item in ranked] == ["higher", "due today"]


def test_classic_ignores_effort():
    quick = FakeTask(effort="xs", name="quick", created_at=NOW - timedelta(hours=1))
    long = FakeTask(effort="xl", name="long", created_at=NOW - timedelta(hours=2))

    ranked = ClassicGUT().rank([quick, long], NOW)

    assert [item.task.name for item in ranked] == ["long", "quick"]
    assert ranked[0].priority.score == ranked[1].priority.score == 27


# The original's legend: what a score means, in words.


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (125, "fazer já"),
        (75, "fazer já"),
        (74, "nesta semana"),
        (40, "nesta semana"),
        (39, "agendar"),
        (20, "agendar"),
        (19, "quando sobrar tempo"),
        (1, "quando sobrar tempo"),
    ],
)
def test_every_score_falls_in_a_named_band(score, label):
    assert band_for(score).label == label


def test_bands_cover_the_whole_scale_without_gaps():
    labels = [band_for(score).label for score in range(1, 126)]

    assert len(set(labels)) == len(BANDS) == 4
    assert labels == sorted(labels, key=[band.label for band in reversed(BANDS)].index)


def test_classic_priority_carries_its_band():
    priority = ClassicGUT().priority(FakeTask(gravity=5, urgency=4, trend=4), NOW)

    assert (priority.score, priority.band.label) == (80, "fazer já")
