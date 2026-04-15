"""Member model for Telegram task assignment bot."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database.session import Base

if TYPE_CHECKING:
    from src.app.models.task import Task
    from src.app.models.task_event import TaskEvent


class Member(Base):
    """Represents a Telegram user known by the bot."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True, index=True)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    assigned_tasks: Mapped[list[Task]] = relationship(
        "Task",
        foreign_keys="Task.assigned_by_member_id",
        back_populates="assigned_by",
    )
    received_tasks: Mapped[list[Task]] = relationship(
        "Task",
        foreign_keys="Task.assigned_to_member_id",
        back_populates="assigned_to",
    )
    acted_task_events: Mapped[list[TaskEvent]] = relationship(
        "TaskEvent",
        foreign_keys="TaskEvent.actor_member_id",
        back_populates="actor",
    )

    def __repr__(self) -> str:
        return f"<Member(id={self.id}, telegram_id={self.telegram_id}, username={self.username!r})>"
