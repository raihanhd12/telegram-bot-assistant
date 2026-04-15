"""Repository helpers for TaskEvent model."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.app.models import TaskEvent


class TaskEventRepository:
    """CRUD helpers for task events."""

    @staticmethod
    def create_event(db: Session, **kwargs: Any) -> TaskEvent:
        event = TaskEvent(**kwargs)
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def list_by_task(db: Session, task_id: int) -> list[TaskEvent]:
        return db.query(TaskEvent).filter(TaskEvent.task_id == task_id).order_by(TaskEvent.id.asc()).all()
