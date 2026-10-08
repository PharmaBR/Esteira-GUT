"""The classic esteira end to end: models and the HTTP surface."""

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from esteira.boards.models import Board, Task
from esteira.domain.rules import RuleViolation, Status

from .conftest import HTMX

pytestmark = pytest.mark.django_db


# ── Model behaviour ────────────────────────────────────────────────


def test_pull_next_starts_the_highest_score(classic, add_task):
    add_task(classic, "baixa", g=1, u=1, t=1)
    top = add_task(classic, "alta", g=5, u=5, t=5)

    started = classic.pull_next(timezone.now())

    assert started == top
    assert classic.running_task() == top
    assert started.started_at is not None


def test_cannot_pull_while_a_task_is_running(classic, add_task):
    add_task(classic, "a", g=5)
    add_task(classic, "b")
    classic.pull_next(timezone.now())

    with pytest.raises(RuleViolation):
        classic.pull_next(timezone.now())

    assert classic.tasks.filter(status=Status.RUNNING).count() == 1


def test_database_refuses_a_second_running_task(classic, add_task):
    add_task(classic, "a", status=Status.RUNNING)

    with pytest.raises(IntegrityError), transaction.atomic():
        add_task(classic, "b", status=Status.RUNNING)


def test_database_refuses_ratings_outside_the_scale(classic, add_task):
    with pytest.raises(IntegrityError), transaction.atomic():
        add_task(classic, "fora da escala", g=6)


def test_pulling_from_an_empty_queue_is_refused(classic):
    with pytest.raises(RuleViolation):
        classic.pull_next(timezone.now())


def test_completing_frees_the_slot(classic, add_task):
    add_task(classic, "a", g=5)
    add_task(classic, "b")
    first = classic.pull_next(timezone.now())

    first.complete(timezone.now())
    second = classic.pull_next(timezone.now())

    assert first.status == Status.DONE and first.completed_at is not None
    assert second.title == "b"


def test_returning_a_task_puts_it_back_in_the_queue(classic, add_task):
    add_task(classic, "a")
    task = classic.pull_next(timezone.now())

    task.return_to_queue()

    assert classic.running_task() is None
    assert [item.task for item in classic.ranked_queue(timezone.now())] == [task]


def test_only_queued_tasks_can_be_deleted(classic, add_task):
    add_task(classic, "a")
    task = classic.pull_next(timezone.now())

    with pytest.raises(RuleViolation):
        task.remove()

    assert Task.objects.filter(pk=task.pk).exists()


# ── HTTP surface ───────────────────────────────────────────────────


def test_board_requires_login(client, classic):
    client.logout()

    response = client.get(reverse("board", args=[classic.pk]))

    assert response.status_code == 302
    assert response.url.startswith(reverse("login"))


def test_expired_session_on_htmx_becomes_a_full_redirect(client, classic):
    client.logout()

    response = client.post(reverse("pull-next", args=[classic.pk]), **HTMX)

    assert response.headers["HX-Redirect"].startswith(reverse("login"))


def test_first_visit_creates_the_default_board(client, user):
    response = client.get(reverse("home"))

    board = Board.objects.get(owner=user, mode=Board.Mode.CLASSIC)
    assert response.status_code == 302 and response.url == board.get_absolute_url()


def test_board_page_lists_the_queue_in_priority_order(client, classic, add_task):
    add_task(classic, "Corrigir provas", g=2, u=2, t=2)
    add_task(classic, "Lançar notas", g=5, u=5, t=4)

    html = client.get(classic.get_absolute_url()).content.decode()

    assert html.index("Lançar notas") < html.index("Corrigir provas")
    assert ">100<" in html.replace("\n", "").replace(" ", "")


def test_creating_a_task_over_htmx_returns_the_board_partial(client, classic):
    data = {"title": "Preparar aula", "gravity": 4, "urgency": 5, "trend": 3, "category": "content"}

    response = client.post(reverse("task-create", args=[classic.pk]), data, **HTMX)

    html = response.content.decode()
    assert response.status_code == 200
    assert 'id="board"' in html and "<html" not in html
    task = classic.tasks.get()
    assert (task.title, task.gravity, task.urgency, task.trend) == ("Preparar aula", 4, 5, 3)


