from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("saude/", views.health, name="health"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("esteiras/<int:pk>/", views.board, name="board"),
    path("esteiras/<int:pk>/revisao/", views.review, name="review"),
    path("esteiras/<int:pk>/tarefas/", views.task_create, name="task-create"),
    path("esteiras/<int:pk>/puxar/", views.pull_next, name="pull-next"),
    path("tarefas/<int:pk>/editar/", views.task_edit, name="task-edit"),
    path("tarefas/<int:pk>/concluir/", views.task_complete, name="task-complete"),
    path("tarefas/<int:pk>/devolver/", views.task_return, name="task-return"),
    path("tarefas/<int:pk>/excluir/", views.task_delete, name="task-delete"),
    path("tarefas/<int:pk>/pausar/", views.task_pause, name="task-pause"),
    path("tarefas/<int:pk>/retomar/", views.task_resume, name="task-resume"),
    path("tarefas/<int:pk>/bloquear/", views.task_block, name="task-block"),
    path("tarefas/<int:pk>/desbloquear/", views.task_unblock, name="task-unblock"),
    path("tarefas/<int:pk>/descartar/", views.task_discard, name="task-discard"),
    path("tarefas/<int:pk>/restaurar/", views.task_restore, name="task-restore"),
]
