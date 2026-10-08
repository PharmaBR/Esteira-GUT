"""The design system in design.md, held in place by tests.

These are the rules that are easy to erode one small edit at a time: a raw
colour here, a capitalised label there. Each one is a decision made for
readability and calm, so breaking it should be deliberate.
"""

import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse
from django.utils import timezone

import esteira.boards

APP = Path(esteira.boards.__file__).parent
CSS = APP / "static" / "boards" / "css"
TEMPLATES = sorted((APP / "templates").rglob("*.html"))


def rules_of(path):
    """The stylesheet without comments, so prose in comments cannot trip a check."""
    return re.sub(r"/\*.*?\*/", "", path.read_text(), flags=re.DOTALL)


APP_CSS = rules_of(CSS / "app.css")
TOKENS_CSS = rules_of(CSS / "tokens.css")


def test_every_colour_in_the_app_stylesheet_is_a_token():
    raw = re.findall(r"#[0-9a-fA-F]{3,8}\b|\b(?:oklch|oklab|rgb|rgba|hsl|hsla|lab|lch)\(", APP_CSS)

    assert raw == [], f"raw colours in app.css; add a token to tokens.css instead: {raw}"


def test_every_font_in_the_app_stylesheet_is_a_token():
    families = re.findall(r"font-family:\s*([^;]+);", APP_CSS)

    assert families and all(value.strip().startswith("var(--font-") for value in families)


def test_tokens_are_oklch_and_never_pure_black_or_white():
    colours = re.findall(r"--color-[\w-]+:\s*([^;]+);", TOKENS_CSS)

    assert colours
    for value in colours:
        assert value.startswith(("oklch(", "var(--color-")), value
        match = re.match(r"oklch\(([\d.]+)% ([\d.]+)", value)
        if match:
            lightness, chroma = float(match[1]), float(match[2])
            assert 0 < lightness < 100 and chroma >= 0.005, f"flat or pure colour: {value}"


def test_design_md_states_the_same_colours_as_the_tokens():
    """design.md is the written rule and tokens.css the running one: they must agree."""
    design = (APP.parent.parent / "design.md").read_text()
    light = TOKENS_CSS.split("@media")[0]
    colours = re.findall(r"(--color-[\w-]+):\s*([^;]+);", light)

    assert colours
    for name, value in colours:
        assert re.search(rf"{re.escape(name)}:\s*{re.escape(value)};", design), (
            f"design.md does not say {name}: {value}"
        )


def test_nothing_is_set_in_capitals_or_italics():
    """Capitals and italics are harder to read, most of all for dyslexic readers."""
    assert "text-transform" not in APP_CSS
    assert "font-style: italic" not in APP_CSS
    for template in TEMPLATES:
        assert not re.search(r"<(em|i)\b", template.read_text()), template.name


def test_no_animation_runs_without_a_reduced_motion_rule():
    assert "prefers-reduced-motion: reduce" in APP_CSS
    assert "transition: all" not in APP_CSS and "transition:all" not in APP_CSS


def test_templates_use_real_typography():
    for template in TEMPLATES:
        text = BeautifulSoup(template.read_text(), "html.parser").get_text()
        text = re.sub(r"\{[%{#].*?[%}#]\}", "", text, flags=re.DOTALL)
        assert "..." not in text, f"{template.name}: use … instead of three dots"
        assert not re.search(r"\w \-\- \w", text), f"{template.name}: use — instead of --"
        assert not re.search(r"""(?<![=\w])["'][A-Za-zÀ-ú]""", text), (
            f"{template.name}: use curly quotes in visible text"
        )


@pytest.mark.django_db
def test_every_form_field_has_a_visible_label(client, classic, enhanced, add_task):
    """No placeholder-as-label: the question stays visible after you start typing."""
    now = timezone.now()
    for board in (classic, enhanced):
        add_task(board, "na fila", effort="s")
        add_task(board, "rodando", effort="s", status="running", started_at=now, running_since=now)
    urls = [classic.get_absolute_url(), enhanced.get_absolute_url(), reverse("login")]

    for url in urls:
        client.logout() if url == reverse("login") else None
        soup = BeautifulSoup(client.get(url).content, "html.parser")
        for field in soup.select("input:not([type=hidden]):not([type=submit]), select, textarea"):
            label = soup.select_one(f'label[for="{field.get("id")}"]') or field.find_parent("label")
            assert label is not None, f"{url}: {field.get('name')} has no label"
            assert "sr-only" not in label.get("class", []), (
                f"{url}: the label of {field.get('name')} is hidden"
            )
