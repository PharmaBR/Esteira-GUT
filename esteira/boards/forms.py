from django import forms

from esteira.domain.scoring import MAX_RATING, MIN_RATING

from .models import Task

RATING_CHOICES = [(n, str(n)) for n in range(MIN_RATING, MAX_RATING + 1)]
DEFAULT_RATING = 3


class RatingField(forms.TypedChoiceField):
    def __init__(self, **kwargs):
        kwargs.setdefault("choices", RATING_CHOICES)
        kwargs.setdefault("coerce", int)
        super().__init__(**kwargs)


class ClassicTaskForm(forms.ModelForm):
    """The original form: three ratings defaulting to 3, a category, a date."""

    gravity = RatingField(label="Gravidade", initial=DEFAULT_RATING)
    urgency = RatingField(label="Urgência", initial=DEFAULT_RATING)
    trend = RatingField(label="Tendência", initial=DEFAULT_RATING)

    class Meta:
        model = Task
        fields = ["title", "gravity", "urgency", "trend", "category", "due_date"]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "O que precisa ser feito?", "autocomplete": "off"}
            ),
            "due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        labels = {"title": "Tarefa", "category": "Categoria", "due_date": "Prazo (opcional)"}

    @property
    def rating_fields(self):
        return [self[name] for name in ("gravity", "urgency", "trend")]


def task_form_class(board, editing=False):
    return ClassicTaskForm
