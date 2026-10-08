from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("saude/", views.health, name="health"),
    path("favicon.ico", views.favicon, name="favicon"),
    path("esteiras/<int:pk>/", views.board, name="board"),
    path("esteiras/<int:pk>/tarefas/", views.task_create, name="task-create"),
    path("esteiras/<int:pk>/puxar/", views.pull_next, name="pull-next"),
    path("tarefas/<int:pk>/editar/", views.task_edit, name="task-edit"),
    path("tarefas/<int:pk>/concluir/", views.task_complete, name="task-complete"),
    path("tarefas/<int:pk>/devolver/", views.task_return, name="task-return"),
    path("tarefas/<int:pk>/excluir/", views.task_delete, name="task-delete"),
]
