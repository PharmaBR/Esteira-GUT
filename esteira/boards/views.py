from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from esteira.domain.rules import OPEN_STATUSES, RuleViolation, Status, estimate_accuracy
from esteira.domain.scoring import Effort

from .forms import CompletionForm, task_form_class
from .models import Board, Task

DONE_SHOWN = 20
STALE_AFTER_WEEKS = 2
CONFLICT = 409
UNPROCESSABLE = 422


@require_GET
def health(request):
    return HttpResponse("ok", content_type="text/plain")


@require_GET
def favicon(request):
    return redirect(static("boards/icons/icon.svg"))


# Every lookup is filtered by the signed-in owner: other people's boards and
# tasks are indistinguishable from ones that do not exist.
def _board(request, pk, lock=False):
    boards = Board.objects.select_for_update() if lock else Board.objects
    return get_object_or_404(boards, pk=pk, owner=request.user)


def _task(request, pk):
    owned = get_object_or_404(Task, pk=pk, board__owner=request.user)
    # Lock the board, then read the task again so we act on its current state.
    board = Board.objects.select_for_update().get(pk=owned.board_id)
    task = Task.objects.get(pk=pk)
    task.board = board
    return task


def _context(request, board, form=None, error=None, completion_form=None):
    now = timezone.localtime()
    queue = board.ranked_queue(now)
    done = board.done_tasks()
    running = board.running_task()
    context = {
        "board": board,
        "running": running,
        "queue": queue,
        "next_up": queue[0] if queue else None,
        "done": done[:DONE_SHOWN],
        "done_count": done.count(),
        "form": form or task_form_class(board)(),
        "error": error,
        "today": now.date(),
    }
    if board.is_enhanced:
        if running and completion_form is None:
            measured = running.measured_effort(now)
            completion_form = CompletionForm(initial={"actual_effort": measured.value})
        context.update(
            paused=board.with_status(Status.PAUSED),
            blocked=board.with_status(Status.BLOCKED),
            open_count=board.open_count(),
            completion_form=completion_form,
        )
    return context


def _page(request, board, context, status=200):
    context["boards"] = Board.for_user(request.user)
    return render(request, "boards/board.html", context, status=status)


def _respond(request, board, status=200, **context):
    """Answer an action with the fresh board: a partial for htmx, a page otherwise."""
    if not request.htmx and status == 200:
        return redirect(board)
    context = _context(request, board, **context)
    if request.htmx:
        return render(request, "boards/_board.html", context, status=status)
    return _page(request, board, context, status=status)


def _attempt(request, board, action):
    """Run a state change; a broken rule comes back as a message on the board."""
    try:
        action()
    except RuleViolation as violation:
        return _respond(request, board, error=str(violation), status=CONFLICT)
    return _respond(request, board)


@login_required
@require_GET
def home(request):
    return redirect(Board.for_user(request.user).first())


@login_required
@require_GET
def board(request, pk):
    board = _board(request, pk)
    context = _context(request, board)
    if request.htmx:
        return render(request, "boards/_board.html", context)
    return _page(request, board, context)


@login_required
@require_GET
def review(request, pk):
    """The weekly review of the enhanced esteira: is the scoring telling the truth?"""
    board = _board(request, pk)
    if not board.is_enhanced:
        raise Http404
    now = timezone.localtime()
    week_ago = now - timedelta(days=7)
    month = board.with_status(Status.DONE).filter(completed_at__gte=now - timedelta(days=30))

    pairs = (
        month.exclude(effort="").exclude(actual_effort="").values_list("effort", "actual_effort")
    )
    counted = dict(
        month.exclude(priority_verdict="")
        .values_list("priority_verdict")
        .annotate(total=Count("pk"))
    )
    verdicts = {verdict.value: counted.get(verdict.value, 0) for verdict in Task.PriorityVerdict}
    touched_this_week = Q(status__in=OPEN_STATUSES) | Q(completed_at__gte=week_ago)
    interruptions = board.tasks.filter(touched_this_week).aggregate(total=Sum("interruptions"))

    context = {
        "board": board,
        "boards": Board.for_user(request.user),
        "stale_weeks": STALE_AFTER_WEEKS,
        "review": {
            "done_this_week": month.filter(completed_at__gte=week_ago).count(),
            "accuracy": estimate_accuracy((Effort(e), Effort(a)) for e, a in pairs),
            "verdicts": verdicts,
            "verdict_rows": [(v.label, verdicts[v.value]) for v in Task.PriorityVerdict],
            "interruptions": interruptions["total"] or 0,
            "open_count": board.open_count(),
            "stale": [
                item
                for item in board.ranked_queue(now)
                if item.priority.weeks_waiting >= STALE_AFTER_WEEKS
            ],
            "blocked": board.with_status(Status.BLOCKED),
            "paused": board.with_status(Status.PAUSED),
        },
    }
    return render(request, "boards/review.html", context)


@login_required
@require_POST
@transaction.atomic
def task_create(request, pk):
    board = _board(request, pk, lock=True)
    form = task_form_class(board)(request.POST)
    if not form.is_valid():
        return _respond(request, board, form=form, status=UNPROCESSABLE)
    try:
        board.ensure_room()
    except RuleViolation as violation:
        # Keep what was typed: the person may make room and try again.
        return _respond(request, board, form=form, error=str(violation), status=CONFLICT)
    form.instance.board = board
    form.save()
    return _respond(request, board)


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def task_edit(request, pk):
    task = _task(request, pk)
    if task.status != Status.QUEUED:
        return _respond(
            request, task.board, error="Só tarefas na fila podem ser editadas.", status=CONFLICT
        )
    form_class = task_form_class(task.board, editing=True)
    form = form_class(request.POST or None, instance=task, auto_id="edit_%s")
    if request.method == "POST" and form.is_valid():
        form.save()
        return _respond(request, task.board)
    status = UNPROCESSABLE if request.method == "POST" else 200
    context = {"board": task.board, "task": task, "form": form}
    template = "boards/_task_edit.html" if request.htmx else "boards/task_edit.html"
    return render(request, template, context, status=status)


@login_required
@require_POST
@transaction.atomic
def pull_next(request, pk):
    board = _board(request, pk, lock=True)
    return _attempt(request, board, lambda: board.pull_next(timezone.now()))


@login_required
@require_POST
@transaction.atomic
def task_complete(request, pk):
    task = _task(request, pk)
    now = timezone.now()
    if not task.board.is_enhanced:
        return _attempt(request, task.board, lambda: task.complete(now))
    form = CompletionForm(request.POST)
    if not form.is_valid():
        return _respond(request, task.board, completion_form=form, status=UNPROCESSABLE)
    return _attempt(request, task.board, lambda: task.complete(now, **form.cleaned_data))


def _task_action(action):
    """Build a view that applies one state change to one of the user's tasks."""

    @login_required
    @require_POST
    @transaction.atomic
    def view(request, pk):
        task = _task(request, pk)
        return _attempt(request, task.board, lambda: action(task, request))

    return view


task_return = _task_action(lambda task, request: task.return_to_queue(timezone.now()))
task_delete = _task_action(lambda task, request: task.remove())
task_pause = _task_action(
    lambda task, request: task.pause(timezone.now(), request.POST.get("reason"))
)
task_block = _task_action(
    lambda task, request: task.block(timezone.now(), request.POST.get("reason"))
)
task_resume = _task_action(lambda task, request: task.resume(timezone.now()))
task_unblock = _task_action(lambda task, request: task.unblock())
task_discard = _task_action(lambda task, request: task.discard())
