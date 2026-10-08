"""R11: every level of every scale says what it means."""

from datetime import timedelta

from esteira.domain.scoring import ANCHORS, MAX_RATING, MIN_RATING, urgency_from_deadline

from .factories import NOW

LEVELS = list(range(MIN_RATING, MAX_RATING + 1))


def test_every_scale_describes_every_level():
    assert set(ANCHORS) == {"gravity", "urgency", "trend"}
    for scale, levels in ANCHORS.items():
        assert list(levels) == LEVELS, scale
        assert len(set(levels.values())) == len(LEVELS), f"{scale} repeats a description"


def test_urgency_anchors_agree_with_the_deadline_table():
    """Guessing 'precisa sair hoje' and typing today's date must give the same urgency."""
    today = NOW.date()
    examples = {5: 0, 4: 2, 3: 7, 2: 14, 1: 30}  # days left that each anchor describes

    for urgency, days_left in examples.items():
        assert urgency_from_deadline(today + timedelta(days=days_left), today) == urgency
