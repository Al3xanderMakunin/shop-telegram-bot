"""add top-up notification destination settings

Revision ID: b4c6d8e0f2a4
Revises: 9a7b6c5d4e3f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c6d8e0f2a4"
down_revision: Union[str, None] = "9a7b6c5d4e3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bot_settings",
        sa.Column("topup_notification_chat_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "bot_settings",
        sa.Column("topup_notification_thread_id", sa.Integer(), nullable=True),
    )
    # Older installations may not have created the singleton row yet.
    op.execute(
        sa.text(
            "INSERT INTO bot_settings (id, maintenance_mode) "
            "SELECT 1, false WHERE NOT EXISTS "
            "(SELECT 1 FROM bot_settings WHERE id = 1)"
        )
    )


def downgrade() -> None:
    op.drop_column("bot_settings", "topup_notification_thread_id")
    op.drop_column("bot_settings", "topup_notification_chat_id")