def test_creating_a_task_without_javascript_redirects_back(client, classic):
    data = {"title": "Preparar aula", "gravity": 3, "urgency": 3, "trend": 3, "category": "content"}

    response = client.post(reverse("task-create", args=[classic.pk]), data)

    assert response.status_code == 302 and response.url == classic.get_absolute_url()


def test_invalid_task_comes_back_as_422_with_the_typed_values(client, classic):
    data = {"title": "", "gravity": 9, "urgency": 3, "trend": 3, "category": "content"}

    response = client.post(reverse("task-create", args=[classic.pk]), data, **HTMX)

    assert response.status_code == 422
    assert not classic.tasks.exists()
    assert "field-error" in response.content.decode()


def test_new_task_form_defaults_every_rating_to_3(client, classic):
    form = client.get(classic.get_absolute_url()).context["form"]

    assert [field.initial for field in form.rating_fields] == [3, 3, 3]


def test_pull_complete_cycle_over_http(client, classic, add_task):
    task = add_task(classic, "Única")

    client.post(reverse("pull-next", args=[classic.pk]), **HTMX)
    task.refresh_from_db()
    assert task.status == Status.RUNNING

    client.post(reverse("task-complete", args=[task.pk]), **HTMX)
    task.refresh_from_db()
    assert task.status == Status.DONE


def test_breaking_a_rule_answers_409_with_a_message(client, classic, add_task):
    add_task(classic, "a", status=Status.RUNNING)
    add_task(classic, "b")

    response = client.post(reverse("pull-next", args=[classic.pk]), **HTMX)

    assert response.status_code == 409
    assert "Já existe uma tarefa em execução" in response.content.decode()


def test_editing_a_queued_task(client, classic, add_task):
    task = add_task(classic, "Rascunho")
    url = reverse("task-edit", args=[task.pk])

    form_html = client.get(url, **HTMX).content.decode()
    assert 'value="Rascunho"' in form_html

    data = {"title": "Versão final", "gravity": 5, "urgency": 3, "trend": 3, "category": "project"}
    client.post(url, data, **HTMX)
    task.refresh_from_db()
    assert (task.title, task.gravity, task.category) == ("Versão final", 5, "project")


def test_deleting_a_queued_task(client, classic, add_task):
    task = add_task(classic, "Descartável")

    client.post(reverse("task-delete", args=[task.pk]), **HTMX)

    assert not Task.objects.filter(pk=task.pk).exists()


@pytest.mark.parametrize("method", ["get", "post"])
def test_other_peoples_boards_do_not_exist(client, stranger, method):
    theirs = Board.objects.create(owner=stranger, name="Alheia", mode=Board.Mode.CLASSIC)

    response = getattr(client, method)(theirs.get_absolute_url())

    assert response.status_code in (404, 405)
    assert client.post(reverse("pull-next", args=[theirs.pk])).status_code == 404
    assert client.post(reverse("task-create", args=[theirs.pk]), {"title": "x"}).status_code == 404


@pytest.mark.parametrize("action", ["task-complete", "task-return", "task-delete", "task-edit"])
def test_other_peoples_tasks_do_not_exist(client, stranger, add_task, action):
    theirs = Board.objects.create(owner=stranger, name="Alheia", mode=Board.Mode.CLASSIC)
    task = add_task(theirs, "Privada")

    response = client.post(reverse(action, args=[task.pk]))

    assert response.status_code == 404
    task.refresh_from_db()
    assert task.status == Status.QUEUED


def test_state_changes_refuse_get(client, classic, add_task):
    task = add_task(classic, "a")

    assert client.get(reverse("pull-next", args=[classic.pk])).status_code == 405
    assert client.get(reverse("task-delete", args=[task.pk])).status_code == 405


def test_health_endpoint_is_public(client):
    client.logout()

    assert client.get(reverse("health")).content == b"ok"


def test_responses_carry_a_content_security_policy(client, classic):
    policy = client.get(classic.get_absolute_url()).headers["Content-Security-Policy"]

    assert "default-src 'self'" in policy and "unsafe-inline" not in policy
