from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from esteira.domain import rules
from esteira.domain.rules import OPEN_STATUSES, RuleViolation, Status
from esteira.domain.scoring import (
    MAX_RATING,
    MIN_RATING,
    ClassicGUT,
    Effort,
    EnhancedGUT,
    effort_for_minutes,
)

RATING_VALIDATORS = [MinValueValidator(MIN_RATING), MaxValueValidator(MAX_RATING)]
EFFORT_CHOICES = [(effort.value, effort.label) for effort in Effort]


class Board(models.Model):
    """One person's esteira. The mode picks the rules it plays by."""

    class Mode(models.TextChoices):
        CLASSIC = rules.Mode.CLASSIC.value, "Clássica"
        ENHANCED = rules.Mode.ENHANCED.value, "Aprimorada"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="boards"
    )
    name = models.CharField("nome", max_length=80)
    mode = models.CharField("modo", max_length=10, choices=Mode.choices, default=Mode.CLASSIC)
    queue_limit = models.PositiveSmallIntegerField(
        "teto de tarefas abertas",
        default=20,
        help_text="Só vale para a esteira aprimorada.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "esteira"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "mode"], name="one_board_per_mode_per_owner"),
        ]

    def __str__(self):
        return f"{self.name} ({self.owner})"

    def get_absolute_url(self):
        return reverse("board", args=[self.pk])

    @classmethod
    def for_user(cls, user):
        """The user's boards, creating one per version on first visit."""
        for mode in cls.Mode:
            cls.objects.get_or_create(owner=user, mode=mode, defaults={"name": mode.label})
        return cls.objects.filter(owner=user)

    @property
    def rule_mode(self) -> rules.Mode:
        return rules.Mode(self.mode)

    @property
    def is_enhanced(self) -> bool:
        return self.mode == self.Mode.ENHANCED

    @property
    def policy(self):
        return EnhancedGUT() if self.is_enhanced else ClassicGUT()

    def ranked_queue(self, now):
        return self.policy.rank(self.tasks.filter(status=Status.QUEUED), now)

    def running_task(self):
        return self.tasks.filter(status=Status.RUNNING).first()

    def with_status(self, status: Status):
        return self.tasks.filter(status=status)

    def done_tasks(self):
        return self.with_status(Status.DONE).order_by("-completed_at")

    def open_count(self) -> int:
        return self.tasks.filter(status__in=OPEN_STATUSES).count()

    def ensure_room(self):
        """Refuse a new task when the enhanced esteira is at its ceiling."""
        if self.is_enhanced:
            rules.ensure_capacity(self.open_count(), self.queue_limit)

    def pull_next(self, now):
        """Start whatever the policy puts at the head of the queue."""
        queue = self.ranked_queue(now)
        if not queue:
            raise RuleViolation("A fila está vazia.")
        task = queue[0].task
        task.start(now)
        return task


