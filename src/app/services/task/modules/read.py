"""Task read/query operations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.app.models import Member, Task, TaskStatus
from src.app.repositories.task import TaskRepository
from src.app.services.task.modules.validators import TaskValidators


class TaskReadService:
    """Service for reading task data."""

    def __init__(self, db: Session):
        self.db = db

    def get_task(self, task_id: int, scope_chat_id: int) -> Task | None:
        return TaskRepository.get_by_id_in_scope(self.db, task_id, scope_chat_id)

    def list_open_tasks(self, scope_chat_id: int, limit: int = 20) -> list[Task]:
        return TaskRepository.list_tasks(
            self.db,
            scope_chat_id=scope_chat_id,
            status=TaskStatus.ASSIGNED,
            limit=limit,
        )

    def list_tasks_for_assignee(self, scope_chat_id: int, member: Member, limit: int = 20) -> list[Task]:
        return TaskRepository.list_tasks(
            self.db,
            scope_chat_id=scope_chat_id,
            status=TaskStatus.ASSIGNED,
            assigned_to_member_id=member.id,
            limit=limit,
        )

    def list_tasks_from_assigner(self, scope_chat_id: int, member: Member, limit: int = 20) -> list[Task]:
        return TaskRepository.list_tasks(
            self.db,
            scope_chat_id=scope_chat_id,
            status=TaskStatus.ASSIGNED,
            assigned_by_member_id=member.id,
            limit=limit,
        )

    def get_latest_open_task(
        self,
        scope_chat_id: int,
        assigned_to_member_id: int | None = None,
        assigned_by_member_id: int | None = None,
    ) -> Task | None:
        return TaskRepository.get_latest_open_task(
            self.db,
            scope_chat_id=scope_chat_id,
            assigned_to_member_id=assigned_to_member_id,
            assigned_by_member_id=assigned_by_member_id,
        )

    def get_latest_matching_open_task(
        self,
        scope_chat_id: int,
        description_fragment: str,
        assigned_to_member_id: int | None = None,
        assigned_by_member_id: int | None = None,
    ) -> Task | None:
        return TaskRepository.get_latest_matching_open_task(
            self.db,
            scope_chat_id=scope_chat_id,
            description_fragment=description_fragment,
            assigned_to_member_id=assigned_to_member_id,
            assigned_by_member_id=assigned_by_member_id,
        )

    def list_all_open_tasks(self) -> list[Task]:
        return TaskRepository.list_all_open_tasks(self.db)

    def format_task_list(self, title: str, tasks: list[Task]) -> str:
        if not tasks:
            return f"{title}\n\nBelum ada task."

        lines = [title, ""]
        for task in tasks:
            lines.append(f"#{task.id} -> {TaskValidators.display_member(task.assigned_to)}")
            lines.append(task.description)
            lines.append(f"By: {TaskValidators.display_member(task.assigned_by)}")
            if task.due_at or task.due_text:
                lines.append(f"Due: {TaskValidators.format_due(task)}")
            lines.append("")
        return "\n".join(lines).strip()
