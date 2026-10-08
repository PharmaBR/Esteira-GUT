from django import forms
from django.utils import timezone

from esteira.domain.rules import Verdict, triage
from esteira.domain.scoring import ANCHORS, MAX_RATING, MIN_RATING, urgency_from_deadline

from .models import EFFORT_CHOICES, Task

RATINGS = range(MIN_RATING, MAX_RATING + 1)
UNSET = [("", "Escolha…")]
DEFAULT_RATING = 3

TASK_WIDGETS = {
    "title": forms.TextInput(attrs={"autocomplete": "off"}),
    "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
}
# The question is the visible label, never a placeholder that vanishes on the first keystroke.
TITLE_LABEL = "O que precisa ser feito?"
# Error wording is ours and short: each message has one reserved line under its field,
# and must fit there on a phone (tests/boards/test_feedback.py).
TITLE_ERRORS = {"required": "Escreva o que precisa ser feito."}


class RatingField(forms.TypedChoiceField):
    def __init__(self, **kwargs):
        kwargs.setdefault("choices", [(n, str(n)) for n in RATINGS])
        kwargs.setdefault("coerce", int)
        kwargs.setdefault("error_messages", {"required": "Escolha uma nota."})
        super().__init__(**kwargs)


def anchored(scale):
    """Choices that say what each level means, with nothing preselected."""
    return UNSET + [(n, f"{n} · {ANCHORS[scale][n]}") for n in RATINGS]


class ClassicTaskForm(forms.ModelForm):
    """The original form: three ratings defaulting to 3, a category, a date."""

    fields_template = "boards/_task_fields_classic.html"

    gravity = RatingField(label="Gravidade", initial=DEFAULT_RATING)
    urgency = RatingField(label="Urgência", initial=DEFAULT_RATING)
    trend = RatingField(label="Tendência", initial=DEFAULT_RATING)

    class Meta:
        model = Task
        fields = ["title", "gravity", "urgency", "trend", "category", "due_date"]
        widgets = TASK_WIDGETS
        labels = {"title": TITLE_LABEL, "category": "Categoria", "due_date": "Prazo (opcional)"}
        error_messages = {"title": TITLE_ERRORS}

    @property
    def rating_fields(self):
        return [self[name] for name in ("gravity", "urgency", "trend")]


class EnhancedTaskForm(forms.ModelForm):
    """The audited form: no defaults, anchored scales, a deadline instead of a guess."""

    fields_template = "boards/_task_fields_enhanced.html"

    gravity = RatingField(label="Gravidade", choices=anchored("gravity"))
    trend = RatingField(label="Tendência", choices=anchored("trend"))
    urgency = RatingField(
        label="Urgência, se não houver prazo",
        choices=anchored("urgency"),
        required=False,
        empty_value=None,
    )
    effort = forms.ChoiceField(
        label="Esforço estimado",
        choices=UNSET + EFFORT_CHOICES,
        error_messages={"required": "Escolha o esforço."},
    )

    class Meta:
        model = Task
        fields = ["title", "gravity", "trend", "due_date", "urgency", "effort", "category"]
        widgets = TASK_WIDGETS
        labels = {"title": TITLE_LABEL, "category": "Categoria", "due_date": "Prazo"}
        help_texts = {"due_date": "Com prazo, a urgência é calculada."}
        error_messages = {"title": TITLE_ERRORS}

    def clean(self):
        cleaned = super().clean()
        due_date = cleaned.get("due_date")
        if due_date:
            # Stored as a snapshot; the policy recomputes it from the date every day.
            cleaned["urgency"] = urgency_from_deadline(due_date, timezone.localdate())
        elif cleaned.get("urgency") is None and "urgency" not in self.errors:
            self.add_error("urgency", "Informe o prazo ou a urgência.")
        return cleaned


class EnhancedNewTaskForm(EnhancedTaskForm):
    """Adds the triage at the door: only what is important and yours gets in."""

    important = forms.BooleanField(label="É importante para um objetivo meu", required=False)
    mine = forms.BooleanField(label="Só eu posso fazer", required=False)

    ADVICE = {
        Verdict.DISCARD: "Não é importante: descarte.",
        Verdict.DELEGATE: "Não é sua: delegue a quem cabe.",
    }

    def clean(self):
        cleaned = super().clean()
        verdict = triage(important=cleaned.get("important", False), mine=cleaned.get("mine", False))
        if verdict is not Verdict.ADMIT:
            self.add_error(None, self.ADVICE[verdict])
        return cleaned


class CompletionForm(forms.Form):
    """What the enhanced esteira asks when a task is done, to calibrate the next ones."""

    actual_effort = forms.ChoiceField(
        label="Quanto tempo levou?",
        choices=EFFORT_CHOICES,
        error_messages={"required": "Escolha quanto tempo levou."},
    )
    priority_verdict = forms.ChoiceField(
        label="A prioridade estava certa?",
        choices=Task.PriorityVerdict.choices,
        widget=forms.RadioSelect,
    )


def task_form_class(board, editing=False):
    if not board.is_enhanced:
        return ClassicTaskForm
    return EnhancedTaskForm if editing else EnhancedNewTaskForm
