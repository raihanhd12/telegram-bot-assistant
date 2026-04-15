"""Add is_verified to players

Revision ID: 002_add_player_is_verified
Revises: 001_add_game_tables
Create Date: 2026-03-03

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_add_player_is_verified"
down_revision: Union[str, None] = "001_add_game_tables"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add players.is_verified column."""
    op.add_column(
        "players",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    """Downgrade schema - remove players.is_verified column."""
    op.drop_column("players", "is_verified")
