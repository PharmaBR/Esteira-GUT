"""What the original's own help text promises, checked on the classic board.

Source: the "Como usar a esteira" panel of the original artifact.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from esteira.domain.rules import Status

from .conftest import HTMX

pytestmark = pytest.mark.django_db


def test_a_tie_goes_to_the_nearest_deadline(classic, add_task):
    """ "Em empate, vem antes a de prazo mais próximo." """
    today = timezone.localdate()
    add_task(classic, "sem prazo")
    add_task(classic, "prazo distante", due_date=today + timedelta(days=20))
    add_task(classic, "prazo próximo", due_date=today + timedelta(days=1))

    queue = [item.task.title for item in classic.ranked_queue(timezone.localtime())]

    assert queue == ["prazo próximo", "prazo distante", "sem prazo"]


def test_every_queued_task_says_what_its_score_means(client, classic, add_task):
    """The legend: 75-125 fazer já, 40-74 nesta semana, 20-39 agendar, 1-19 quando sobrar tempo."""
    add_task(classic, "a", g=5, u=5, t=4)  # 100
    add_task(classic, "b", g=4, u=4, t=3)  # 48
    add_task(classic, "c", g=3, u=3, t=3)  # 27
    add_task(classic, "d", g=2, u=2, t=2)  # 8

    html = client.get(classic.get_absolute_url()).content.decode()
    queue = html[html.index('id="h-queue"') :]

    positions = [
        queue.index(label)
        for label in ("Fazer já", "Nesta semana", "Agendar", "Quando sobrar tempo")
    ]
    assert positions == sorted(positions)


def test_only_the_first_task_can_be_started(client, classic, add_task):
    """ "Clique em Iniciar na primeira." There is one start action, and it starts the head."""
    add_task(classic, "segunda", g=2)
    add_task(classic, "primeira", g=5)

    html = client.get(classic.get_absolute_url()).content.decode()
    client.post(reverse("pull-next", args=[classic.pk]), **HTMX)

    assert html.count(reverse("pull-next", args=[classic.pk])) == 2  # one form: action + hx-post
    assert classic.running_task().title == "primeira"


def test_nothing_else_can_start_while_a_task_runs(client, classic, add_task):
    """ "Enquanto ela estiver em execução, as outras ficam bloqueadas." """
    add_task(classic, "rodando", status=Status.RUNNING)
    add_task(classic, "esperando")

    html = client.get(classic.get_absolute_url()).content.decode()

    assert reverse("pull-next", args=[classic.pk]) not in html


def test_board_says_when_the_queue_now_outranks_the_running_task(client, classic, add_task):
    """ "Só troque de tarefa se a nova passar da atual." """
    add_task(classic, "atual", g=3, u=3, t=3, status=Status.RUNNING)
    add_task(classic, "mais baixa", g=2, u=2, t=2)

    def board_region():
        html = client.get(classic.get_absolute_url()).content.decode()
        return html[html.index('id="board"') :]

    assert "nota maior" not in board_region()

    add_task(classic, "urgente", g=5, u=5, t=4)

    assert "nota maior (100) que esta tarefa (27)" in board_region()
