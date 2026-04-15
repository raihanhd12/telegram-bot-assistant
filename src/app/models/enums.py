"""Shared enums for task-assignment models."""

from enum import StrEnum
from typing import Type


class TaskStatus(StrEnum):
    """Lifecycle status for a task."""

    ASSIGNED = "assigned"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskEventType(StrEnum):
    """Audit event types for task changes."""

    ASSIGNED = "assigned"
    REASSIGNED = "reassigned"
    DONE = "done"
    CANCELLED = "cancelled"


def enum_values(enum_cls: Type[StrEnum]) -> list[str]:
    """Return enum values for SQLAlchemy Enum persistence."""
    return [member.value for member in enum_cls]
