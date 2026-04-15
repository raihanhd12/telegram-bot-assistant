"""Task create operations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from src.app.models import Member, Task, TaskEventType, TaskStatus
from src.app.repositories.member import MemberRepository
from src.app.repositories.task import TaskRepository
from src.app.repositories.task_event import TaskEventRepository
from src.app.services.task.modules.validators import TaskValidators


class TaskCreateService:
    """Service for creating task assignments."""

    def __init__(self, db: Session):
        self.db = db

    def ensure_actor(self, telegram_id: int, username: str | None, full_name: str | None) -> Member:
        return MemberRepository.get_or_create_from_telegram(
            self.db,
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )

    def ensure_assignee(self, username: str) -> Member:
        return MemberRepository.get_or_create_by_username(self.db, username)

    def create_task(
        self,
        scope_chat_id: int,
        raw_chat_id: int,
        thread_id: int | None,
        assigned_by: Member,
        assigned_to: Member,
        description: str,
        source_message_id: int | None,
        source_text: str | None,
    ) -> Task:
        clean_description = TaskValidators.ensure_description(description)
        if not clean_description:
            raise ValueError("Deskripsi task kosong.")

        task = TaskRepository.create_task(
            self.db,
            scope_chat_id=scope_chat_id,
            raw_chat_id=raw_chat_id,
            thread_id=thread_id,
            description=clean_description,
            status=TaskStatus.ASSIGNED,
            assigned_by_member_id=assigned_by.id,
            assigned_to_member_id=assigned_to.id,
            source_message_id=source_message_id,
            source_text=TaskValidators.sanitize_text(source_text),
        )
        TaskEventRepository.create_event(
            self.db,
            task_id=task.id,
            event_type=TaskEventType.ASSIGNED,
            actor_member_id=assigned_by.id,
            previous_assignee_member_id=None,
            new_assignee_member_id=assigned_to.id,
        )
        return TaskRepository.get_by_id(self.db, task.id) or task
