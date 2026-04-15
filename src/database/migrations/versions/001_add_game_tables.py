"""Add game tables

Revision ID: 001_add_game_tables
Revises: 0d8254272b94
Create Date: 2026-03-02

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_add_game_tables"
down_revision: Union[str, None] = "0d8254272b94"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add game-related tables."""
    # Create enum types for PostgreSQL
    # Note: SQLite doesn't support CREATE ENUM, so we use CHECK constraints instead

    # Create questions table
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(length=255), nullable=False),
        sa.Column("answer", sa.String(length=255), nullable=False),
        sa.Column(
            "category",
            sa.Enum("lucu", "mind_blowing", name="category"),
            nullable=False,
        ),
        sa.Column(
            "difficulty",
            sa.Enum("easy", "medium", "hard", name="difficulty"),
            nullable=False,
        ),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="100"),
        sa.Column(
            "source",
            sa.Enum("llm", "manual", name="questionsource"),
            nullable=False,
            server_default="llm",
        ),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
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
    op.create_index(op.f("ix_questions_id"), "questions", ["id"])
    op.create_index(op.f("ix_questions_word"), "questions", ["word"], unique=True)
    op.create_index(op.f("ix_questions_category"), "questions", ["category"])
    op.create_index(op.f("ix_questions_is_active"), "questions", ["is_active"])

    # Create players table
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("best_streak", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index(op.f("ix_players_id"), "players", ["id"])
    op.create_index(
        op.f("ix_players_telegram_id"), "players", ["telegram_id"], unique=True
    )

    # Create games table
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column(
            "category",
            sa.Enum("lucu", "mind_blowing", name="category"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("active", "expired", "completed", name="gamestatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "current_hint_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
    )
    op.create_index(op.f("ix_games_id"), "games", ["id"])
    op.create_index(op.f("ix_games_chat_id"), "games", ["chat_id"])
    op.create_index(op.f("ix_games_status"), "games", ["status"])

    # Create game_players junction table
    op.create_table(
        "game_players",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_answered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["game_id"], ["games.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
    )
    op.create_index(op.f("ix_game_players_id"), "game_players", ["id"])


def downgrade() -> None:
    """Downgrade schema - remove game-related tables."""
    # Drop in reverse order due to foreign keys
    op.drop_index(op.f("ix_game_players_id"), table_name="game_players")
    op.drop_table("game_players")

    op.drop_index(op.f("ix_games_status"), table_name="games")
    op.drop_index(op.f("ix_games_chat_id"), table_name="games")
    op.drop_index(op.f("ix_games_id"), table_name="games")
    op.drop_table("games")

    op.drop_index(op.f("ix_players_telegram_id"), table_name="players")
    op.drop_index(op.f("ix_players_id"), table_name="players")
    op.drop_table("players")

    op.drop_index(op.f("ix_questions_is_active"), table_name="questions")
    op.drop_index(op.f("ix_questions_category"), table_name="questions")
    op.drop_index(op.f("ix_questions_word"), table_name="questions")
    op.drop_index(op.f("ix_questions_id"), table_name="questions")
    op.drop_table("questions")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS category")
    op.execute("DROP TYPE IF EXISTS difficulty")
    op.execute("DROP TYPE IF EXISTS questionsource")
    op.execute("DROP TYPE IF EXISTS gamestatus")
