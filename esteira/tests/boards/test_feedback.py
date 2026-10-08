"""After every action the person must see what happened, in the place they are looking.

Each test here is a defect an independent audit of the interface found: a message
rendered off screen, a browser bubble instead of our own wording, a form that jumped.
"""

import re

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from django.utils import timezone

from esteira.domain.rules import Status

from .conftest import HTMX
from .test_design_system import APP_CSS

pytestmark = pytest.mark.django_db

# About what fits on one line of a 320 px phone at the size of an error message.
ONE_LINE = 34


def soup_of(response):
    return BeautifulSoup(response.content, "html.parser")


@pytest.fixture
def busy(enhanced, add_task):
    now = timezone.now()
    add_task(enhanced, "na fila", effort="s")
    add_task(
        enhanced, "rodando", effort="s", status=Status.RUNNING, started_at=now, running_since=now
    )
    add_task(enhanced, "pausada", effort="s", status=Status.PAUSED, status_reason="telefone")
    return enhanced


def test_a_refused_action_answers_with_a_message_that_can_take_focus(client, busy):
    """app.js moves focus (and so the scroll) to it; without tabindex it cannot."""
    paused = busy.tasks.get(title="pausada")

    response = client.post(reverse("task-resume", args=[paused.pk]), **HTMX)

    alert = soup_of(response).select_one("#board > .alert")
    assert response.status_code == 409
    assert alert["role"] == "alert" and alert["tabindex"] == "-1"


@pytest.mark.parametrize(
    ("action", "title"), [("task-block", "na fila"), ("task-pause", "rodando")]
)
def test_an_empty_reason_is_answered_inside_the_form_that_asked(client, busy, action, title):
    task = busy.tasks.get(title=title)
    was = task.status

    response = client.post(reverse(action, args=[task.pk]), {"reason": "  "}, **HTMX)

    task.refresh_from_db()
    form = soup_of(response).select_one(f'form[action="{reverse(action, args=[task.pk])}"]')
    field = form.select_one("input[name=reason]")
    note = form.select_one(f"#{field['aria-describedby']}")
    assert response.status_code == 422 and task.status == was
    assert form.find_parent("details").has_attr("open"), "the form that failed must stay open"
    assert field["aria-invalid"] == "true"
    assert "field-error" in note["class"] and note.get_text(strip=True)
    assert soup_of(response).select_one("#board > .alert") is None, "one message, in one place"


def test_an_invalid_edit_replaces_only_its_own_row(client, busy):
    """The edit form targets the whole board; an invalid answer is just the form."""
    task = busy.tasks.get(title="na fila")

    response = client.post(reverse("task-edit", args=[task.pk]), {"title": ""}, **HTMX)

    soup = soup_of(response)
    assert response.status_code == 422
    assert response["HX-Retarget"] == f"#task-{task.pk}"
    assert soup.select_one("#board") is None and soup.select_one(f"li#task-{task.pk}.editing")
    assert soup.select_one('[aria-invalid="true"]')


def test_reason_forms_use_our_wording_not_the_browser_bubble(client, busy):
    forms = soup_of(client.get(busy.get_absolute_url())).select("details.reason form")

    assert forms
    for form in forms:
        assert form.has_attr("novalidate")
        assert not form.select_one("[required]")


def test_only_the_page_you_are_on_is_marked_as_current(client, busy):
    board = soup_of(client.get(busy.get_absolute_url()))
    review = soup_of(client.get(reverse("review", args=[busy.pk])))

    assert [a.get_text() for a in board.select('.versions [aria-current="page"]')] == ["Aprimorada"]
    assert review.select('.versions [aria-current="page"]') == []


def test_every_page_has_a_main_landmark_and_a_way_to_skip_to_it(client, busy):
    task = busy.tasks.get(title="na fila")
    pages = [
        busy.get_absolute_url(),
        reverse("review", args=[busy.pk]),
        reverse("task-edit", args=[task.pk]),
        reverse("login"),
    ]

    for url in pages:
        client.logout() if url == reverse("login") else None
        soup = soup_of(client.get(url))
        main = soup.select_one("main[id]")
        assert main is not None, f"{url}: no <main>"
        assert soup.select_one(f'a[href="#{main["id"]}"]') is not None, f"{url}: no skip link"


def test_every_field_has_its_error_line_before_any_error(client, busy):
    """A line that only appears with the error pushes the rest of the form down."""
    pages = [soup_of(client.get(busy.get_absolute_url()))]
    client.logout()
    pages.append(soup_of(client.get(reverse("login"))))

    for soup in pages:
        groups = soup.select("form .field, form fieldset")
        assert groups
        for group in groups:
            shared = group.find_parent(class_="field-group")
            assert group.select_one(".field-note") or (
                shared and shared.select_one(".field-note")
            ), f"no reserved error line: {group.get_text(' ', strip=True)[:40]}"


def test_error_messages_fit_the_line_reserved_for_them(client, enhanced, add_task):
    now = timezone.now()
    task = add_task(
        enhanced, "rodando", effort="s", status=Status.RUNNING, started_at=now, running_since=now
    )

    responses = [
        client.post(reverse("task-create", args=[enhanced.pk]), {"title": ""}, **HTMX),
        client.post(
            reverse("task-create", args=[enhanced.pk]),
            {
                "title": "x",
                "gravity": 3,
                "trend": 3,
                "urgency": 3,
                "effort": "s",
                "category": "content",
            },
            **HTMX,
        ),
        client.post(reverse("task-complete", args=[task.pk]), {}, **HTMX),
        client.post(reverse("task-pause", args=[task.pk]), {"reason": ""}, **HTMX),
    ]

    seen = []
    for response in responses:
        assert response.status_code == 422
        seen += [note.get_text(strip=True) for note in soup_of(response).select(".field-error")]
    assert len(seen) >= 6
    for message in seen:
        assert len(message) <= ONE_LINE, f"too long for one line on a phone: {message!r}"


def test_reduced_motion_rules_are_not_overridden_later_in_the_file():
    last_transition = max(m.start() for m in re.finditer(r"transition:(?!\s*none)", APP_CSS))

    assert APP_CSS.rindex("prefers-reduced-motion: reduce") > last_transition


def test_an_invalid_field_turns_red_whatever_its_type():
    """`[aria-invalid]` alone loses to `input[type="text"]` on specificity."""
    for control in ("input", "select"):
        assert f'{control}[aria-invalid="true"]' in APP_CSS
