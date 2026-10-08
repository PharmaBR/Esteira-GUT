from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from esteira.domain.rules import RuleViolation, Status

from .forms import task_form_class
from .models import Board, Task

DONE_SHOWN = 20
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


def _context(request, board, form=None, error=None):
    now = timezone.localtime()
    queue = board.ranked_queue(now)
    done = board.done_tasks()
    return {
        "board": board,
        "running": board.running_task(),
        "queue": queue,
        "next_up": queue[0] if queue else None,
        "done": done[:DONE_SHOWN],
        "done_count": done.count(),
        "form": form or task_form_class(board)(),
        "error": error,
        "today": now.date(),
    }


def _page(request, board, context, status=200):
    context["boards"] = Board.for_user(request.user)
    return render(request, "boards/board.html", context, status=status)


def _respond(request, board, form=None, error=None, status=200):
    """Answer an action with the fresh board: a partial for htmx, a page otherwise."""
    if not request.htmx and status == 200:
        return redirect(board)
    context = _context(request, board, form, error)
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
@require_POST
@transaction.atomic
def task_create(request, pk):
    board = _board(request, pk, lock=True)
    form = task_form_class(board)(request.POST)
    if not form.is_valid():
        return _respond(request, board, form=form, status=UNPROCESSABLE)
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
    return _attempt(request, task.board, lambda: task.complete(timezone.now()))


@login_required
@require_POST
@transaction.atomic
def task_return(request, pk):
    task = _task(request, pk)
    return _attempt(request, task.board, task.return_to_queue)


@login_required
@require_POST
@transaction.atomic
def task_delete(request, pk):
    task = _task(request, pk)
    return _attempt(request, task.board, task.remove)
