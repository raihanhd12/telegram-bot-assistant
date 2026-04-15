"""Repository helpers for Task model."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.app.models import Task, TaskStatus


class TaskRepository:
    """CRUD helpers for tasks."""

    @staticmethod
    def _with_relations(query):
        return query.options(
            joinedload(Task.assigned_by),
            joinedload(Task.assigned_to),
            joinedload(Task.events),
        )

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Task | None:
        return TaskRepository._with_relations(db.query(Task)).filter(Task.id == task_id).first()

    @staticmethod
    def get_by_id_in_scope(db: Session, task_id: int, scope_chat_id: int) -> Task | None:
        return (
            TaskRepository._with_relations(db.query(Task))
            .filter(Task.id == task_id, Task.scope_chat_id == scope_chat_id)
            .first()
        )

    @staticmethod
    def create_task(db: Session, **kwargs: Any) -> Task:
        task = Task(**kwargs)
        db.add(task)
        db.commit()
        db.refresh(task)
        return TaskRepository.get_by_id(db, task.id) or task

    @staticmethod
    def update_task(db: Session, task: Task, update_data: dict[str, Any]) -> Task:
        for key, value in update_data.items():
            setattr(task, key, value)
        db.add(task)
        db.commit()
        db.refresh(task)
        return TaskRepository.get_by_id(db, task.id) or task

    @staticmethod
    def list_tasks(
        db: Session,
        scope_chat_id: int,
        status: TaskStatus | None = None,
        assigned_to_member_id: int | None = None,
        assigned_by_member_id: int | None = None,
        limit: int = 20,
    ) -> list[Task]:
        query = TaskRepository._with_relations(db.query(Task)).filter(Task.scope_chat_id == scope_chat_id)
        if status is not None:
            query = query.filter(Task.status == status)
        if assigned_to_member_id is not None:
            query = query.filter(Task.assigned_to_member_id == assigned_to_member_id)
        if assigned_by_member_id is not None:
            query = query.filter(Task.assigned_by_member_id == assigned_by_member_id)
        return query.order_by(Task.created_at.desc(), Task.id.desc()).limit(limit).all()

    @staticmethod
    def get_latest_open_task(
        db: Session,
        scope_chat_id: int,
        assigned_to_member_id: int | None = None,
        assigned_by_member_id: int | None = None,
    ) -> Task | None:
        query = TaskRepository._with_relations(db.query(Task)).filter(
            Task.scope_chat_id == scope_chat_id,
            Task.status == TaskStatus.ASSIGNED,
        )
        if assigned_to_member_id is not None:
            query = query.filter(Task.assigned_to_member_id == assigned_to_member_id)
        if assigned_by_member_id is not None:
            query = query.filter(Task.assigned_by_member_id == assigned_by_member_id)
        return query.order_by(Task.created_at.desc(), Task.id.desc()).first()

    @staticmethod
    def get_latest_matching_open_task(
        db: Session,
        scope_chat_id: int,
        description_fragment: str,
        assigned_to_member_id: int | None = None,
        assigned_by_member_id: int | None = None,
    ) -> Task | None:
        query = TaskRepository._with_relations(db.query(Task)).filter(
            Task.scope_chat_id == scope_chat_id,
            Task.status == TaskStatus.ASSIGNED,
            func.lower(Task.description).like(f"%{description_fragment.lower()}%"),
        )
        if assigned_to_member_id is not None:
            query = query.filter(Task.assigned_to_member_id == assigned_to_member_id)
        if assigned_by_member_id is not None:
            query = query.filter(Task.assigned_by_member_id == assigned_by_member_id)
        return query.order_by(Task.created_at.desc(), Task.id.desc()).first()

    @staticmethod
    def list_all_open_tasks(db: Session) -> list[Task]:
        return (
            TaskRepository._with_relations(db.query(Task))
            .filter(Task.status == TaskStatus.ASSIGNED)
            .order_by(Task.assigned_to_member_id.asc(), Task.created_at.asc(), Task.id.asc())
            .all()
        )