class Task(models.Model):
    class Category(models.TextChoices):
        CONTENT = "content", "Conteúdo"
        ASSESSMENT = "assessment", "Avaliação"
        ADMIN = "admin", "Administrativo"
        PROJECT = "project", "Projeto"
        PERSONAL = "personal", "Pessoal"

    class PriorityVerdict(models.TextChoices):
        RIGHT = "right", "Veio na hora certa"
        LATE = "late", "Deveria ter vindo antes"
        EARLY = "early", "Poderia ter esperado"

    STATUS_CHOICES = [
        (Status.QUEUED.value, "Na fila"),
        (Status.RUNNING.value, "Em execução"),
        (Status.PAUSED.value, "Pausada"),
        (Status.BLOCKED.value, "Bloqueada"),
        (Status.DONE.value, "Concluída"),
        (Status.DISCARDED.value, "Descartada"),
    ]

    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField("tarefa", max_length=200)
    gravity = models.PositiveSmallIntegerField("gravidade", validators=RATING_VALIDATORS)
    urgency = models.PositiveSmallIntegerField("urgência", validators=RATING_VALIDATORS)
    trend = models.PositiveSmallIntegerField("tendência", validators=RATING_VALIDATORS)
    category = models.CharField(
        "categoria", max_length=20, choices=Category.choices, default=Category.CONTENT
    )
    due_date = models.DateField("prazo", null=True, blank=True)
    effort = models.CharField("esforço", max_length=2, choices=EFFORT_CHOICES, blank=True)

    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=Status.QUEUED.value, db_index=True
    )
    status_reason = models.CharField("motivo", max_length=200, blank=True)
    interruptions = models.PositiveSmallIntegerField("interrupções", default=0)

    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    running_since = models.DateTimeField(null=True, blank=True)
    worked_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)

    actual_effort = models.CharField(
        "esforço real", max_length=2, choices=EFFORT_CHOICES, blank=True
    )
    priority_verdict = models.CharField(
        "a prioridade estava certa?", max_length=5, choices=PriorityVerdict.choices, blank=True
    )

    class Meta:
        verbose_name = "tarefa"
        ordering = ["created_at"]
        constraints = [
            # The single slot, enforced by the database as well as by the rules.
            models.UniqueConstraint(
                fields=["board"],
                condition=Q(status=Status.RUNNING.value),
                name="one_running_task_per_board",
            ),
            models.CheckConstraint(
                condition=Q(gravity__range=(MIN_RATING, MAX_RATING))
                & Q(urgency__range=(MIN_RATING, MAX_RATING))
                & Q(trend__range=(MIN_RATING, MAX_RATING)),
                name="gut_ratings_between_1_and_5",
            ),
        ]

    def __str__(self):
        return self.title

    # ── Time in the slot ────────────────────────────────────────────

    def seconds_worked(self, now) -> int:
        current = (now - self.running_since).total_seconds() if self.running_since else 0
        return self.worked_seconds + max(0, int(current))

    def measured_effort(self, now) -> Effort:
        """The effort size the clock suggests; offered as the default at completion."""
        return effort_for_minutes(self.seconds_worked(now) / 60)

    def _stop_clock(self, now):
        self.worked_seconds = self.seconds_worked(now)
        self.running_since = None

    # ── State changes: the domain rules decide, the model records ───

    def _move_to(self, target: Status):
        rules.ensure_transition(self.board.rule_mode, Status(self.status), target)
        self.status = target.value

    def _enter_slot(self, now):
        running = self.board.tasks.filter(status=Status.RUNNING).count()
        rules.ensure_slot_free(running)
        self._move_to(Status.RUNNING)
        self.started_at = self.started_at or now
        self.running_since = now
        self.status_reason = ""
        self.save()

    def start(self, now):
        self._enter_slot(now)

    def resume(self, now):
        self._enter_slot(now)

    def complete(self, now, actual_effort="", priority_verdict=""):
        self._move_to(Status.DONE)
        self._stop_clock(now)
        self.completed_at = now
        self.actual_effort = actual_effort
        self.priority_verdict = priority_verdict
        self.save()

    def return_to_queue(self, now):
        self._move_to(Status.QUEUED)
        self._stop_clock(now)
        self.save()

    def pause(self, now, reason):
        """An interruption: free the slot, remember why, count it."""
        reason = rules.ensure_reason(reason)
        self._move_to(Status.PAUSED)
        self._stop_clock(now)
        self.status_reason = reason
        self.interruptions += 1
        self.save()

    def block(self, now, reason):
        """Waiting on someone or something else: step aside until that changes."""
        reason = rules.ensure_reason(reason)
        self._move_to(Status.BLOCKED)
        self._stop_clock(now)
        self.status_reason = reason
        self.save()

    def unblock(self):
        self._move_to(Status.QUEUED)
        self.status_reason = ""
        self.save()

    def discard(self):
        """Decide not to do it. Kept on record, out of the way."""
        self._move_to(Status.DISCARDED)
        self.save()

    def remove(self):
        """Delete a task that was never started."""
        if self.status != Status.QUEUED:
            raise RuleViolation("Só é possível excluir tarefas que ainda estão na fila.")
        self.delete()
