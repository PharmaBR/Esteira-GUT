from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from esteira.domain import rules
from esteira.domain.rules import RuleViolation, Status
from esteira.domain.scoring import MAX_RATING, MIN_RATING, ClassicGUT

RATING_VALIDATORS = [MinValueValidator(MIN_RATING), MaxValueValidator(MAX_RATING)]


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
        """The user's boards, creating the default ones on first visit."""
        for mode in DEFAULT_MODES:
            cls.objects.get_or_create(owner=user, mode=mode, defaults={"name": mode.label})
        return cls.objects.filter(owner=user)

    @property
    def rule_mode(self) -> rules.Mode:
        return rules.Mode(self.mode)

    @property
    def policy(self):
        return ClassicGUT()

    def ranked_queue(self, now):
        return self.policy.rank(self.tasks.filter(status=Status.QUEUED), now)

    def running_task(self):
        return self.tasks.filter(status=Status.RUNNING).first()

    def done_tasks(self):
        return self.tasks.filter(status=Status.DONE).order_by("-completed_at")

    def pull_next(self, now):
        """Start whatever the policy puts at the head of the queue."""
        queue = self.ranked_queue(now)
        if not queue:
            raise RuleViolation("A fila está vazia.")
        task = queue[0].task
        task.start(now)
        return task


DEFAULT_MODES = [Board.Mode.CLASSIC]


class Task(models.Model):
    class Category(models.TextChoices):
        CONTENT = "content", "Conteúdo"
        ASSESSMENT = "assessment", "Avaliação"
        ADMIN = "admin", "Administrativo"
        PROJECT = "project", "Projeto"
        PERSONAL = "personal", "Pessoal"

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
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=Status.QUEUED.value, db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

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

    def _move_to(self, target: Status):
        rules.ensure_transition(self.board.rule_mode, Status(self.status), target)
        self.status = target.value

    def start(self, now):
        running = self.board.tasks.filter(status=Status.RUNNING).count()
        rules.ensure_slot_free(running)
        self._move_to(Status.RUNNING)
        self.started_at = self.started_at or now
        self.save()

    def complete(self, now):
        self._move_to(Status.DONE)
        self.completed_at = now
        self.save()

    def return_to_queue(self):
        self._move_to(Status.QUEUED)
        self.save()

    def remove(self):
        """Delete a task that was never started."""
        if self.status != Status.QUEUED:
            raise RuleViolation("Só é possível excluir tarefas que ainda estão na fila.")
        self.delete()
