"""Enforce players.is_verified default false

Revision ID: 003_player_verified_false
Revises: 002_add_player_is_verified
Create Date: 2026-03-03

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_player_verified_false"
down_revision: Union[str, None] = "002_add_player_is_verified"
branch_labels: Union[str, list[str], None] = None
depends_on: Union[str, list[str], None] = None


def upgrade() -> None:
    """Set players verification default to false and revoke current players."""
    op.alter_column(
        "players",
        "is_verified",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
    op.execute("UPDATE players SET is_verified = false")


def downgrade() -> None:
    """Restore players verification default to true."""
    op.alter_column(
        "players",
        "is_verified",
        existing_type=sa.Boolean(),
        server_default=sa.text("true"),
        existing_nullable=False,
    )
