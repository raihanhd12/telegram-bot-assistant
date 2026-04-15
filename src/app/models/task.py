"""Task model for Telegram task assignment bot."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.app.models.enums import TaskStatus, enum_values
from src.database.session import Base

if TYPE_CHECKING:
    from src.app.models.member import Member
    from src.app.models.task_event import TaskEvent


class Task(Base):
    """Represents one task assignment in a group/topic scope."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    raw_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    thread_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(
            TaskStatus,
            name="taskstatus",
            values_callable=enum_values,
            validate_strings=True,
        ),
        nullable=False,
        default=TaskStatus.ASSIGNED,
        index=True,
    )
    assigned_by_member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False)
    assigned_to_member_id: Mapped[int] = mapped_column(Integer, ForeignKey("members.id"), nullable=False)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assigned_by: Mapped[Member] = relationship(
        "Member",
        foreign_keys=[assigned_by_member_id],
        back_populates="assigned_tasks",
    )
    assigned_to: Mapped[Member] = relationship(
        "Member",
        foreign_keys=[assigned_to_member_id],
        back_populates="received_tasks",
    )
    events: Mapped[list[TaskEvent]] = relationship(
        "TaskEvent",
        back_populates="task",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, scope_chat_id={self.scope_chat_id}, status={self.status})>"
