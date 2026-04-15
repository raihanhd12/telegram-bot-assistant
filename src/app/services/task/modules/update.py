"""Task update operations."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.app.models import Member, Task, TaskEventType, TaskStatus
from src.app.repositories.task import TaskRepository
from src.app.repositories.task_event import TaskEventRepository
from src.app.services.task.modules.validators import TaskValidators


class TaskUpdateService:
    """Service for task state transitions."""

    def __init__(self, db: Session):
        self.db = db

    def reassign_task(self, task: Task, actor: Member, new_assignee: Member, is_admin: bool) -> Task:
        if not TaskValidators.can_reassign(task, actor, is_admin):
            raise PermissionError("Hanya assigner atau admin yang bisa reassign task ini.")
        if not TaskValidators.is_open(task):
            raise ValueError("Task ini sudah tidak aktif.")

        previous_assignee_id = task.assigned_to_member_id
        updated = TaskRepository.update_task(
            self.db,
            task,
            {"assigned_to_member_id": new_assignee.id},
        )
        TaskEventRepository.create_event(
            self.db,
            task_id=updated.id,
            event_type=TaskEventType.REASSIGNED,
            actor_member_id=actor.id,
            previous_assignee_member_id=previous_assignee_id,
            new_assignee_member_id=new_assignee.id,
        )
        return TaskRepository.get_by_id(self.db, updated.id) or updated

    def mark_done(self, task: Task, actor: Member, is_admin: bool) -> Task:
        if not TaskValidators.can_mark_done(task, actor, is_admin):
            raise PermissionError("Hanya assignee, assigner, atau admin yang bisa menyelesaikan task ini.")
        if not TaskValidators.is_open(task):
            raise ValueError("Task ini sudah tidak aktif.")

        updated = TaskRepository.update_task(
            self.db,
            task,
            {
                "status": TaskStatus.DONE,
                "completed_at": datetime.now(timezone.utc),
                "cancelled_at": None,
            },
        )
        TaskEventRepository.create_event(
            self.db,
            task_id=updated.id,
            event_type=TaskEventType.DONE,
            actor_member_id=actor.id,
            previous_assignee_member_id=updated.assigned_to_member_id,
            new_assignee_member_id=updated.assigned_to_member_id,
        )
        return TaskRepository.get_by_id(self.db, updated.id) or updated

    def cancel_task(self, task: Task, actor: Member, is_admin: bool) -> Task:
        if not TaskValidators.can_cancel(task, actor, is_admin):
            raise PermissionError("Hanya assigner atau admin yang bisa membatalkan task ini.")
        if not TaskValidators.is_open(task):
            raise ValueError("Task ini sudah tidak aktif.")

        updated = TaskRepository.update_task(
            self.db,
            task,
            {
                "status": TaskStatus.CANCELLED,
                "cancelled_at": datetime.now(timezone.utc),
                "completed_at": None,
            },
        )
        TaskEventRepository.create_event(
            self.db,
            task_id=updated.id,
            event_type=TaskEventType.CANCELLED,
            actor_member_id=actor.id,
            previous_assignee_member_id=updated.assigned_to_member_id,
            new_assignee_member_id=updated.assigned_to_member_id,
        )
        return TaskRepository.get_by_id(self.db, updated.id) or updated

    def set_due(self, task: Task, actor: Member, due_at, due_text: str | None, is_admin: bool) -> Task:
        if not TaskValidators.can_reassign(task, actor, is_admin):
            raise PermissionError("Hanya assigner atau admin yang bisa mengubah target waktu task ini.")
        if not TaskValidators.is_open(task):
            raise ValueError("Task ini sudah tidak aktif.")

        updated = TaskRepository.update_task(
            self.db,
            task,
            {
                "due_at": due_at,
                "due_text": due_text,
            },
        )
        return TaskRepository.get_by_id(self.db, updated.id) or updated
