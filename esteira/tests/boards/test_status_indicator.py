"""Project rule: nothing talks to the server without showing it.

Every element that issues an htmx request must declare a visible indicator
and disable itself while the request is in flight. These tests render every
screen with tasks in every state and fail if a single request is silent.
"""

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from django.utils import timezone

from .conftest import HTMX

pytestmark = pytest.mark.django_db

HX_VERBS = ["hx-get", "hx-post", "hx-put", "hx-patch", "hx-delete"]


def requesting_elements(soup):
    return [el for el in soup.find_all(True) if any(el.has_attr(verb) for verb in HX_VERBS)]


def describe(el):
    verb = next(v for v in HX_VERBS if el.has_attr(v))
    return f"<{el.name} {verb}={el[verb]!r}>"


def indicator_is_visible(el, soup):
    """The declared indicator must lead to an element carrying .htmx-indicator."""
    target = el.get("hx-indicator", "")
    if target == "this":
        owners = [el]
    elif target.startswith("#"):
        owners = soup.select(target)
    else:
        return False
    return any(
        "htmx-indicator" in owner.get("class", []) or owner.select_one(".htmx-indicator")
        for owner in owners
    )


def assert_no_silent_requests(html):
    soup = BeautifulSoup(html, "html.parser")
    elements = requesting_elements(soup)
    assert elements, "expected at least one htmx request on this screen"
    for el in elements:
        assert indicator_is_visible(el, soup), f"{describe(el)} has no visible hx-indicator"
        assert el.has_attr("hx-disabled-elt"), f"{describe(el)} does not set hx-disabled-elt"
    return len(elements)


@pytest.fixture
def busy_classic(classic, add_task):
    """A classic board with something in every state it can show."""
    add_task(classic, "Na fila 1", g=5)
    add_task(classic, "Na fila 2")
    add_task(classic, "Feita", status="done", completed_at=timezone.now())
    add_task(classic, "Rodando", status="running", started_at=timezone.now())
    return classic


def test_page_has_the_global_progress_bar_and_error_region(client, classic):
    soup = BeautifulSoup(client.get(classic.get_absolute_url()).content, "html.parser")

    assert soup.select_one("#progress")
    assert soup.select_one("#request-status[aria-live]")
    assert soup.select_one("#request-error[role=alert]")


def test_classic_board_with_a_running_task(client, busy_classic):
    assert_no_silent_requests(client.get(busy_classic.get_absolute_url()).content)


def test_classic_board_with_an_empty_slot(client, classic, add_task):
    add_task(classic, "Na fila")

    assert_no_silent_requests(client.get(classic.get_absolute_url()).content)


def test_edit_form(client, classic, add_task):
    task = add_task(classic, "Na fila")

    assert_no_silent_requests(client.get(reverse("task-edit", args=[task.pk]), **HTMX).content)


@pytest.fixture
def busy_enhanced(enhanced, add_task):
    """An enhanced board showing every kind of card at once."""
    now = timezone.now()
    add_task(enhanced, "Crise", g=5, u=5, t=3, effort="s")
    add_task(enhanced, "Na fila", effort="m", due_date=timezone.localdate())
    add_task(enhanced, "Pausada", effort="s", status="paused", status_reason="interrupção")
    add_task(enhanced, "Bloqueada", effort="s", status="blocked", status_reason="aguardando")
    add_task(enhanced, "Feita", effort="s", status="done", completed_at=now)
    add_task(enhanced, "Rodando", effort="s", status="running", started_at=now, running_since=now)
    return enhanced


def test_enhanced_board_with_every_state(client, busy_enhanced):
    html = client.get(busy_enhanced.get_absolute_url()).content.decode()

    for section in ("Pausadas", "Bloqueadas", "Crise", "Pausar", "Bloquear", "Descartar"):
        assert section in html, f"fixture no longer renders {section!r}"
    assert assert_no_silent_requests(html) >= 12


def test_enhanced_board_with_an_empty_slot(client, enhanced, add_task):
    add_task(enhanced, "Na fila", effort="m")

    assert_no_silent_requests(client.get(enhanced.get_absolute_url()).content)


def test_enhanced_board_after_a_rejected_action(client, busy_enhanced):
    """Error responses are swapped in too, so they obey the same rule."""
    response = client.post(reverse("pull-next", args=[busy_enhanced.pk]), **HTMX)

    assert response.status_code == 409
    assert_no_silent_requests(response.content)


def test_enhanced_edit_form(client, enhanced, add_task):
    task = add_task(enhanced, "Na fila", effort="m")

    assert_no_silent_requests(client.get(reverse("task-edit", args=[task.pk]), **HTMX).content)


def test_review_page_navigates_under_the_global_bar(client, busy_enhanced):
    soup = BeautifulSoup(
        client.get(reverse("review", args=[busy_enhanced.pk])).content, "html.parser"
    )

    assert soup.select_one("#progress")
    assert requesting_elements(soup) == []  # plain links only; app.js covers page loads


def test_every_template_with_an_htmx_request_is_exercised_here():
    """A new partial that issues requests must be added to the screens rendered above."""
    from pathlib import Path

    import esteira.boards

    templates = Path(esteira.boards.__file__).parent / "templates"
    with_requests = {
        path.name
        for path in templates.rglob("*.html")
        if any(f"{verb}=" in path.read_text() for verb in HX_VERBS)
    }

    assert with_requests == {
        "_board.html",
        "_running.html",
        "_task.html",
        "_task_edit.html",
        "_parked.html",
        "_reason_form.html",
    }


def test_the_check_itself_catches_a_silent_request():
    silent = '<form hx-post="/x/" hx-disabled-elt="find button"><button>Ir</button></form>'

    with pytest.raises(AssertionError, match="no visible hx-indicator"):
        assert_no_silent_requests(silent)
