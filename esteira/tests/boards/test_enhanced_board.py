"""The enhanced esteira end to end. Rule numbers match docs/auditoria.md."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from esteira.boards.models import Board, Task
from esteira.domain.rules import RuleViolation, Status

from .conftest import HTMX

pytestmark = pytest.mark.django_db


def titles(board):
    return [item.task.title for item in board.ranked_queue(timezone.localtime())]


def new_task(**overrides):
    data = {
        "title": "Montar prova",
        "gravity": 4,
        "trend": 3,
        "urgency": 3,
        "effort": "m",
        "category": "assessment",
        "important": "on",
        "mine": "on",
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


# ── The two versions live side by side ──────────────────────────────


def test_first_visit_creates_both_versions(client, user):
    client.get(reverse("home"))

    assert set(Board.objects.filter(owner=user).values_list("mode", flat=True)) == {
        "classic",
        "enhanced",
    }


def test_each_board_ranks_by_its_own_policy(classic, enhanced, add_task):
    for board in (classic, enhanced):
        add_task(board, "maratona", g=5, u=4, t=5, effort="xl")
        add_task(board, "rápida", g=4, u=4, t=4, effort="xs")

    assert titles(classic) == ["maratona", "rápida"]
    assert titles(enhanced) == ["rápida", "maratona"]


def test_each_board_has_its_own_slot(classic, enhanced, add_task):
    add_task(classic, "a")
    add_task(enhanced, "b", effort="s")

    classic.pull_next(timezone.now())
    enhanced.pull_next(timezone.now())

    assert Task.objects.filter(status=Status.RUNNING).count() == 2


# ── R1 + R3: the form asks for a deadline or an urgency, and an effort ─


def test_new_task_form_has_no_default_ratings(client, enhanced):
    form = client.get(enhanced.get_absolute_url()).context["form"]

    assert [form[name].initial for name in ("gravity", "urgency", "trend", "effort")] == [None] * 4


def test_a_deadline_replaces_the_urgency_question(client, enhanced):
    due = timezone.localdate() + timedelta(days=1)
    data = new_task(urgency=None, due_date=due.isoformat())

    response = client.post(reverse("task-create", args=[enhanced.pk]), data, **HTMX)

    assert response.status_code == 200
    task = enhanced.tasks.get()
    assert task.due_date == due
    assert task.urgency == 4  # one day left


def test_without_deadline_or_urgency_the_task_is_refused(client, enhanced):
    response = client.post(
        reverse("task-create", args=[enhanced.pk]), new_task(urgency=None), **HTMX
    )

    assert response.status_code == 422
    assert "prazo ou a urgência" in response.content.decode()
    assert not enhanced.tasks.exists()


def test_effort_is_required(client, enhanced):
    response = client.post(reverse("task-create", args=[enhanced.pk]), new_task(effort=""), **HTMX)

    assert response.status_code == 422
    assert not enhanced.tasks.exists()


# ── R7: triage at the door ──────────────────────────────────────────


@pytest.mark.parametrize(
    ("answers", "advice"),
    [
        ({"important": None}, "descarte"),
        ({"mine": None}, "delegue"),
    ],
)
def test_triage_refuses_what_is_not_important_or_not_mine(client, enhanced, answers, advice):
    response = client.post(reverse("task-create", args=[enhanced.pk]), new_task(**answers), **HTMX)

    assert response.status_code == 422
    assert advice in response.content.decode().lower()
    assert not enhanced.tasks.exists()


def test_editing_does_not_repeat_the_triage(client, enhanced, add_task):
    task = add_task(enhanced, "Rascunho", effort="s")
    data = new_task(title="Final", important=None, mine=None)

    client.post(reverse("task-edit", args=[task.pk]), data, **HTMX)

    task.refresh_from_db()
    assert task.title == "Final"


# ── R8: the ceiling ─────────────────────────────────────────────────


def test_a_full_esteira_refuses_new_tasks_and_keeps_what_was_typed(client, enhanced, add_task):
    enhanced.queue_limit = 2
    enhanced.save()
    add_task(enhanced, "a", effort="s")
    add_task(enhanced, "b", effort="s", status=Status.BLOCKED, status_reason="aguardando")

    response = client.post(reverse("task-create", args=[enhanced.pk]), new_task(), **HTMX)

    html = response.content.decode()
    assert response.status_code == 409
    assert "cheia" in html and 'value="Montar prova"' in html
    assert enhanced.tasks.count() == 2


def test_done_and_discarded_tasks_do_not_count_against_the_ceiling(client, enhanced, add_task):
    enhanced.queue_limit = 1
    enhanced.save()
    add_task(enhanced, "feita", effort="s", status=Status.DONE)
    add_task(enhanced, "descartada", effort="s", status=Status.DISCARDED)

    response = client.post(reverse("task-create", args=[enhanced.pk]), new_task(), **HTMX)

    assert response.status_code == 200


def test_the_classic_esteira_has_no_ceiling(client, classic, add_task):
    classic.queue_limit = 1
    classic.save()
    add_task(classic, "a")
    data = {"title": "b", "gravity": 3, "urgency": 3, "trend": 3, "category": "content"}

    assert client.post(reverse("task-create", args=[classic.pk]), data, **HTMX).status_code == 200


# ── R6: blocked ─────────────────────────────────────────────────────


def test_blocking_the_running_task_frees_the_slot(enhanced, add_task):
    add_task(enhanced, "depende de terceiros", g=5, effort="s")
    add_task(enhanced, "posso fazer", effort="s")
    now = timezone.now()
    stuck = enhanced.pull_next(now)

    stuck.block(now, "aguardando a coordenação")
    following = enhanced.pull_next(now)

    assert (stuck.status, stuck.status_reason) == (Status.BLOCKED, "aguardando a coordenação")
    assert following.title == "posso fazer"


def test_a_blocked_task_is_skipped_until_unblocked(enhanced, add_task):
    blocked = add_task(enhanced, "bloqueada", g=5, effort="s")
    add_task(enhanced, "livre", effort="s")
    blocked.block(timezone.now(), "aguardando")

    assert titles(enhanced) == ["livre"]

    blocked.unblock()

    assert titles(enhanced) == ["bloqueada", "livre"]
    assert blocked.status_reason == ""


def test_blocking_needs_a_reason(client, enhanced, add_task):
    task = add_task(enhanced, "a", effort="s")

    response = client.post(reverse("task-block", args=[task.pk]), {"reason": "  "}, **HTMX)

    task.refresh_from_db()
    assert response.status_code == 409 and task.status == Status.QUEUED


def test_classic_has_no_blocked_state(client, classic, add_task):
    task = add_task(classic, "a")

    with pytest.raises(RuleViolation):
        task.block(timezone.now(), "motivo")


# ── R9: explicit pause, counted ─────────────────────────────────────


def test_pausing_frees_the_slot_and_counts_the_interruption(enhanced, add_task):
    add_task(enhanced, "foco", g=5, u=4, t=5, effort="xs")
    add_task(enhanced, "emergência", effort="xs")
    start = timezone.now()
    focus = enhanced.pull_next(start)

    focus.pause(start + timedelta(minutes=20), "aluno na porta")
    emergency = enhanced.pull_next(start + timedelta(minutes=20))

    assert (focus.status, focus.interruptions, focus.status_reason) == (
        Status.PAUSED,
        1,
        "aluno na porta",
    )
    assert focus.worked_seconds == 20 * 60
    assert emergency.title == "emergência"


def test_resuming_needs_the_slot(enhanced, add_task):
    add_task(enhanced, "foco", g=5, u=4, t=5, effort="xs")
    add_task(enhanced, "emergência", effort="xs")
    now = timezone.now()
    focus = enhanced.pull_next(now)
    focus.pause(now, "interrupção")
    emergency = enhanced.pull_next(now)

    with pytest.raises(RuleViolation):
        focus.resume(now)

    emergency.complete(now)
    focus.resume(now)
    assert focus.status == Status.RUNNING and focus.status_reason == ""


def test_time_worked_adds_up_across_pauses(enhanced, add_task):
    add_task(enhanced, "longa", effort="m")
    t0 = timezone.now()
    task = enhanced.pull_next(t0)
    task.pause(t0 + timedelta(minutes=30), "almoço")
    task.resume(t0 + timedelta(minutes=90))

    task.complete(t0 + timedelta(minutes=100))

    assert task.worked_seconds == 40 * 60
    assert task.measured_effort(t0 + timedelta(minutes=100)).value == "s"


def test_enhanced_has_no_silent_return_to_queue(client, enhanced, add_task):
    add_task(enhanced, "a", effort="s")
    task = enhanced.pull_next(timezone.now())

    response = client.post(reverse("task-return", args=[task.pk]), **HTMX)

    task.refresh_from_db()
    assert response.status_code == 409 and task.status == Status.RUNNING


# ── R8 (continued): discarding ──────────────────────────────────────


def test_discarding_keeps_the_record_but_leaves_the_queue(client, enhanced, add_task):
    task = add_task(enhanced, "não vale mais a pena", effort="s")

    client.post(reverse("task-discard", args=[task.pk]), **HTMX)

    task.refresh_from_db()
    assert task.status == Status.DISCARDED
    assert titles(enhanced) == []


# ── R10: feedback at completion ─────────────────────────────────────


def test_completing_asks_for_actual_effort_and_priority_verdict(client, enhanced, add_task):
    add_task(enhanced, "a", effort="s")
    task = enhanced.pull_next(timezone.now())

    response = client.post(reverse("task-complete", args=[task.pk]), {}, **HTMX)

    task.refresh_from_db()
    assert response.status_code == 422 and task.status == Status.RUNNING


def test_completing_records_the_feedback(client, enhanced, add_task):
    add_task(enhanced, "a", effort="s")
    task = enhanced.pull_next(timezone.now())

    client.post(
        reverse("task-complete", args=[task.pk]),
        {"actual_effort": "l", "priority_verdict": "late"},
        **HTMX,
    )

    task.refresh_from_db()
    assert (task.status, task.actual_effort, task.priority_verdict) == (Status.DONE, "l", "late")


def test_weekly_review_summarises_the_feedback(client, enhanced, add_task):
    now = timezone.now()
    done = {"status": Status.DONE, "completed_at": now}
    add_task(enhanced, "no alvo", effort="s", actual_effort="s", priority_verdict="right", **done)
    add_task(enhanced, "estourou", effort="s", actual_effort="l", priority_verdict="late", **done)
    add_task(enhanced, "parada", effort="s", created_at=now - timedelta(weeks=3))
    add_task(enhanced, "travada", effort="s", status=Status.BLOCKED, status_reason="sem resposta")

    response = client.get(reverse("review", args=[enhanced.pk]))

    review = response.context["review"]
    assert response.status_code == 200
    assert review["done_this_week"] == 2
    assert (review["accuracy"].on_target, review["accuracy"].underestimated) == (1, 1)
    assert review["verdicts"] == {"right": 1, "late": 1, "early": 0}
    assert [item.task.title for item in review["stale"]] == ["parada"]
    assert [task.title for task in review["blocked"]] == ["travada"]


def test_the_classic_esteira_has_no_review(client, classic):
    assert client.get(reverse("review", args=[classic.pk])).status_code == 404


# ── Privacy holds for the new actions too ───────────────────────────


@pytest.mark.parametrize(
    "action", ["task-block", "task-unblock", "task-pause", "task-resume", "task-discard"]
)
def test_other_peoples_tasks_do_not_exist(client, stranger, add_task, action):
    theirs = Board.objects.create(owner=stranger, name="Alheia", mode=Board.Mode.ENHANCED)
    task = add_task(theirs, "Privada", effort="s")

    response = client.post(reverse(action, args=[task.pk]), {"reason": "x"})

    task.refresh_from_db()
    assert response.status_code == 404 and task.status == Status.QUEUED


def test_other_peoples_review_does_not_exist(client, stranger):
    theirs = Board.objects.create(owner=stranger, name="Alheia", mode=Board.Mode.ENHANCED)

    assert client.get(reverse("review", args=[theirs.pk])).status_code == 404
