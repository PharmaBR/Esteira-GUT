from django.contrib import admin

from .models import Board, Task


@admin.register(Board)
class BoardAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "mode", "created_at"]
    list_filter = ["mode"]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "board", "status", "gravity", "urgency", "trend", "due_date"]
    list_filter = ["status", "board__mode", "category"]
    search_fields = ["title"]
