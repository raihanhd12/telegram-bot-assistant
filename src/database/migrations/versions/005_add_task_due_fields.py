"""Add task due metadata fields.

Revision ID: 005_add_task_due_fields
Revises: 004_task_assignment_refactor
Create Date: 2026-04-15
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_add_task_due_fields"
down_revision: Union[str, None] = "004_task_assignment_refactor"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("due_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "due_text")
    op.drop_column("tasks", "due_at")
