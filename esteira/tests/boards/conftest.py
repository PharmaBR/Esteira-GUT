from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from esteira.boards.models import Board, Task

HTMX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user("breno", password="segredo-forte-1")


@pytest.fixture
def stranger(db):
    return get_user_model().objects.create_user("outra", password="segredo-forte-2")


@pytest.fixture
def client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def classic(user):
    return Board.objects.create(owner=user, name="Clássica", mode=Board.Mode.CLASSIC)


@pytest.fixture
def enhanced(user):
    return Board.objects.create(owner=user, name="Aprimorada", mode=Board.Mode.ENHANCED)


@pytest.fixture
def add_task():
    """Create tasks spaced a minute apart, so arrival order is unambiguous."""
    counter = {"n": 0}

    def make(board, title="Tarefa", g=3, u=3, t=3, **extra):
        counter["n"] += 1
        extra.setdefault(
            "created_at", timezone.now() - timedelta(hours=1) + timedelta(minutes=counter["n"])
        )
        return Task.objects.create(board=board, title=title, gravity=g, urgency=u, trend=t, **extra)

    return make
