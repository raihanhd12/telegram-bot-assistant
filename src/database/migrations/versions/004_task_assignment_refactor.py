"""Refactor bot schema from game domain to task assignment domain.

Revision ID: 004_task_assignment_refactor
Revises: 003_player_verified_false
Create Date: 2026-04-15
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_task_assignment_refactor"
down_revision: Union[str, None] = "003_player_verified_false"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    """Replace game tables with task assignment tables."""
    op.drop_index(op.f("ix_game_players_id"), table_name="game_players")
    op.drop_table("game_players")

    op.drop_index(op.f("ix_games_status"), table_name="games")
    op.drop_index(op.f("ix_games_chat_id"), table_name="games")
    op.drop_index(op.f("ix_games_id"), table_name="games")
    op.drop_table("games")

    op.drop_index(op.f("ix_questions_is_active"), table_name="questions")
    op.drop_index(op.f("ix_questions_category"), table_name="questions")
    op.drop_index(op.f("ix_questions_word"), table_name="questions")
    op.drop_index(op.f("ix_questions_id"), table_name="questions")
    op.drop_table("questions")

    op.drop_index(op.f("ix_players_telegram_id"), table_name="players")
    op.drop_index(op.f("ix_players_id"), table_name="players")
    op.drop_table("players")

    op.execute("DROP TYPE IF EXISTS gamestatus")
    op.execute("DROP TYPE IF EXISTS questionsource")
    op.execute("DROP TYPE IF EXISTS difficulty")
    op.execute("DROP TYPE IF EXISTS category")

    op.create_table(
        "members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_members_id"), "members", ["id"])
    op.create_index(op.f("ix_members_telegram_id"), "members", ["telegram_id"], unique=True)
    op.create_index(op.f("ix_members_username"), "members", ["username"], unique=True)

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("raw_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("assigned", "done", "cancelled", name="taskstatus"),
            nullable=False,
            server_default="assigned",
        ),
        sa.Column("assigned_by_member_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to_member_id", sa.Integer(), nullable=False),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["assigned_by_member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["assigned_to_member_id"], ["members.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_id"), "tasks", ["id"])
    op.create_index(op.f("ix_tasks_scope_chat_id"), "tasks", ["scope_chat_id"])
    op.create_index(op.f("ix_tasks_raw_chat_id"), "tasks", ["raw_chat_id"])
    op.create_index(op.f("ix_tasks_thread_id"), "tasks", ["thread_id"])
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"])

    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum("assigned", "reassigned", "done", "cancelled", name="taskeventtype"),
            nullable=False,
        ),
        sa.Column("actor_member_id", sa.Integer(), nullable=True),
        sa.Column("previous_assignee_member_id", sa.Integer(), nullable=True),
        sa.Column("new_assignee_member_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["new_assignee_member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["previous_assignee_member_id"], ["members.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_events_id"), "task_events", ["id"])
    op.create_index(op.f("ix_task_events_task_id"), "task_events", ["task_id"])
    op.create_index(op.f("ix_task_events_event_type"), "task_events", ["event_type"])


def downgrade() -> None:
    """Recreate old game schema and drop task assignment tables."""
    op.drop_index(op.f("ix_task_events_event_type"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_task_id"), table_name="task_events")
    op.drop_index(op.f("ix_task_events_id"), table_name="task_events")
    op.drop_table("task_events")

    op.drop_index(op.f("ix_tasks_status"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_thread_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_raw_chat_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_scope_chat_id"), table_name="tasks")
    op.drop_index(op.f("ix_tasks_id"), table_name="tasks")
    op.drop_table("tasks")

    op.drop_index(op.f("ix_members_username"), table_name="members")
    op.drop_index(op.f("ix_members_telegram_id"), table_name="members")
    op.drop_index(op.f("ix_members_id"), table_name="members")
    op.drop_table("members")

    op.execute("DROP TYPE IF EXISTS taskeventtype")
    op.execute("DROP TYPE IF EXISTS taskstatus")
