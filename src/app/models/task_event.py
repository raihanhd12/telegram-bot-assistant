"""Task event audit model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.models.enums import TaskEventType, enum_values
from src.database.session import Base

if TYPE_CHECKING:
    from src.app.models.member import Member
    from src.app.models.task import Task


class TaskEvent(Base):
    """Audit record for task lifecycle changes."""

    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[TaskEventType] = mapped_column(
        SQLEnum(
            TaskEventType,
            name="taskeventtype",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
    )
    actor_member_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("members.id"), nullable=True)
    previous_assignee_member_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("members.id"),
        nullable=True,
    )
    new_assignee_member_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("members.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    task: Mapped[Task] = relationship("Task", back_populates="events")
    actor: Mapped[Member | None] = relationship(
        "Member",
        foreign_keys=[actor_member_id],
        back_populates="acted_task_events",
    )
    previous_assignee: Mapped[Member | None] = relationship(
        "Member",
        foreign_keys=[previous_assignee_member_id],
    )
    new_assignee: Mapped[Member | None] = relationship(
        "Member",
        foreign_keys=[new_assignee_member_id],
    )

    def __repr__(self) -> str:
        return f"<TaskEvent(id={self.id}, task_id={self.task_id}, event_type={self.event_type})>"
